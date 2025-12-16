import hashlib
import json
from time import time
from datetime import datetime
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# --- CONFIG ---
GOOGLE_SHEET_API = "https://script.google.com/macros/s/AKfycbx7oMF4Poj0L1U30vM5MYx7ABt_wG18d3EQ2FmXV-WtiJjWVKCvoFx7BS5s0Iqbf7sJ/exec"

class Blockchain:
    def __init__(self):
        self.chain = []
        # Membuat Genesis Block
        self.create_block(prev_hash='0', specific_data={
            "student_id": "0", "nama_mahasiswa": "GENESIS", 
            "mata_kuliah": "-", "nilai": "-", "semester": 0, "dosen_pengampu": "-"
        })

    def create_block(self, prev_hash, specific_data):
        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

        # Hitung Current Hash
        block['current hash'] = self.hash(block)
        
        self.chain.append(block)
        return block

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

blockchain = Blockchain()

# --- ENDPOINTS ---

@app.route('/add_data', methods=['POST'])
def add_data():
    values = request.get_json()
    required = ['student_id', 'nama_mahasiswa', 'mata_kuliah', 'nilai', 'semester', 'dosen_pengampu']
    
    if not all(k in values for k in required):
        return 'Missing values', 400

    # Ambil hash blok terakhir
    prev_hash = blockchain.last_block.get('current hash')
    
    # Buat Blok
    block = blockchain.create_block(prev_hash, values)

    # Kirim ke Cloud (Google Sheets)
    try:
        requests.post(GOOGLE_SHEET_API, json=block)
    except Exception as e:
        print(f"Error Cloud: {e}")

    return jsonify({'message': 'Block added', 'block': block}), 201

@app.route('/get_chain', methods=['GET'])
def get_chain():
    return jsonify({'chain': blockchain.chain, 'length': len(blockchain.chain)}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)