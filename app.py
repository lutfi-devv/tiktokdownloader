from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import time
import threading
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = 'tiktok_downloader_secret_key'

# Folder untuk menyimpan video yang diunduh
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Fungsi untuk membersihkan folder downloads
def clean_download_folder():
    for filename in os.listdir(DOWNLOAD_FOLDER):
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(f"Error deleting {file_path}: {e}")

# Fungsi untuk mendownload video TikTok
def download_tiktok_video(url, unique_id):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Menggunakan API TikTok downloader
        api_url = f"https://api.tikmate.app/api/1.2/tiktok?url={url}"
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                video_url = data.get('video_url')
                if video_url:
                    video_response = requests.get(video_url, stream=True, headers=headers)
                    if video_response.status_code == 200:
                        filename = f"{unique_id}.mp4"
                        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
                        with open(filepath, 'wb') as f:
                            for chunk in video_response.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                        return filename
        return None
    except Exception as e:
        print(f"Error downloading video: {e}")
        return None

# Route untuk halaman utama
@app.route('/')
def index():
    return render_template('index.html')

# Route untuk halaman downloader
@app.route('/downloader')
def downloader():
    return render_template('downloader.html')

# Route untuk proses download
@app.route('/download', methods=['POST'])
def download():
    tiktok_url = request.form.get('url')
    
    if not tiktok_url:
        flash('Masukkan URL TikTok yang valid', 'error')
        return redirect(url_for('downloader'))
    
    # Validasi URL TikTok
    if not re.search(r'(tiktok\.com\/@[^\/]+\/video\/\d+|vm\.tiktok\.com\/\w+)', tiktok_url):
        flash('URL TikTok tidak valid', 'error')
        return redirect(url_for('downloader'))
    
    # Generate unique ID untuk file
    unique_id = str(uuid.uuid4())
    
    # Tampilkan halaman loading
    return render_template('loading.html', url=tiktok_url, unique_id=unique_id)

# Route untuk memulai proses download (dipanggil dari halaman loading)
@app.route('/start_download/<unique_id>')
def start_download(unique_id):
    tiktok_url = request.args.get('url')
    
    # Mulai proses download di thread terpisah
    def download_thread():
        filename = download_tiktok_video(tiktok_url, unique_id)
        if filename:
            # Simpan nama file di session untuk diakses nanti
            with app.app_context():
                session[f'download_{unique_id}'] = filename
    
    thread = threading.Thread(target=download_thread)
    thread.start()
    
    return {'status': 'started'}

# Route untuk mengecek status download
@app.route('/check_status/<unique_id>')
def check_status(unique_id):
    filename = session.get(f'download_{unique_id}')
    if filename:
        return {'status': 'completed', 'filename': filename}
    return {'status': 'processing'}

# Route untuk mengunduh file
@app.route('/get_file/<filename>')
def get_file(filename):
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name='tiktok_video.mp4')
    flash('File tidak ditemukan', 'error')
    return redirect(url_for('downloader'))

# Route untuk membersihkan session
@app.route('/cleanup/<unique_id>')
def cleanup(unique_id):
    if f'download_{unique_id}' in session:
        session.pop(f'download_{unique_id}')
    return {'status': 'cleaned'}

if __name__ == '__main__':
    # Bersihkan folder downloads saat aplikasi dimulai
    clean_download_folder()
    app.run(debug=True)