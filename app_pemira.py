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
    conn = sqlite3.connect('pemira_fti_v6.db', check_same_thread=False)
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

# --- 2. FUNGSI LOG ---
def save_log(npm, aktivitas):
    c = conn.cursor()
    waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('INSERT INTO activity_logs (npm, waktu, lokasi, aktivitas) VALUES (?,?,"Jakarta",?)', (npm, waktu, aktivitas))
    conn.commit()

# --- 3. HALAMAN LOGIN (LOGIKA PINTU RAHASIA) ---
def show_login_page():
    st.header("Login Sistem Pemira")
    
    login_npm = st.text_input("NPM / Username")
    login_pw = st.text_input("Password", type='password')

    if st.button("Masuk"):
        # CEK APAKAH INI ADMIN (PINTU RAHASIA)
        if login_npm == "1111111" and login_pw == "admin123":
            st.session_state.is_admin = True
            st.session_state.user_aktif = "ADMIN-SUPER"
            st.session_state.page = 'admin'
            st.rerun()
        
        # JIKA BUKAN ADMIN, CEK SEBAGAI MAHASISWA BIASA
        else:
            hashed_pw = hashlib.sha256(login_pw.encode()).hexdigest()
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE npm=? AND password=?', (login_npm, hashed_pw))
            user = c.fetchone()
            
            if user:
                st.session_state.user_aktif = login_npm
                st.session_state.is_admin = False
                save_log(login_npm, "Login Mahasiswa Berhasil")
                st.session_state.page = 'analytics' if user[6] == 1 else 'voting'
                st.rerun()
            else:
                st.error("Kredensial tidak ditemukan atau salah.")

    if st.button("Belum punya akun? Daftar"):
        st.session_state.page = 'register'
        st.rerun()

# --- 4. DASHBOARD ADMIN ---
def show_admin_dashboard():
    st.title("Admin Monitoring Dashboard")
    st.sidebar.write("Logged in as: **Master Admin**")
    
    if st.sidebar.button("Logout Admin"):
        st.session_state.is_admin = False
        st.session_state.page = 'login'
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["Data Pemilih", "Log Aktivitas Global", "Statistik Suara"])

    with tab1:
        df_users = pd.read_sql_query("SELECT npm, nama, region, kelas, status_vote FROM users", conn)
        st.dataframe(df_users, use_container_width=True)
        
        c1, c2 = st.columns(2)
        c1.metric("Total Terdaftar", len(df_users))
        c2.metric("Sudah Memilih", len(df_users[df_users['status_vote'] == 1]))

    with tab2:
        df_logs = pd.read_sql_query("SELECT * FROM activity_logs ORDER BY id DESC", conn)
        st.table(df_logs)

    with tab3:
        df_votes = pd.read_sql_query("SELECT pilihan, count(*) as total FROM votes GROUP BY pilihan", conn)
        if not df_votes.empty:
            fig = px.pie(df_votes, values='total', names='pilihan', hole=0.3)
            st.plotly_chart(fig)
        else:
            st.info("Belum ada data suara.")

# --- ROUTER ---
if st.session_state.page == 'admin' and st.session_state.is_admin:
    show_admin_dashboard()
elif st.session_state.page == 'login':
    show_login_page()
# ... (Sisanya show_register, show_voting, show_analytics seperti sebelumnya)