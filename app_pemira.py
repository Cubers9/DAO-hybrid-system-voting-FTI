import streamlit as st
import sqlite3
import pandas as pd
import cv2
import numpy as np
import fitz
import hashlib
import time

# --- 1. KONEKSI DATABASE ---
def init_db():
    conn = sqlite3.connect('pemira_fti_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (npm TEXT PRIMARY KEY, nama TEXT, region TEXT, kelas TEXT, 
                  password TEXT, status_vote INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS votes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, pilihan TEXT, waktu TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# Session State
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'user_aktif' not in st.session_state:
    st.session_state.user_aktif = None

# --- 2. CSS UNTUK UI FORMAL (HILANGKAN EMOTICON) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #004a99; color: white; }
    .stTextInput>div>div>input { border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNGSI LOGIKA (VALIDASI) ---
def validate_selfie_opencv(image_file):
    if image_file is None: return False, "Face data missing"
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
    return (True, "Ok") if len(faces) > 0 else (False, "Face not detected")

def verify_krs_logic(npm, nama, krs_file):
    krs_file.seek(0)
    with fitz.open(stream=krs_file.read(), filetype="pdf") as doc:
        text = "".join([page.get_text() for page in doc]).upper()
    return (npm in text and nama.upper() in text and "2024" in text)

# --- 4. HALAMAN REGISTRASI ---
def show_register_page():
    st.header("Form Registrasi Mahasiswa")
    st.caption("Verifikasi identitas melalui dokumen KRS dan Biometrik Wajah")
    
    col1, col2 = st.columns(2)
    with col1:
        new_nama = st.text_input("Nama Lengkap")
        new_npm = st.text_input("NPM")
        new_region = st.selectbox("Region Kampus", ["Region 1", "Region 2", "Region 3"])
        new_kelas = st.text_input("Kelas")
        new_pw = st.text_input("Password", type='password')
        krs_file = st.file_uploader("Dokumen KRS (PDF)", type=["pdf"])
    
    with col2:
        selfie_file = st.camera_input("Scanner Biometrik")

    if st.button("PROSES VERIFIKASI"):
        if new_nama and new_npm and new_pw and krs_file and selfie_file:
            krs_valid = verify_krs_logic(new_npm, new_nama, krs_file)
            face_valid, msg = validate_selfie_opencv(selfie_file)
            
            if krs_valid and face_valid:
                try:
                    c = conn.cursor()
                    hashed_pw = hashlib.sha256(new_pw.encode()).hexdigest()
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,0)', 
                             (new_npm, new_nama, new_region, new_kelas, hashed_pw))
                    conn.commit()
                    st.success("Registrasi Berhasil. Akun Anda telah diverifikasi sistem.")
                    time.sleep(1)
                    st.session_state.page = 'login'
                    st.rerun()
                except:
                    st.error("NPM sudah terdaftar di sistem.")
            else:
                st.error("Verifikasi Gagal: Data dokumen atau wajah tidak valid.")

# --- 5. HALAMAN LOGIN ---
def show_login_page():
    st.header("Login Pemira FTI")
    login_npm = st.text_input("Username (NPM)")
    login_pw = st.text_input("Password", type='password')

    if st.button("Masuk Ke Sistem"):
        hashed_pw = hashlib.sha256(login_pw.encode()).hexdigest()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE npm=? AND password=?', (login_npm, hashed_pw))
        user = c.fetchone()
        
        if user:
            st.session_state.user_aktif = login_npm
            st.session_state.page = 'analytics' if user[5] == 1 else 'voting'
            st.rerun()
        else:
            st.error("Kredensial tidak ditemukan.")

    if st.button("Belum terdaftar? Buat Akun"):
        st.session_state.page = 'register'
        st.rerun()

# --- 6. HALAMAN VOTING ---
def show_voting_page():
    st.header("Bilik Suara Digital")
    st.write(f"ID Pemilih: {st.session_state.user_aktif}")
    
    st.subheader("Daftar Kandidat")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Paslon 01")
        if st.button("PILIH PASLON 01"):
            simpan_suara("Kandidat 01")
    with col2:
        st.markdown("### Paslon 02")
        if st.button("PILIH PASLON 02"):
            simpan_suara("Kandidat 02")

def simpan_suara(pilihan):
    c = conn.cursor()
    c.execute('INSERT INTO votes (pilihan, waktu) VALUES (?,?)', (pilihan, time.ctime()))
    c.execute('UPDATE users SET status_vote = 1 WHERE npm = ?', (st.session_state.user_aktif,))
    conn.commit()
    st.session_state.page = 'analytics'
    st.rerun()

# --- 7. HALAMAN ANALYTICS ---
def show_analytics_page():
    st.header("Dashboard Hasil Pemilihan")
    if st.sidebar.button("Keluar"):
        st.session_state.page = 'login'
        st.session_state.user_aktif = None
        st.rerun()

    df = pd.read_sql_query("SELECT * FROM votes", conn)
    if not df.empty:
        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Total Partisipasi", len(df))
        
        # Menggunakan Bar Chart Formal
        st.bar_chart(df['pilihan'].value_counts())
    else:
        st.info("Menunggu data suara masuk.")

# ROUTER
if st.session_state.page == 'register': show_register_page()
elif st.session_state.page == 'login': show_login_page()
elif st.session_state.page == 'voting': show_voting_page()
elif st.session_state.page == 'analytics': show_analytics_page()