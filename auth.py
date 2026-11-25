"""
auth.py - Modul login & registrasi untuk Anies (Anime List)

Fitur:
- Registrasi akun (username, email, password)
- Login dengan session_state
- Password di-hash (PBKDF2-HMAC-SHA256 + salt acak), tidak disimpan polos
- Penguncian sementara setelah beberapa kali gagal login
- require_login() untuk melindungi halaman lain
- Tombol logout
"""

import hashlib
import hmac
import os
import re
import time
from pathlib import Path

import streamlit as st

import storage

# logo.png diletakkan di folder yang sama dengan auth.py
LOGO_PATH = Path(__file__).parent / "logo.png"
PBKDF2_ITERATIONS = 200_000
MAX_FAILED_ATTEMPTS = 5
LOCK_SECONDS = 30


def _stretch():
    """Argumen lebar penuh yang kompatibel dengan versi Streamlit lama & baru."""
    try:
        major, minor = (int(x) for x in st.__version__.split(".")[:2])
        if (major, minor) >= (1, 49):
            return {"width": "stretch"}
    except ValueError:
        pass
    return {"use_container_width": True}



# ---------------------------------------------------------------- Database
def init_db():
    storage.init_db()


# ---------------------------------------------------------------- Password
def _hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )


# ---------------------------------------------------------------- Logika akun
def register_user(username: str, email: str, password: str, confirm: str):
    """Mengembalikan (berhasil: bool, pesan: str)."""
    username = username.strip()
    email = email.strip().lower()

    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
        return False, "Username 3-20 karakter, hanya huruf, angka, dan underscore."
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return False, "Format email tidak valid."
    if len(password) < 8:
        return False, "Password minimal 8 karakter."
    if password != confirm:
        return False, "Konfirmasi password tidak cocok."

    salt = os.urandom(16)
    pw_hash = _hash_password(password, salt)

    if not storage.create_user(username, email, pw_hash, salt):
        return False, "Username atau email sudah terdaftar."
    return True, "Akun berhasil dibuat. Silakan masuk."


def authenticate(username: str, password: str):
    """Mengembalikan dict user jika valid, None jika gagal."""
    row = storage.get_user(username)

    if row is None:
        # Tetap hitung hash agar waktu respons tidak membocorkan keberadaan akun
        _hash_password(password, b"\x00" * 16)
        return None

    if hmac.compare_digest(_hash_password(password, row["salt"]), row["password_hash"]):
        return {"id": row["id"], "username": row["username"], "email": row["email"]}
    return None


# ---------------------------------------------------------------- Session
def is_logged_in() -> bool:
    return st.session_state.get("user") is not None


def current_user():
    return st.session_state.get("user")


def logout():
    st.session_state["user"] = None
    st.rerun()


def logout_button(location=None):
    """Tampilkan info user + tombol keluar (default: sidebar)."""
    target = location or st.sidebar
    user = current_user()
    if user:
        target.markdown(f"Masuk sebagai **{user['username']}**")
        if target.button("Keluar", **_stretch()):
            logout()


def require_login():
    """Panggil di awal setiap halaman. Menampilkan login jika belum masuk."""
    init_db()
    if not is_logged_in():
        login_page()
        st.stop()


# ---------------------------------------------------------------- UI
_CSS = """
<style>
.anies-title {font-size: 1.6rem; font-weight: 800; text-align: center; margin: .25rem 0 0 0;}
.anies-sub {text-align: center; opacity: .7; margin-bottom: 1.25rem;}
[data-testid="stImage"] img {border-radius: 50%;}
</style>
"""


def login_page():
    st.markdown(_CSS, unsafe_allow_html=True)
    st.session_state.setdefault("failed_attempts", 0)
    st.session_state.setdefault("lock_until", 0.0)

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        # Logo aplikasi (di tengah)
        _, logo_col, _ = st.columns([1, 1.2, 1])
        with logo_col:
            if LOGO_PATH.exists():
                st.image(str(LOGO_PATH), width=180)
            else:
                st.markdown('<p class="anies-title">anies</p>', unsafe_allow_html=True)
        st.markdown(
            '<p class="anies-title">Selamat datang di Anies</p>'
            '<p class="anies-sub">Masuk untuk menemukan anime favoritmu.</p>',
            unsafe_allow_html=True,
        )
        tab_login, tab_register = st.tabs(["Masuk", "Daftar"])

        # ---- Tab Masuk
        with tab_login:
            with st.form("login_form"):
                identity = st.text_input("Username atau email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button(
                    "Masuk", **_stretch(), type="primary"
                )

            if submitted:
                remaining = st.session_state["lock_until"] - time.time()
                if remaining > 0:
                    st.error(f"Terlalu banyak percobaan. Coba lagi dalam {int(remaining) + 1} detik.")
                elif not identity or not password:
                    st.warning("Isi username/email dan password.")
                else:
                    user = authenticate(identity, password)
                    if user:
                        st.session_state["user"] = user
                        st.session_state["failed_attempts"] = 0
                        st.rerun()
                    else:
                        st.session_state["failed_attempts"] += 1
                        if st.session_state["failed_attempts"] >= MAX_FAILED_ATTEMPTS:
                            st.session_state["lock_until"] = time.time() + LOCK_SECONDS
                            st.session_state["failed_attempts"] = 0
                            st.error(f"Terlalu banyak percobaan. Dikunci selama {LOCK_SECONDS} detik.")
                        else:
                            st.error("Username/email atau password salah.")

        # ---- Tab Daftar
        with tab_register:
            with st.form("register_form", clear_on_submit=False):
                new_username = st.text_input("Username")
                new_email = st.text_input("Email")
                new_password = st.text_input("Password (min. 8 karakter)", type="password")
                confirm = st.text_input("Konfirmasi password", type="password")
                reg_submitted = st.form_submit_button(
                    "Buat akun", **_stretch(), type="primary"
                )

            if reg_submitted:
                ok, msg = register_user(new_username, new_email, new_password, confirm)
                (st.success if ok else st.error)(msg)
