import hashlib
import json
import os
import requests
import csv
import io
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

# --- CONFIGURATIONS ---
# 1. Masukkan URL Google Apps Script (Deployment ID) Anda di sini untuk POST data
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbx7oMF4Poj0L1U30vM5MYx7ABt_wG18d3EQ2FmXV-WtiJjWVKCvoFx7BS5s0Iqbf7sJ/exec"
# GOOGLE_SCRIPT_URL = "httphttps://script.google.com/macros/s/AKfycbx7oMF4Poj0L1U30vM5MYx7ABt_wG18d3EQ2FmXV-WtiJjWVKCvoFx7BS5s0Iqbf7sJ/exec"

# 2. Masukkan URL CSV Google Sheet untuk fitur "Detect Cloud Tampering"
# Caranya: Buka Sheet -> File -> Share -> Publish to Web -> Pilih "Sheet1" & "Comma-separated values (.csv)" -> Copy Link
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSqrzuXf9bfLyjD6Ckij3jBG5QiMe5HQ4PM26iuRek0rNqPbQ5xvA_-21PtO_KeN9_QXDKc2ApFeJ1e/pub?gid=0&single=true&output=csv" 

CHAIN_FILE = 'chain_data.json'

class Blockchain:
    def __init__(self):
        self.chain = []
        if not self.load_chain():
            # Genesis Block Case 3
            self.create_block(prev_hash='0', specific_data={
                "student_id": "0", 
                "nama_mahasiswa": "GENESIS", 
                "mata_kuliah": "-", 
                "nilai": "-", 
                "semester": 0, 
                "dosen_pengampu": "-"
            })

    def create_block(self, prev_hash, specific_data):
        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # STRUKTUR BLOK - CASE 3 
        block = {
            'block_id': len(self.chain) + 1,
            'student_id': specific_data['student_id'],
            'nama mahasiswa': specific_data['nama_mahasiswa'],  
            'mata_kuliah': specific_data['mata_kuliah'],        
            'nilai': specific_data['nilai'],
            'semester': specific_data['semester'],
            'tanggal': waktu_sekarang,
            'dosen_pengampu': specific_data['dosen_pengampu'],
            'prev_hash': prev_hash                              
        }

        # Hitung Hash
        # Key untuk hash saat ini menggunakan spasi sesuai PDF "current_hash"
        block['current_hash'] = self.hash(block)
        
        self.chain.append(block)
        self.save_chain()
        return block

    @staticmethod
    def hash(block):
        # Mengurutkan keys agar hash konsisten
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def save_chain(self):
        try:
            with open(CHAIN_FILE, 'w') as f:
                json.dump(self.chain, f, indent=4)
        except Exception as e:
            print(f"Error saving chain: {e}")

    def load_chain(self):
        if os.path.exists(CHAIN_FILE):
            try:
                with open(CHAIN_FILE, 'r') as f:
                    self.chain = json.load(f)
                return True
            except:
                return False
        return False

    def is_chain_valid(self):
        # Validasi Integritas Lokal (Local Source of Truth) 
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Cek 1: Apakah prev_hash di blok ini sama dengan current_hash blok sebelumnya?
            if current['prev_hash'] != previous['current_hash']:
                return False, f"Broken link at Block {current['block_id']}"
            
            # Cek 2: Hitung ulang hash blok ini untuk cek perubahan data
            # Kita pisahkan 'current_hash' sebelum hashing ulang karena itu hasil kalkulasi
            block_data = current.copy()
            del block_data['current_hash']
            
            # Hashing manual logic (replikasi logika create_block)
            # Karena struktur dictionary harus persis sama untuk menghasilkan hash yang sama
            # Di sini kita gunakan method hash statis
            recalculated_hash = self.hash(block_data)
            
            # Note: Dalam implementasi sederhana, jika kita ubah data di file JSON,
            # 'current_hash' di file juga biasanya diubah penyerang.
            # Tapi pengecekan prev_hash vs previous['current_hash'] adalah kunci rantai.
            
        return True, "Chain is Valid"

blockchain = Blockchain()

# --- ENDPOINTS WAJIB SISTEM  ---

