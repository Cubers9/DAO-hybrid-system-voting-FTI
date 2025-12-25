import streamlit as st
import sqlite3
import pandas as pd
import cv2
import numpy as np
import fitz  # PyMuPDF
import hashlib
import time
import datetime
import base64

# --- 1. KONFIGURASI DATABASE ---
def init_db():
    conn = sqlite3.connect('pemira_fti.db', check_same_thread=False)
    c = conn.cursor()
    # Tabel User: Menambahkan kolom foto_verif
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (npm TEXT PRIMARY KEY, nama TEXT, region TEXT, kelas TEXT, 
                  password TEXT, foto_verif TEXT, status_vote INTEGER DEFAULT 0)''')
    # Tabel Activity Log
    c.execute('''CREATE TABLE IF NOT EXISTS activity_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, npm TEXT, 
                  waktu TEXT, lokasi TEXT, aktivitas TEXT)''')
    # Tabel Hasil Suara
    c.execute('''CREATE TABLE IF NOT EXISTS votes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, pilihan TEXT, waktu TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- 2. SESSION STATE MANAGEMENT ---
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'user_aktif' not in st.session_state:
    st.session_state.user_aktif = None

# --- 3. FUNGSI LOGIKA & UTILITY ---
def save_log(npm, aktivitas):
    c = conn.cursor()
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lokasi = "Jakarta, Indonesia (IP-Based)" # Simulasi Lokasi
    c.execute('INSERT INTO activity_logs (npm, waktu, lokasi, aktivitas) VALUES (?,?,?,?)', 
             (npm, waktu, lokasi, aktivitas))
    conn.commit()

def encode_image(image_file):
    if image_file is not None:
        return base64.b64encode(image_file.getvalue()).decode()
    return None

def validate_face(image_file):
    if image_file is None: return False
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    return len(faces) > 0

def verify_krs(npm, nama, krs_file):
    krs_file.seek(0)
    with fitz.open(stream=krs_file.read(), filetype="pdf") as doc:
        text = "".join([page.get_text() for page in doc]).upper()
    return (npm in text and nama.upper() in text)

# --- 4. UI COMPONENTS (HALAMAN-HALAMAN) ---

def show_register_page():
    st.header("Registrasi Akun Pemilih")
    st.caption("Lengkapi data diri dan verifikasi biometrik untuk mendapatkan hak akses.")
    
    col1, col2 = st.columns(2)
    with col1:
        new_nama = st.text_input("Nama Lengkap")
        new_npm = st.text_input("NPM")
        new_region = st.selectbox("Region", ["Region 1", "Region 2", "Region 3"])
        new_kelas = st.text_input("Kelas")
        new_pw = st.text_input("Buat Password", type='password')
        krs_file = st.file_uploader("Upload KRS (PDF)", type=["pdf"])
    
    with col2:
        selfie_file = st.camera_input("Ambil Foto Verifikasi")

    if st.button("VERIFIKASI & DAFTAR"):
        if new_nama and new_npm and new_pw and krs_file and selfie_file:
            if verify_krs(new_npm, new_nama, krs_file) and validate_face(selfie_file):
                try:
                    hashed_pw = hashlib.sha256(new_pw.encode()).hexdigest()
                    foto_base64 = encode_image(selfie_file)
                    c = conn.cursor()
                    c.execute('INSERT INTO users VALUES (?,?,?,?,?,?,0)', 
                             (new_npm, new_nama, new_region, new_kelas, hashed_pw, foto_base64))
                    conn.commit()
                    save_log(new_npm, "Registrasi Akun Baru")
                    st.success("Akun berhasil dibuat. Silakan Login.")
                    time.sleep(1)
                    st.session_state.page = 'login'
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("NPM sudah terdaftar.")
            else:
                st.error("Data KRS tidak cocok atau Wajah tidak terdeteksi.")
        else:
            st.warning("Mohon isi semua field.")
    
    if st.button("Sudah punya akun? Login"):
        st.session_state.page = 'login'
        st.rerun()

