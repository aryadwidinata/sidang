import streamlit as st
from datetime import datetime, time, date
import firebase_admin
from firebase_admin import credentials, firestore
import os

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(
    page_title="Penjadwalan Rapat - DPRD Kab. Deli Serdang",
    page_icon="📅",
    layout="wide"
)

# --- 2. CUSTOM CSS MODERN (TOMBOL LEBIH COMPACT & PAS) ---
def apply_custom_css():
    st.markdown(
        """
        <style>
        /* Import Font Modern Inter */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Background Utama Modern */
        .stApp {
            background-color: #F8FAFC !important;
        }

        /* Top Bar Header Transparan */
        [data-testid="stHeader"] {
            background-color: rgba(248, 250, 252, 0) !important;
        }

        /* Sidebar Styling Clean */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E2E8F0 !important;
            padding-top: 1rem;
        }

        /* Header / Judul Utama */
        h1 {
            color: #C2410C !important;
            font-weight: 700 !important;
            font-size: 1.8rem !important;
            letter-spacing: -0.5px;
        }

        /* Subtitle / Caption */
        .stCaption, p {
            color: #475569 !important;
        }

        /* --- CARD JADWAL & CONTAINER STYLING --- */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #FFFFFF !important;
            border: 1px solid #FED7AA !important;
            border-left: 5px solid #EA580C !important;
            border-radius: 12px !important;
            padding: 18px !important;
            box-shadow: 0 4px 15px rgba(234, 88, 12, 0.05) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(234, 88, 12, 0.1) !important;
        }

        /* --- FORM & INPUT STYLING --- */
        [data-testid="stForm"] {
            background-color: #FFFFFF !important;
            border: 1px solid #E2E8F0 !important;
            border-radius: 16px !important;
            padding: 24px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03) !important;
        }

        .stTextInput label, .stDateInput label, .stTimeInput label, .stTextArea label {
            color: #1E293B !important;
            font-weight: 600 !important;
            font-size: 0.9rem !important;
        }

        div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div {
            background-color: #F8FAFC !important;
            border: 1px solid #CBD5E1 !important;
            border-radius: 8px !important;
            color: #0F172A !important;
        }

        div[data-baseweb="input"]:focus-within > div {
            border-color: #EA580C !important;
            box-shadow: 0 0 0 2px rgba(234, 88, 12, 0.2) !important;
        }

        /* --- BUTTON STYLING (UKURAN PROPORSIONAL & TIDAK RAKSASA) --- */
        div.stButton > button, 
        div[data-testid="stFormSubmitButton"] > button {
            background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 8px 20px !important; /* Diperkecil dari 12px 24px */
            font-weight: 600 !important;
            font-size: 0.9rem !important;
            box-shadow: 0 2px 6px rgba(234, 88, 12, 0.2) !important;
            transition: all 0.2s ease !important;
            width: auto !important; /* Dibuat pas dengan isi teks, tidak melebar melar */
            min-width: 200px !important; /* Lebar minimal pas di mata */
            display: block !important;
            margin: 0 auto !important; /* Posisi di tengah */
        }

        /* Memastikan Teks & Ikon di Dalam Tombol Berwarna Putih Clear */
        div.stButton > button *, 
        div[data-testid="stFormSubmitButton"] > button * {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
            font-weight: 600 !important;
        }

        /* Hover State Tombol */
        div.stButton > button:hover, 
        div[data-testid="stFormSubmitButton"] > button:hover {
            background: linear-gradient(135deg, #C2410C 0%, #9A3412 100%) !important;
            box-shadow: 0 4px 12px rgba(194, 65, 12, 0.3) !important;
            transform: translateY(-1px);
        }

        /* Radio Navigasi Sidebar */
        div[role="radiogroup"] label {
            padding: 8px 12px;
            border-radius: 8px;
            transition: background 0.2s;
        }
        div[role="radiogroup"] label:hover {
            background-color: #FFF7ED;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

apply_custom_css()

# --- 3. INISIALISASI FIREBASE ---
@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

# --- 4. FUNGSI DATABASE ---
def tambah_usulan_antrian(judul, tanggal, waktu_mulai, ruangan, agenda=""):
    data = {
        "judul": judul,
        "tanggal": tanggal.strftime("%Y-%m-%d"),
        "waktu_mulai": waktu_mulai.strftime("%H:%M"),
        "ruangan": ruangan,
        "agenda": agenda,
        "status": "pending",
        "request_timestamp": firestore.SERVER_TIMESTAMP
    }
    db.collection("jadwal_rapat").add(data)

def get_antrian_fifo():
    docs = db.collection("jadwal_rapat").where("status", "==", "pending").stream()
    antrian = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        antrian.append(d)
    antrian.sort(key=lambda x: str(x.get("request_timestamp", "")))
    return antrian

def get_jadwal_terkonfirmasi():
    docs = db.collection("jadwal_rapat").where("status", "==", "terkonfirmasi").stream()
    jadwal = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        jadwal.append(d)
    jadwal.sort(key=lambda x: str(x.get("tanggal", "")))
    return jadwal

def cek_konflik_jadwal(tanggal, waktu_mulai, ruangan):
    docs = db.collection("jadwal_rapat")\
             .where("status", "==", "terkonfirmasi")\
             .where("tanggal", "==", tanggal)\
             .where("ruangan", "==", ruangan)\
             .where("waktu_mulai", "==", waktu_mulai)\
             .stream()
    return any(docs)

def proses_konfirmasi_fifo(doc_id):
    doc_ref = db.collection("jadwal_rapat").document(doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False, "Data usulan tidak ditemukan!"
    
    data = doc.to_dict()
    if cek_konflik_jadwal(data["tanggal"], data["waktu_mulai"], data["ruangan"]):
        return False, f"⚠️ KONFLIK: Ruangan '{data['ruangan']}' sudah terpakai pada {data['tanggal']} jam {data['waktu_mulai']} WIB!"
    
    doc_ref.update({"status": "terkonfirmasi"})
    return True, "✅ Usulan berhasil disetujui!"

def hapus_jadwal(doc_id):
    try:
        db.collection("jadwal_rapat").document(doc_id).delete()
        return True
    except Exception as e:
        st.error(f"Gagal menghapus data: {e}")
        return False

# --- 5. SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- 6. SIDEBAR NAVIGASI & LOGO ---
if os.path.exists("assets/logo.png"):
    st.sidebar.image("assets/logo.png", use_container_width=True)
elif os.path.exists("static/logo.png"):
    st.sidebar.image("static/logo.png", use_container_width=True)

st.sidebar.markdown("### 📌 **Sistem Penjadwalan**")

if st.session_state.authenticated:
    st.sidebar.success("🔑 Status: **ADMIN**")
    if st.sidebar.button("Logout Admin", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
else:
    st.sidebar.info("👤 Status: **Tamu / User**")

menu = st.sidebar.radio(
    "Navigasi Menu:",
    ["Dashboard Jadwal", "Antrian Usulan (FIFO)", "Ajukan Rapat Baru", "Login Admin"]
)

# ==========================================
# 7. DASHBOARD JADWAL (TERKONFIRMASI)
# ==========================================
if menu == "Dashboard Jadwal":
    st.title("📅 Dashboard Jadwal Rapat Resmi")
    st.caption("Daftar agenda kegiatan rapat DPRD Kabupaten Deli Serdang yang telah terkonfirmasi.")
    st.markdown("---")
    
    jadwal_list = get_jadwal_terkonfirmasi()
    if not jadwal_list:
        st.info("ℹ️ Belum ada jadwal rapat yang terkonfirmasi saat ini.")
    else:
        cols = st.columns(3)
        for i, item in enumerate(jadwal_list):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"🗓️ **{item['tanggal']}**")
                    st.subheader(item['judul'])
                    st.markdown(f"🕒 **Waktu:** {item['waktu_mulai']} WIB")
                    st.markdown(f"📍 **Ruangan:** {item['ruangan']}")
                    st.markdown(f"📖 **Agenda:** {item.get('agenda') or '-'}")
                    
                    if st.session_state.authenticated:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("🗑️ Hapus Jadwal", key=f"del_{item['id']}", use_container_width=True):
                            if hapus_jadwal(item['id']):
                                st.toast("Jadwal berhasil dihapus!")
                                st.rerun()

# ==========================================
# 8. ANTRIAN USULAN (URUTAN FIFO)
# ==========================================
elif menu == "Antrian Usulan (FIFO)":
    st.title("⏳ Antrian Usulan Rapat")
    st.caption("Daftar pengajuan rapat yang menunggu persetujuan Admin (Sistem FIFO).")
    st.markdown("---")
    
    antrian_list = get_antrian_fifo()
    if not antrian_list:
        st.success("🎉 Tidak ada usulan rapat dalam antrian.")
    else:
        st.warning(f"📌 Total Ada **{len(antrian_list)} Usulan** Menunggu Pengecekan Admin.")
        
        for idx, item in enumerate(antrian_list, 1):
            with st.container(border=True):
                if idx == 1:
                    st.markdown("🔥 **PRIORITAS UTAMA (Antrian No. 1)**")
                else:
                    st.markdown(f"🔹 **Antrian Urutan Ke-{idx}**")
                    
                st.subheader(item['judul'])
                st.markdown(f"📅 **Tanggal:** {item['tanggal']} | 🕒 **Jam:** {item['waktu_mulai']} WIB | 📍 **Ruang:** {item['ruangan']}")
                
                ts = item.get('request_timestamp')
                ts_str = ts.strftime('%d/%m/%Y %H:%M:%S') if ts else "-"
                st.caption(f"🕒 Diterima Sistem: {ts_str}")
                
                if st.session_state.authenticated:
                    st.markdown("<br>", unsafe_allow_html=True)
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("✅ Disetujui (ACC)", key=f"pros_{item['id']}", use_container_width=True):
                            sukses, msg = proses_konfirmasi_fifo(item['id'])
                            if sukses:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    with col2:
                        if st.button("❌ Tolak Usulan", key=f"bat_{item['id']}", use_container_width=True):
                            if hapus_jadwal(item['id']):
                                st.toast("Usulan ditolak & dihapus.")
                                st.rerun()
                else:
                    st.info("🔒 *Hanya Admin yang dapat menyetujui antrian ini.*")

# ==========================================
# 9. AJUKAN RAPAT BARU (USER)
# ==========================================
elif menu == "Ajukan Rapat Baru":
    st.title("➕ Form Pengajuan Rapat Baru")
    st.caption("Isi formulir di bawah ini untuk mengusulkan agenda rapat baru.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    with st.form("form_tambah"):
        judul = st.text_input("Judul Rapat / Agenda Sidang", placeholder="Contoh: Rapat Paripurna LKPJ")
        c1, c2 = st.columns(2)
        with c1:
            tanggal = st.date_input("Tanggal Pelaksanaan", value=date.today())
        with c2:
            waktu = st.time_input("Waktu Mulai", value=time(9, 0))
            
        ruangan = st.text_input("Ruangan / Lokasi", placeholder="Contoh: Ruang Rapat Utama")
        agenda = st.text_area("Rincian Agenda (Opsional)", placeholder="Tuliskan catatan atau rincian agenda di sini...")
        
        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("📋 Kirim Usulan Ke Antrian Sistem", use_container_width=True)
        
        if submit:
            if judul and ruangan:
                tambah_usulan_antrian(judul, tanggal, waktu, ruangan, agenda)
                st.success(" Usulan rapat berhasil dikirim! Silakan pantau di menu 'Antrian Usulan (FIFO)'.")
            else:
                st.error("Judul Rapat dan Ruangan wajib diisi!")

# ==========================================
# 10. LOGIN KHUSUS ADMIN
# ==========================================
elif menu == "Login Admin":
    st.title("🔒 Login Portal Admin")
    st.caption("Masuk untuk mengelola dan memvalidasi antrian rapat.")
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state.authenticated:
        st.success("Anda sedang dalam **Mode Admin**. Semua akses kontrol aktif.")
    else:
        with st.form("login_form"):
            user = st.text_input("Username Admin")
            pwd = st.text_input("Password Admin", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            btn = st.form_submit_button("Login Ke Sistem", use_container_width=True)
            
            if btn:
                if user == "admin" and pwd == "admin123":
                    st.session_state.authenticated = True
                    st.success("Login Admin Berhasil!")
                    st.rerun()
                else:
                    st.error("Username atau Password Admin salah!")