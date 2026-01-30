import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from datetime import datetime
import pandas as pd  # <-- YENİ: Tablo filtreleme için eklendi

# --- AYARLAR ---
SPREADSHEET_ID = '1w7_IRXQ9I2eAFLlhbCqr-Q_R5Ww752zjs8CTNNbfRgI' 
RANGE_NAME = 'Sayfa1!A:E' 
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
st.set_page_config(page_title="Teknofest Takip", page_icon="🚀")

# --- GİRİŞ KONTROLÜ ---
if 'giris_yapildi' not in st.session_state:
    st.session_state['giris_yapildi'] = False

if not st.session_state['giris_yapildi']:
    st.title("🔒 Admin Girişi")
    sifre = st.text_input("Şifre:", type="password")
    if st.button("Giriş Yap"):
        if sifre == ADMIN_SIFRESI:
            st.session_state['giris_yapildi'] = True
            st.success("Giriş Başarılı!")
            st.rerun()
        else:
            st.error("❌ Hatalı Şifre")
else:
    # --- UYGULAMA İÇERİĞİ ---
    if st.sidebar.button("Çıkış Yap"):
        st.session_state['giris_yapildi'] = False
        st.rerun()

    st.title("Teknofest Görev Takip Sistemi 🚀")

    try:
        service = get_google_sheet_service()
        sheet = service.spreadsheets()

        # 1. VERİLERİ OKU
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
        values = result.get('values', [])

        st.subheader("📋 Mevcut Görevler")
        
        if not values:
            st.info("Kayıt yok.")
        else:
            # --- YENİ: FİLTRELEME BÖLÜMÜ ---
            # Veriyi Pandas DataFrame'e çeviriyoruz (Daha kolay yönetmek için)
            # Sütun isimlerini veriyoruz: Tarih, İsim, Alan, İş
            df = pd.DataFrame(values, columns=["Tarih", "İsim", "Alan", "İş"])

            # Filtreleme Kutusu
            alanlar = ["Tümü"] + ["Yazılım", "Mekanik", "Elektronik", "Tasarım", "Diğer"]
            secilen_filtre = st.selectbox("🔍 Alana Göre Filtrele:", alanlar)

            # Filtreleme Mantığı
            if secilen_filtre != "Tümü":
                # Sadece seçilen alana eşit olan satırları getir
                df_goster = df[df["Alan"] == secilen_filtre]
            else:
                # Hepsini göster
                df_goster = df

            # Tabloyu göster (use_container_width=True tam ekran yapar)
            st.dataframe(df_goster, use_container_width=True)


        # 2. EKLEME BÖLÜMÜ
        st.divider()
        st.subheader("✍️ Yeni İş Ekle")
        with st.form("kayit_formu", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                isim = st.text_input("İsim Soyisim")
            with col2:
                alan = st.selectbox("Alan", ["Yazılım", "Mekanik", "Elektronik", "Tasarım", "Diğer"])
            is_tanimi = st.text_area("Yapılan İş")
            
            if st.form_submit_button("Kaydet"):
                tarih = datetime.now().strftime("%Y-%m-%d %H:%M")
                yeni_veri = [[tarih, isim, alan, is_tanimi]]
                sheet.values().append(
                    spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME,
                    valueInputOption="USER_ENTERED", body={"values": yeni_veri}
                ).execute()
                st.success("Eklendi!")
                st.rerun()

        # 3. SİLME BÖLÜMÜ
        st.divider()
        st.subheader("🗑️ Kayıt Sil")
        
        if len(values) > 0:
            secenekler = []
            # enumerate ile index numarasını alıyoruz (Silme işlemi için lazım)
            for i, row in enumerate(values):
                # Hata almamak için kontrol: row[1] isim var mı?
                isim_goster = row[1] if len(row) > 1 else "İsimsiz"
                is_goster = row[3] if len(row) > 3 else "..."
                gosterim = f"{isim_goster} ({is_goster})"
                secenekler.append((i, gosterim))
            
            secilen_satir = st.selectbox("Silinecek Kaydı Seçin:", options=secenekler, format_func=lambda x: x[1])
            
            if st.button("Seçili Kaydı Sil ❌"):
                row_index = secilen_satir[0] 
                
                # Google Sheets API Silme İsteği
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
                st.warning("Kayıt Silindi!")
                st.rerun()
        else:
            st.info("Silinecek kayıt yok.")

    except Exception as e:
        st.error(f"Hata: {e}")