import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from datetime import datetime
import pandas as pd
import plotly.express as px

# --- AYARLAR ---
SPREADSHEET_ID = '1w7_IRXQ9I2eAFLlhbCqr-Q_R5Ww752zjs8CTNNbfRgI' 
RANGE_NAME = 'Sayfa1!A:E'
ARCHIVE_RANGE_NAME = 'Arsiv!A:E' # Silinenler buraya gidecek

# Şifre Yönetimi
try:
    ADMIN_SIFRESI = st.secrets["admin_sifresi"]
except:
    ADMIN_SIFRESI = "teknofest2026"

# --- BAĞLANTI FONKSİYONU ---
def get_google_sheet_service():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    if os.path.exists("secrets.json"):
        creds = service_account.Credentials.from_service_account_file("secrets.json", scopes=SCOPES)
    elif "gcp_service_account" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    else:
        st.error("🚨 HATA: Robot anahtarı bulunamadı!")
        st.stop()
    return build('sheets', 'v4', credentials=creds)

# --- SAYFA YAPISI ---
st.set_page_config(page_title="Teknofest Yarış Paneli", page_icon="🏆", layout="wide")

# --- YAN MENÜ (ADMİN) ---
st.sidebar.title("🔧 Kontrol Merkezi")

if 'admin_logged_in' not in st.session_state:
    st.session_state['admin_logged_in'] = False

if not st.session_state['admin_logged_in']:
    st.sidebar.info("Rapor girmek serbest. Silmek için giriş yap.")
    sifre_girilen = st.sidebar.text_input("Admin Şifresi", type="password")
    if st.sidebar.button("Giriş Yap"):
        if sifre_girilen == ADMIN_SIFRESI:
            st.session_state['admin_logged_in'] = True
            st.sidebar.success("Hoş geldin Kaptan! 👨‍✈️")
            st.rerun()
        else:
            st.sidebar.error("Yanlış şifre!")
else:
    st.sidebar.success("✅ Admin Modu Aktif")
    if st.sidebar.button("Çıkış Yap"):
        st.session_state['admin_logged_in'] = False
        st.rerun()

# --- ANA EKRAN ---
st.title("Teknofest Takım Yarışı 🏁")