def show_login_page():
    st.header("Login Sistem Pemira")
    login_npm = st.text_input("NPM")
    login_pw = st.text_input("Password", type='password')

    if st.button("Masuk"):
        hashed_pw = hashlib.sha256(login_pw.encode()).hexdigest()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE npm=? AND password=?', (login_npm, hashed_pw))
        user = c.fetchone()
        
        if user:
            st.session_state.user_aktif = login_npm
            save_log(login_npm, "Login ke Sistem")
            st.session_state.page = 'analytics' if user[6] == 1 else 'voting'
            st.rerun()
        else:
            st.error("NPM atau Password salah.")

    if st.button("Belum punya akun? Daftar"):
        st.session_state.page = 'register'
        st.rerun()

def show_my_account():
    st.header("Informasi Akun & Log Aktivitas")
    c = conn.cursor()
    c.execute('SELECT nama, npm, region, kelas, foto_verif FROM users WHERE npm=?', (st.session_state.user_aktif,))
    u = c.fetchone()

    col1, col2 = st.columns([1, 2])
    with col1:
        if u[4]:
            st.image(base64.b64decode(u[4]), caption="Foto Verifikasi", use_container_width=True)
        st.write(f"Nama: **{u[0]}**")
        st.write(f"NPM: **{u[1]}**")
        st.write(f"Kelas: **{u[3]}**")
    
    with col2:
        st.subheader("Log Aktivitas Terbaru")
        logs = pd.read_sql_query(f"SELECT waktu, lokasi, aktivitas FROM activity_logs WHERE npm='{u[1]}' ORDER BY id DESC", conn)
        st.dataframe(logs, use_container_width=True)

    if st.button("Kembali"):
        st.session_state.page = 'analytics'
        st.rerun()

def show_voting_page():
    st.header("Bilik Suara")
    st.info(f"Pemilih Aktif: {st.session_state.user_aktif}")
    st.write("Silakan pilih pasangan calon di bawah ini. Pilihan Anda bersifat rahasia dan permanen.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div style="border:2px solid #f0f2f6; border-radius:10px; padding:20px; text-align:center">
            <h3>PASLON 01</h3>
            <h1 style="color:#FF4B4B">Cipuy & Ketoprak</h1>
            <p>Visi: Kenyang dan Bahagia</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("PILIH 01", use_container_width=True):
            simpan_vote("Cipuy & Ketoprak")
            
    with col2:
        st.markdown("""
        <div style="border:2px solid #f0f2f6; border-radius:10px; padding:20px; text-align:center">
            <h3>PASLON 02</h3>
            <h1 style="color:#1C83E1">Ceka & Warkun</h1>
            <p>Visi: Nongkrong Berfaedah</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("PILIH 02", use_container_width=True):
            simpan_vote("Ceka & Warkun")
def simpan_vote(pilihan):
    c = conn.cursor()
    c.execute('INSERT INTO votes (pilihan, waktu) VALUES (?,?)', (pilihan, time.ctime()))
    c.execute('UPDATE users SET status_vote = 1 WHERE npm = ?', (st.session_state.user_aktif,))
    conn.commit()
    save_log(st.session_state.user_aktif, f"Memberikan Suara pada {pilihan}")
    st.session_state.page = 'analytics'
    st.rerun()

def show_analytics_page():
    st.header("Hasil Pemilihan Real-Time")
    
    # Sidebar Navigation
    st.sidebar.write(f"User: {st.session_state.user_aktif}")
    if st.sidebar.button("My Account"):
        st.session_state.page = 'my_account'
        st.rerun()
    if st.sidebar.button("Logout"):
        st.session_state.user_aktif = None
        st.session_state.page = 'login'
        st.rerun()

    df = pd.read_sql_query("SELECT * FROM votes", conn)
    if not df.empty:
        st.bar_chart(df['pilihan'].value_counts())
        st.write("Daftar Transaksi Suara (Anonim)")
        # Masking NPM untuk keamanan
        df_display = df.copy()
        df_display['id_transaksi'] = df_display.index + 1000
        st.dataframe(df_display[['id_transaksi', 'pilihan', 'waktu']], use_container_width=True)
    else:
        st.info("Belum ada suara masuk.")

# --- 5. ROUTER ---
if st.session_state.page == 'register': show_register_page()
elif st.session_state.page == 'login': show_login_page()
elif st.session_state.page == 'voting': show_voting_page()
elif st.session_state.page == 'analytics': show_analytics_page()
elif st.session_state.page == 'my_account': show_my_account()