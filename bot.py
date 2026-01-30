import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px

# --- AYARLAR ---
# Buradaki ID'nin senin Google Sheet ID'n olduğundan emin ol!
SPREADSHEET_ID = '1w7_IRXQ9I2eAFLlhbCqr-Q_R5Ww752zjs8CTNNbfRgI' 
RANGE_NAME = 'Sayfa1!A:E'
ARCHIVE_RANGE_NAME = 'Arsiv!A:E'
SETTINGS_RANGE = 'Ayarlar!A1:B1' # A1: Görev Adı, B1: Hedef Tarih

# Şifre Yönetimi (Lokalde hata almamak için try-except)
try:
    ADMIN_SIFRESI = st.secrets["admin_sifresi"]
except:
    ADMIN_SIFRESI = "teknofest2026"

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_google_sheet_service():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    if os.path.exists("secrets.json"):
        creds = service_account.Credentials.from_service_account_file("secrets.json", scopes=SCOPES)
    elif "gcp_service_account" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    else:
        st.error("🚨 HATA: Google Cloud anahtarı bulunamadı!")
        st.stop()
    return build('sheets', 'v4', credentials=creds)

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Teknofest Komuta Merkezi", page_icon="🚀", layout="wide")

try:
    service = get_google_sheet_service()
    sheet = service.spreadsheets()

    # --- 🎯 1. ÖZEL HEDEFİ OKU (Ayarlar sayfasından) ---
    try:
        settings_result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=SETTINGS_RANGE).execute()
        s_values = settings_result.get('values', [["Genel Hedef", "2026-08-30"]])
        gorev_adi = s_values[0][0]
        gorev_tarihi_str = s_values[0][1]
        hedef_dt = datetime.strptime(gorev_tarihi_str, "%Y-%m-%d")
    except:
        gorev_adi = "Genel Hedef"
        hedef_dt = datetime(2026, 8, 30)

    # --- ⏰ 2. ÜST PANEL: GERİ SAYIM SAYACI ---
    simdi = datetime.now()
    kalan = hedef_dt - simdi
    
    if kalan.total_seconds() > 0:
        st.markdown(f"""
            <div style="background-color:#0E1117; padding:30px; border-radius:15px; border-bottom: 5px solid #00D4FF; text-align:center; margin-bottom:25px; box-shadow: 0px 4px 15px rgba(0,0,0,0.5);">
                <h4 style="color:#00D4FF; margin:0; letter-spacing: 3px;">KRİTİK TAKVİM HEDEFİ</h4>
                <h1 style="color:white; margin:15px 0; font-size: 40px;">{gorev_adi}</h1>
                <h2 style="color:#FF4B4B; margin:0;">{kalan.days} Gün : {kalan.seconds//3600} Saat Kaldı</h2>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.balloons()
        st.success(f"🎊 {gorev_adi} Hedef Süresi Tamamlandı!")

    # --- 🔧 3. YAN MENÜ: ADMİN KONTROL ---
    st.sidebar.title("🔧 Yönetici Paneli")
    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False

    if not st.session_state['admin_logged_in']:
        sifre = st.sidebar.text_input("Giriş Şifresi", type="password")
        if st.sidebar.button("Admin Girişi"):
            if sifre == ADMIN_SIFRESI:
                st.session_state['admin_logged_in'] = True
                st.rerun()
            else:
                st.sidebar.error("Hatalı Şifre!")
    else:
        st.sidebar.success("Yönetici Girişi Yapıldı")
        st.sidebar.divider()
        # ADMİN ÖZEL HEDEF BELİRLEME
        st.sidebar.subheader("🎯 Görev Hedefi Güncelle")
        yeni_ad = st.sidebar.text_input("Görevin Adı:", value=gorev_adi)
        yeni_tarih = st.sidebar.date_input("Hedef Tarih:", value=hedef_dt)
        
        if st.sidebar.button("Hedefi Takıma Duyur 📢"):
            yeni_tarih_str = yeni_tarih.strftime("%Y-%m-%d")
            sheet.values().update(
                spreadsheetId=SPREADSHEET_ID, range=SETTINGS_RANGE,
                valueInputOption="USER_ENTERED", body={"values": [[yeni_ad, yeni_tarih_str]]}
            ).execute()
            st.sidebar.success("Sistem güncellendi!")
            st.rerun()

        if st.sidebar.button("Güvenli Çıkış"):
            st.session_state['admin_logged_in'] = False
            st.rerun()

    # --- 📊 4. ANA VERİ ANALİZİ ---
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    if values:
        df = pd.DataFrame(values[1:], columns=["Tarih", "İsim", "Alan", "İş"])
        df["Tarih_Formatli"] = pd.to_datetime(df["Tarih"])
        
        # Grafik ve Tablo Görünümü
        col_sol, col_sag = st.columns([2, 1])

        with col_sol:
            st.subheader("📊 Ekip Performans Analizi")
            tab_gun, tab_ay = st.tabs(["Bugünkü Yarış", "Aylık Dağılım"])
            
            with tab_gun:
                df_gunluk = df[df["Tarih_Formatli"].dt.date == simdi.date()]
                if not df_gunluk.empty:
                    fig_gun = px.bar(df_gunluk["Alan"].value_counts().reset_index(), x="Alan", y="count", color="Alan",
                                     title="Bugün Girilen Rapor Sayıları",
                                     color_discrete_map={"Mekanik": "#EF553B", "Elektronik": "#636EFA", "PR": "#00CC96", "Genel": "#AB63FA"})
                    st.plotly_chart(fig_gun, use_container_width=True)
                else:
                    st.info("Bugün henüz kimse rapor girmedi. İlk sen ol!")

            with tab_ay:
                df_aylik = df[df["Tarih_Formatli"].dt.month == simdi.month]
                if not df_aylik.empty:
                    fig_ay = px.pie(df_aylik["Alan"].value_counts().reset_index(), names="Alan", values="count", hole=0.4)
                    st.plotly_chart(fig_ay, use_container_width=True)

            st.subheader("📝 Rapor Akışı")
            st.dataframe(df.sort_values(by="Tarih_Formatli", ascending=False)[["Tarih", "İsim", "Alan", "İş"]], use_container_width=True, hide_index=True)

        with col_sag:
            st.subheader("➕ Yeni Rapor")
            with st.form("yeni_kayit_formu", clear_on_submit=True):
                y_isim = st.text_input("Ad Soyad")
                y_ekip = st.selectbox("Ekip", ["Mekanik", "Elektronik", "PR", "Genel"])
                y_is = st.text_area("Yapılan Çalışma")
                if st.form_submit_button("Sisteme Kaydet 🚀"):
                    if y_isim and y_is:
                        tarih_kayit = datetime.now().strftime("%Y-%m-%d %H:%M")
                        sheet.values().append(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME, 
                                              valueInputOption="USER_ENTERED", body={"values": [[tarih_kayit, y_isim, y_ekip, y_is]]}).execute()
                        st.success("Rapor başarıyla eklendi!")
                        st.rerun()

    # --- 🗑️ 5. ADMİN: SİLME VE ARŞİVLEME ---
    if st.session_state['admin_logged_in']:
        st.divider()
        st.error("🚨 YÖNETİCİ SİLME PANELİ (Veriler Arşiv Sayfasına Taşınır)")
        if not df.empty:
            secenekler = [(i, f"{row[0]} - {row[1]}", row) for i, row in enumerate(values[1:])]
            silinecek = st.selectbox("Silinecek Kaydı Seç:", secenekler, format_func=lambda x: x[1])
            if st.button("Kayıdı Arşive Kaldır"):
                # Arşiv sayfasına ekle
                sheet.values().append(spreadsheetId=SPREADSHEET_ID, range=ARCHIVE_RANGE_NAME, 
                                      valueInputOption="USER_ENTERED", body={"values": [silinecek[2]]}).execute()
                # Ana sayfadan sil
                r_idx = silinecek[0] + 1
                b_update = {"requests": [{"deleteDimension": {"range": {"sheetId": 0, "dimension": "ROWS", "startIndex": r_idx, "endIndex": r_idx + 1}}}]}
                sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=b_update).execute()
                st.success("İşlem Başarılı!")
                st.rerun()

except Exception as e:
    st.error(f"Sistem Hatası: {e}")