try:
    service = get_google_sheet_service()
    sheet = service.spreadsheets()

    # VERİLERİ ÇEK
    result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        st.warning("Henüz hiç kayıt yok. İlk raporu sen gir!")
    else:
        # Veriyi Pandas'a yükle
        df = pd.DataFrame(values[1:], columns=["Tarih", "İsim", "Alan", "İş"])
        
        # Tarih sütununu gerçek tarih formatına çevir (Analiz için şart)
        df["Tarih_Formatli"] = pd.to_datetime(df["Tarih"])

        # --- 📊 BÖLÜM 1: ÇİFTE YARIŞ GRAFİKLERİ ---
        
        # BUGÜNÜN ve BU AYIN Tarihini al
        bugun = datetime.now().date()
        bu_ay = datetime.now().month

        # Filtreleme Yapıyoruz
        df_gunluk = df[df["Tarih_Formatli"].dt.date == bugun]
        df_aylik = df[df["Tarih_Formatli"].dt.month == bu_ay]

        col_g1, col_g2 = st.columns(2)

        # 1. GRAFİK: GÜNLÜK PERFORMANS
        with col_g1:
            st.subheader("☀️ Günün Lideri")
            if not df_gunluk.empty:
                counts_gun = df_gunluk["Alan"].value_counts().reset_index()
                counts_gun.columns = ["Alan", "Rapor Sayısı"]
                fig_gun = px.bar(counts_gun, x="Alan", y="Rapor Sayısı", color="Alan", 
                                 title="Bugünkü Performans (Her gece sıfırlanır)",
                                 color_discrete_map={"Mekanik": "#EF553B", "Elektronik": "#636EFA", "PR": "#00CC96", "Genel": "#AB63FA"})
                st.plotly_chart(fig_gun, use_container_width=True)
            else:
                st.info("Bugün henüz kimse çalışmamış. İlk sen ol! 🚀")

        # 2. GRAFİK: AYLIK PERFORMANS
        with col_g2:
            st.subheader("📅 Ayın Şampiyonu")
            if not df_aylik.empty:
                counts_ay = df_aylik["Alan"].value_counts().reset_index()
                counts_ay.columns = ["Alan", "Rapor Sayısı"]
                fig_ay = px.pie(counts_ay, names="Alan", values="Rapor Sayısı", hole=0.4,
                                title="Bu Ayın Genel Dağılımı")
                st.plotly_chart(fig_ay, use_container_width=True)
            else:
                st.info("Bu ay veri yok.")

        st.divider()

        # --- 📋 BÖLÜM 2: GÜN GÜN AYRILMIŞ RAPORLAR ---
        st.subheader("📝 Rapor Akışı")
        
        # Filtreleme Kutusu
        secilen_filtre = st.selectbox("Ekip Filtrele:", ["Tümü", "Mekanik", "Elektronik", "PR", "Genel"])
        
        # Tabloyu Tarihe Göre Sırala (En yeni en üstte)
        df_sorted = df.sort_values(by="Tarih_Formatli", ascending=False)

        if secilen_filtre != "Tümü":
            df_goster = df_sorted[df_sorted["Alan"] == secilen_filtre]
        else:
            df_goster = df_sorted

        # Tabloyu Göster (Orijinal sütunlarla)
        st.dataframe(df_goster[["Tarih", "İsim", "Alan", "İş"]], use_container_width=True, hide_index=True)


    # --- ✍️ BÖLÜM 3: RAPOR EKLEME ---
    st.divider()
    st.subheader("➕ Yeni Rapor Ekle")
    with st.form("kayit_formu", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            isim = st.text_input("İsim Soyisim")
        with col2:
            alan = st.selectbox("Hangi Ekip?", ["Mekanik", "Elektronik", "PR", "Genel"])
        is_tanimi = st.text_area("Yapılan İş")
        
        if st.form_submit_button("Kaydet 💾"):
            if isim and is_tanimi:
                tarih_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                # Excel'e gidecek ham veri
                yeni_veri = [[tarih_str, isim, alan, is_tanimi]]
                sheet.values().append(
                    spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME,
                    valueInputOption="USER_ENTERED", body={"values": yeni_veri}
                ).execute()
                st.success("Kaydedildi!")
                st.rerun()
            else:
                st.warning("Boş alan bırakma!")

    # --- 🗑️ BÖLÜM 4: GÜVENLİ SİLME (ARŞİVLEME) ---
    if st.session_state['admin_logged_in']:
        st.divider()
        st.error("🚨 YÖNETİCİ PANELİ (Silinenler Arşive Gider)")
        
        if not df.empty:
            secenekler = []
            for i, row in enumerate(values[1:]): 
                gosterim = f"{row[0]} - {row[1]} ({row[2]})"
                secenekler.append((i, gosterim, row)) # Row verisini de saklıyoruz
            
            silinecek = st.selectbox("Silinecek satırı seç:", secenekler, format_func=lambda x: x[1])
            
            if st.button("Seçili Kaydı ARŞİVE KALDIR 📦"):
                # 1. Önce Arşiv Sayfasına Ekle
                silinecek_veri = [silinecek[2]] # Satırın kendisi
                sheet.values().append(
                    spreadsheetId=SPREADSHEET_ID, range=ARCHIVE_RANGE_NAME,
                    valueInputOption="USER_ENTERED", body={"values": silinecek_veri}
                ).execute()
                
                # 2. Sonra Ana Listeden Sil
                row_index = silinecek[0] + 1
                batch_update_body = {
                    "requests": [{
                        "deleteDimension": {
                            "range": {
                                "sheetId": 0, 
                                "dimension": "ROWS",
                                "startIndex": row_index, 
                                "endIndex": row_index + 1
                            }
                        }
                    }]
                }
                sheet.batchUpdate(spreadsheetId=SPREADSHEET_ID, body=batch_update_body).execute()
                st.success("Kayıt ana listeden silindi ve Arşiv sayfasına taşındı! ✅")
                st.rerun()

except Exception as e:
    st.error(f"Bir hata oluştu: {e}")