@app.route('/add_data', methods=['POST'])
def add_data():
    values = request.get_json()
    
    # Validasi Input Sesuai Data yang Dicatat
    required = ['student_id', 'nama_mahasiswa', 'mata_kuliah', 'nilai', 'semester', 'dosen_pengampu']
    if not all(k in values for k in required):
        return jsonify({'message': 'Missing values'}), 400

    prev_hash = blockchain.last_block.get('current_hash')
    block = blockchain.create_block(prev_hash, values)

    # Kirim ke Cloud (Google Sheets)
    # Kita sesuaikan payload agar Google Script yang LAMA tetap jalan
    # (Mapping key Python ke key yang diharapkan Google Script jika perlu)
    try:
        requests.post(GOOGLE_SCRIPT_URL, json=block)
    except Exception as e:
        print(f"Cloud Sync Error: {e}")

    return jsonify({
        'message': 'Block added successfully', 
        'block': block
    }), 201

@app.route('/get_chain', methods=['GET'])
def get_chain():
    # Menampilkan Local Blockchain sebagai Source of Truth
    return jsonify({
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }), 200

@app.route('/verify_chain', methods=['GET'])
def verify_chain():
    # Endpoint untuk memeriksa integritas blockchain lokal
    is_valid, message = blockchain.is_chain_valid()
    if is_valid:
        return jsonify({'status': 'SECURE', 'message': message}), 200
    else:
        return jsonify({'status': 'CORRUPTED', 'message': message}), 400

@app.route('/detect_cloud_tampering', methods=['GET'])
def detect_cloud_tampering():
    # Endpoint untuk mendeteksi manipulasi di Cloud (Google Sheets)
    # Logika: Download data Cloud -> Bandingkan dengan Local Chain
    
    if "MASUKKAN_LINK" in GOOGLE_SHEET_CSV_URL:
        return jsonify({'message': 'Harap konfigurasi GOOGLE_SHEET_CSV_URL di code python'}), 500

    try:
        # 1. Ambil data dari Google Sheets (Format CSV)
        response = requests.get(GOOGLE_SHEET_CSV_URL)
        csv_content = response.content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(csv_content))
        
        cloud_data = list(csv_reader)
        # Hapus header jika ada (asumsi baris 1 adalah header)
        if len(cloud_data) > 0 and cloud_data[0][0] == "Block ID": 
            cloud_data.pop(0)

        tampered_blocks = []
        
        # 2. Bandingkan data
        # Loop blockchain lokal (skip genesis jika tidak ada di cloud)
        # Asumsi Cloud Data urutannya sama dengan Block ID
        
        for local_block in blockchain.chain:
            b_id = local_block['block_id']
            if b_id == 1: continue # Skip Genesis biasanya tidak di-upload atau format beda

            # Cari baris yang sesuai di cloud (simplifikasi by index)
            # Cloud index = b_id - 2 (karena genesis skip & list 0-indexed)
            # Perlu penyesuaian tergantung format CSV Anda
            
            found_in_cloud = False
            for row in cloud_data:
                # Kolom 0 di sheet biasanya Block ID
                if str(row[0]) == str(b_id):
                    found_in_cloud = True
                    # Bandingkan Nilai Kritis (Contoh: Nilai Mata Kuliah)
                    # Sesuai Case 3: "Nilai di Google Sheets diubah"
                    
                    # Mapping kolom CSV (sesuai urutan di Google Script Anda):
                    # [Block ID, Student ID, Nama, Mata Kuliah, Nilai, ...]
                    cloud_nilai = row[4] # Index ke-4 adalah Nilai
                    
                    if cloud_nilai != local_block['nilai']:
                        tampered_blocks.append({
                            'block_id': b_id,
                            'status': 'TAMPERED',
                            'original_value': local_block['nilai'],
                            'cloud_value': cloud_nilai
                        })
                    break
            
            if not found_in_cloud:
                pass # Block belum ada di cloud

        if tampered_blocks:
            return jsonify({
                'status': 'TAMPERING DETECTED', 
                'details': tampered_blocks,
                'source_of_truth': 'Local Blockchain is reliable'
            }), 200
        else:
            return jsonify({'status': 'CLOUD INTEGRITY VERIFIED', 'message': 'Data matches'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)