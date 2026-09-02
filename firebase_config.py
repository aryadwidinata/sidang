import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import os
import json

@st.cache_resource
def get_db():
    if not firebase_admin._apps:
        file_path = "serviceAccountKey.json"
        
        # 1. Coba baca dari file lokal jika ada dan isinya valid
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                cred = credentials.Certificate(file_path)
                firebase_admin.initialize_app(cred)
            except json.decoder.JSONDecodeError:
                # Jika file lokal rusak, lewati ke st.secrets
                pass

        # 2. Jika lokal gagal/tidak ada, gunakan Streamlit Secrets (TOML)
        if not firebase_admin._apps:
            try:
                key_dict = dict(st.secrets["firebase"])
                if "private_key" in key_dict:
                    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
            except Exception as e:
                st.error("❌ Gagal menginisialisasi Firebase. Periksa file serviceAccountKey.json lokal atau menu Secrets di Streamlit Cloud.")
                st.stop()

    return firestore.client()

db = get_db()

# --- OPERASI FIRESTORE ---

def tambah_usulan_antrian(judul, tanggal, waktu_mulai, ruangan, agenda=""):
    """Menambahkan usulan rapat baru ke antrian (status: pending)."""
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

def get_antrian():
    """Mengambil daftar antrian usulan (status: pending) berurut FIFO berdasarkan timestamp."""
    docs = db.collection("jadwal_rapat")\
             .where("status", "==", "pending")\
             .order_by("request_timestamp", direction=firestore.Query.ASCENDING)\
             .stream()
    
    antrian = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        antrian.append(d)
    return antrian

def get_jadwal_terkonfirmasi():
    """Mengambil jadwal yang sudah disetujui/terkonfirmasi."""
    docs = db.collection("jadwal_rapat")\
             .where("status", "==", "terkonfirmasi")\
             .order_by("tanggal", direction=firestore.Query.ASCENDING)\
             .stream()
    
    jadwal = []
    for doc in docs:
        d = doc.to_dict()
        d["id"] = doc.id
        jadwal.append(d)
    return jadwal

def cek_konflik_jadwal(tanggal, waktu_mulai, ruangan, current_id=None):
    """Mengecek apakah ada bentrok ruangan pada tanggal dan jam yang sama."""
    docs = db.collection("jadwal_rapat")\
             .where("status", "==", "terkonfirmasi")\
             .where("tanggal", "==", tanggal)\
             .where("ruangan", "==", ruangan)\
             .where("waktu_mulai", "==", waktu_mulai)\
             .stream()
    
    for doc in docs:
        if current_id and doc.id == current_id:
            continue
        return True # Terdapat konflik
    return False # Aman

def proses_konfirmasi_fifo(doc_id):
    """Memproses usulan rapat antrian menjadi terkonfirmasi dengan pengecekan konflik."""
    doc_ref = db.collection("jadwal_rapat").document(doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        return False, "Data tidak ditemukan!"
    
    data = doc.to_dict()
    ada_konflik = cek_konflik_jadwal(data["tanggal"], data["waktu_mulai"], data["ruangan"], doc_id)
    
    if ada_konflik:
        return False, f"Konflik ditemukan! Ruangan {data['ruangan']} sudah terpakai pada {data['tanggal']} pkl {data['waktu_mulai']}."
    
    doc_ref.update({"status": "terkonfirmasi"})
    return True, "Jadwal berhasil dikonfirmasi!"

def update_jadwal(doc_id, judul, tanggal, waktu_mulai, ruangan, agenda):
    """Mengubah detail jadwal."""
    doc_ref = db.collection("jadwal_rapat").document(doc_id)
    doc_ref.update({
        "judul": judul,
        "tanggal": tanggal.strftime("%Y-%m-%d"),
        "waktu_mulai": waktu_mulai.strftime("%H:%M"),
        "ruangan": ruangan,
        "agenda": agenda
    })

def hapus_jadwal(doc_id):
    """Menghapus/Membatalkan usulan atau jadwal rapat."""
    db.collection("jadwal_rapat").document(doc_id).delete()
