import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

# --- AYARLAR ---
TAKIM_UYELERI = ["Pırlant", "Ali", "Veli", "Zeynep", "Merve"] 
ALANLAR = ["Mekanik", "Elektronik", "Yazılım", "PR/Sponsorluk", "Genel"]
ADMIN_SIFRESI = "tekno123" 

st.set_page_config(page_title="Teknofest Takip", page_icon="🚀", layout="wide")

# --- AKILLI BAĞLANTI (Hem PC Hem Bulut) ---
@st.cache_resource
def baglanti_kur():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # 1. Önce Streamlit Cloud'daki gizli ayarlara bakar
    if "gcp_service_account" in st.secrets:
        creds_dict = dict(st.secrets["gcp_service_account"])
        # st.secrets bazen özel formatta döner, onu düzeltiyoruz
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    # 2. Bulamazsa bilgisayardaki secrets.json dosyasına bakar
    else:
        creds = ServiceAccountCredentials.from_json_keyfile_name("secrets.json", scope)
    
    client = gspread.authorize(creds)
    sheet = client.open("Teknofest_Veritabani").sheet1 
    return sheet

def veri_ekle(tarih, isim, alan, is_detay):
    try:
        sheet = baglanti_kur()
        sheet.append_row([tarih, isim, alan, is_detay])
        return True
    except Exception as e:
        st.error(f"Hata: {e}")
        return False

def son_satiri_sil():
    try:
        sheet = baglanti_kur()
        son_satir = len(sheet.get_all_values())
        if son_satir > 1:
            sheet.delete_rows(son_satir)
            return True
        return False
    except:
        return False

# --- UYGULAMA ---
st.title("☁️ Teknofest Online Takip Sistemi")

st.sidebar.title("Menü")
secim = st.sidebar.radio("Git:", ["📝 Rapor Ekle", "📂 Raporları İncele"])
st.sidebar.markdown("---")
girilen_sifre = st.sidebar.text_input("Yönetici Şifresi", type="password")

if girilen_sifre == ADMIN_SIFRESI:
    st.sidebar.success("🔓 Yönetici Modu Aktif")

if secim == "📝 Rapor Ekle":
    col1, col2 = st.columns(2)
    with col1:
        isim = st.selectbox("İsim:", TAKIM_UYELERI)
    with col2:
        alan = st.selectbox("Alan:", ALANLAR)
    yapilan_is = st.text_area("Ne yaptın?", height=100)
    
    if st.button("Kaydet", type="primary"):
        if yapilan_is:
            tarih = datetime.now().strftime("%d-%m-%Y %H:%M")
            if veri_ekle(tarih, isim, alan, yapilan_is):
                st.success("Kaydedildi!")
                st.balloons()

elif secim == "📂 Raporları İncele":
    if st.button("🔄 Yenile"):
        st.rerun()

    if girilen_sifre == ADMIN_SIFRESI:
        if st.button("🗑️ Son Raporu Sil"):
            if son_satiri_sil():
                st.success("Silindi!")
                st.rerun()

    try:
        sheet = baglanti_kur()
        data = sheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            filtre = st.selectbox("Filtrele:", ["Tümü"] + ALANLAR)
            if filtre != "Tümü":
                df = df[df["Alan"] == filtre]
            st.dataframe(df.iloc[::-1], use_container_width=True)
        else:
            st.info("Henüz veri yok.")
    except:
        st.warning("Veritabanına bağlanılamadı. Ayarları kontrol edin.")