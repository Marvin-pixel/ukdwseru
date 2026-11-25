from pathlib import Path

import streamlit as st

from auth import require_login, logout_button, current_user

# logo.png diletakkan di folder yang sama dengan file ini
LOGO_PATH = Path(__file__).parent / "logo.png"

st.set_page_config(
    page_title="Anies - Anime List",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else "🎌",
    layout="wide",
)

# Wajib dipanggil sebelum konten apa pun: jika belum login, tampil form login lalu berhenti.
require_login()

# ---- Mulai dari sini hanya dilihat user yang sudah login ----
if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), width=120)
logout_button()

page = st.sidebar.radio("Menu", ["Home", "Explore", "Statistics", "AI Recommendation"])

user = current_user()
st.title(f"Halo, {user['username']}! 👋")

if page == "Home":
    st.header("Temukan Anime Favoritmu.")
    st.info("Dashboard: anime populer & skor tinggi dari MyAnimeList API.")
elif page == "Explore":
    st.header("Jelajahi cerita tanpa batas.")
    st.info("Pencarian, filter genre/tahun/skor, dan sorting.")
elif page == "Statistics":
    st.header("Dunia anime dalam angka.")
    st.info("Grafik Plotly: jumlah anime per genre & skor vs popularitas.")
else:
    st.header("Cerita berikutnya, lebih personal.")
    st.info("Rekomendasi berbasis Gemini API.")