import streamlit as st
import sqlite3
import pandas as pd
import cv2
import numpy as np
import fitz
import hashlib
import time
import datetime
import base64
import plotly.express as px

# --- 1. DATABASE & SESSION ---
def init_db():
    conn = sqlite3.connect('pemira_fti_v5.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (npm TEXT PRIMARY KEY, nama TEXT, region TEXT, kelas TEXT, 
                  password TEXT, foto_verif TEXT, status_vote INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS activity_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, npm TEXT, waktu TEXT, lokasi TEXT, aktivitas TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS votes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, pilihan TEXT, waktu TEXT)''')
    conn.commit()
    return conn

conn = init_db()

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user_aktif' not in st.session_state: st.session_state.user_aktif = None
if 'is_admin' not in st.session_state: st.session_state.is_admin = False

# --- 2. FUNGSI LOGIKA ---
def save_log(npm, aktivitas):
    c = conn.cursor()
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO activity_logs (npm, waktu, lokasi, aktivitas) VALUES (?,?,"Jakarta",?)', (npm, waktu, aktivitas))
    conn.commit()

# --- 3. HALAMAN ADMIN (BARU) ---
def show_admin_dashboard():
    st.title("Admin Control Panel")
    
    if st.sidebar.button("Logout Admin"):
        st.session_state.is_admin = False
        st.session_state.page = 'login'
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["Data Pemilih", "Log Aktivitas Global", "Statistik Suara"])

    with tab1:
        st.subheader("Daftar Mahasiswa Terdaftar")
        df_users = pd.read_sql_query("SELECT npm, nama, region, kelas, status_vote FROM users", conn)
        st.dataframe(df_users, use_container_width=True)
        
        # Ringkasan
        total = len(df_users)
        sudah = len(df_users[df_users['status_vote'] == 1])
        belum = total - sudah
        c1, c2, c3 = st.columns(3)
        c1.metric("Total User", total)
        c2.metric("Sudah Memilih", sudah)
        c3.metric("Belum Memilih", belum)

    with tab2:
        st.subheader("Audit Log Seluruh Sistem")
        df_logs = pd.read_sql_query("SELECT * FROM activity_logs ORDER BY id DESC", conn)
        st.table(df_logs.head(20))

    with tab3:
        st.subheader("Hasil Perhitungan Suara")
        df_votes = pd.read_sql_query("SELECT pilihan, waktu FROM votes", conn)
        if not df_votes.empty:
            fig = px.pie(df_votes, names='pilihan', title="Persentase Suara Masuk")
            st.plotly_chart(fig)
        else:
            st.info("Belum ada suara masuk.")

# --- 4. LOGIN DENGAN SELEKSI ADMIN ---
def show_login_page():
    st.header("Login Sistem")
    
    login_type = st.radio("Masuk Sebagai:", ["Mahasiswa", "Administrator"])
    user_in = st.text_input("NPM / Username")
    pass_in = st.text_input("Password", type='password')

    if st.button("Login"):
        if login_type == "Administrator":
            # Password Admin statis untuk demo
            if user_in == "admin" and pass_in == "admin123":
                st.session_state.is_admin = True
                st.session_state.page = 'admin'
                st.rerun()
            else:
                st.error("Kredensial Admin Salah")
        else:
            # Login Mahasiswa
            hashed_pw = hashlib.sha256(pass_in.encode()).hexdigest()
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE npm=? AND password=?', (user_in, hashed_pw))
            user = c.fetchone()
            if user:
                st.session_state.user_aktif = user_in
                save_log(user_in, "Login Berhasil")
                st.session_state.page = 'analytics' if user[6] == 1 else 'voting'
                st.rerun()
            else:
                st.error("NPM atau Password salah")

# --- 5. HALAMAN LAIN (RINGKASAN) ---
def show_register_page():
    st.header("Registrasi Mahasiswa")
    # ... (Gunakan kode registrasi sebelumnya) ...
    if st.button("Kembali"): st.session_state.page = 'login'; st.rerun()

def show_my_account():
    st.header("Akun Saya")
    # ... (Gunakan kode my_account sebelumnya) ...
    if st.sidebar.button("Kembali ke Utama"): st.session_state.page = 'analytics'; st.rerun()

# --- ROUTER ---
if st.session_state.page == 'admin' and st.session_state.is_admin:
    show_admin_dashboard()
elif st.session_state.page == 'login':
    show_login_page()
elif st.session_state.page == 'register':
    show_register_page()
# ... (tambahkan elif untuk voting, analytics, dan my_account sesuai kode sebelumnya)