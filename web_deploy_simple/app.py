"""
視頻下載器 - 簡化版（無限流，更穩定）
專為 Render 部署優化
"""

from flask import Flask, render_template, request, jsonify, send_file, session
import os
import re
import uuid
import threading
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'felix-secret-key-2026')

PASSWORD = "felix96"
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)
download_tasks = {}


@app.route('/')
def index():
    """主頁面"""
    if not session.get('logged_in'):
        return render_template('login.html')
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    """登錄驗證"""
    data = request.json
    if data.get('password') == PASSWORD:
        session['logged_in'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '密碼錯誤'}), 401


@app.route('/logout', methods=['POST'])
def logout():
    """退出登錄"""
    session.clear()
    return jsonify({'success': True})


@app.route('/api/extract', methods=['POST'])
def extract_video():
    """提取視頻"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': '請先登錄'}), 401
    
    data = request.json
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'success': False, 'error': '請輸入網址'}), 400
    
    task_id = str(uuid.uuid4())
    
    thread = threading.Thread(target=download_video_task, args=(task_id, url))
    thread.daemon = True
    thread.start()
    
    download_tasks[task_id] = {
        'id': task_id,
        'url': url,
        'status': 'processing',
        'progress': 0,
        'filename': None,
        'title': None,
        'error': None,
        'estimated_time': '2-5分鐘'
    }
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'estimated_time': '2-5分鐘'
    })


@app.route('/api/status/<task_id>')
def get_status(task_id):
    """獲取狀態"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': '請先登錄'}), 401
    
    task = download_tasks.get(task_id)
    if not task:
        return jsonify({'success': False, 'error': '任務不存在'}), 404
    
    return jsonify({
        'success': True,
        'task': {
            'id': task['id'],
            'status': task['status'],
            'progress': task['progress'],
            'title': task['title'],
            'filename': task['filename'],
            'error': task['error']
        }
    })


@app.route('/api/download/<task_id>')
def download_file(task_id):
    """下載文件"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'error': '請先登錄'}), 401
    
    task = download_tasks.get(task_id)
    if not task or task['status'] != 'completed':
        return jsonify({'success': False, 'error': '文件未準備好'}), 400
    
    filepath = DOWNLOAD_DIR / task['filename']
    if not filepath.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    
    return send_file(filepath, as_attachment=True)


def download_video_task(task_id, url):
    """後台下載"""
    try:
        import yt_dlp
        task = download_tasks[task_id]
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                if d.get('total_bytes'):
                    task['progress'] = int(d['downloaded_bytes'] / d['total_bytes'] * 100)
                elif d.get('total_bytes_estimate'):
                    task['progress'] = int(d['downloaded_bytes'] / d['total_bytes_estimate'] * 100)
        
        # 免費服務器限制文件大小
        ydl_opts = {
            'format': 'worst[filesize<30M]',
            'outtmpl': str(DOWNLOAD_DIR / f'{task_id}.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                task['title'] = info.get('title', '視頻')
                for ext in ['mp4', 'webm', 'mkv']:
                    filepath = DOWNLOAD_DIR / f'{task_id}.{ext}'
                    if filepath.exists():
                        safe_title = re.sub(r'[<>:"/\\|?*]', '_', task['title'])[:50]
                        new_filename = f"{safe_title}.{ext}"
                        new_filepath = DOWNLOAD_DIR / new_filename
                        counter = 1
                        while new_filepath.exists():
                            new_filename = f"{safe_title}_{counter}.{ext}"
                            new_filepath = DOWNLOAD_DIR / new_filename
                            counter += 1
                        filepath.rename(new_filepath)
                        task['filename'] = new_filename
                        break
        
        task['status'] = 'completed'
        task['progress'] = 100
    except Exception as e:
        if task_id in download_tasks:
            download_tasks[task_id]['status'] = 'failed'
            download_tasks[task_id]['error'] = str(e)


@app.errorhandler(404)
def not_found(e):
    return render_template('login.html'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
