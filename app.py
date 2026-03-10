#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
視頻下載器 - 雲端部署版 (v3.4 簡化穩定版)
支持部署到 Render、PythonAnywhere 等免費服務器
"""

import os
import re
import json
import uuid
import threading
import traceback
from pathlib import Path
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, send_file, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'felix-secret-key-2026')

# 配置
PASSWORD = "felix96"
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# 限制請求頻率
try:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["30 per hour"]
    )
except:
    class FakeLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = FakeLimiter()

# 存儲下載任務狀態
download_tasks = {}

print("=" * 60)
print("視頻下載器 v3.4 啟動中...")
print("=" * 60)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            if request.is_json:
                return jsonify({'success': False, 'error': '請先登錄'}), 401
            return render_template('login.html')
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    if not session.get('logged_in'):
        return render_template('login.html')
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    if request.is_json:
        data = request.json
        password = data.get('password', '').strip()
    else:
        password = request.form.get('password', '').strip()
    
    if password == PASSWORD:
        session['logged_in'] = True
        session.permanent = True
        if request.is_json:
            return jsonify({'success': True})
        return render_template('index.html')
    else:
        if request.is_json:
            return jsonify({'success': False, 'error': '密碼錯誤'}), 401
        return render_template('login.html', error='密碼錯誤')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})


@app.route('/api/extract', methods=['POST'])
@login_required
def extract_video():
    data = request.json
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'success': False, 'error': '請輸入視頻網址'}), 400
    
    if not url.startswith(('http://', 'https://')):
        return jsonify({'success': False, 'error': '請輸入正確的網址格式'}), 400
    
    task_id = str(uuid.uuid4())
    
    # 初始化任務
    download_tasks[task_id] = {
        'id': task_id,
        'url': url,
        'status': 'processing',
        'progress': 0,
        'filename': None,
        'title': None,
        'error': None,
        'created_at': datetime.now(),
    }
    
    # 啟動下載線程
    thread = threading.Thread(target=download_task, args=(task_id, url))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': '開始提取視頻...',
        'estimated_time': '2-5分鐘'
    })


@app.route('/api/status/<task_id>')
@login_required
def get_status(task_id):
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
            'error': task['error'],
        }
    })


@app.route('/api/download/<task_id>')
@login_required
def download_file(task_id):
    task = download_tasks.get(task_id)
    if not task or task['status'] != 'completed':
        return jsonify({'success': False, 'error': '文件尚未準備就緒'}), 400
    
    filepath = DOWNLOAD_DIR / task['filename']
    if not filepath.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    
    return send_file(filepath, as_attachment=True, download_name=task['filename'])


def download_task(task_id, url):
    """下載任務 - 簡化穩定版"""
    try:
        import yt_dlp
        import requests
        
        task = download_tasks[task_id]
        print(f"\n[{task_id}] ====== 開始處理 ======")
        print(f"[{task_id}] URL: {url}")
        
        # 處理短鏈接
        if 'b23.tv' in url:
            try:
                resp = requests.head(url, allow_redirects=True, timeout=10)
                if resp.url != url:
                    url = resp.url
                    task['url'] = url
                    print(f"[{task_id}] 短鏈接展開為: {url}")
            except Exception as e:
                print(f"[{task_id}] 展開短鏈接失敗: {e}")
        
        # 進度回調
        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    task['progress'] = int(d['downloaded_bytes'] / total * 100)
            elif d['status'] == 'finished':
                task['progress'] = 100
                print(f"[{task_id}] yt-dlp: 下載完成")
        
        # 配置 - 使用多個回退格式確保成功
        ydl_opts = {
            'outtmpl': str(DOWNLOAD_DIR / f'{task_id}.%(ext)s'),
            'progress_hooks': [progress_hook],
            # 嘗試多種格式，確保至少有一種可用
            'format': 'worst[filesize<50M]/worst/best[filesize<50M]/best',
            'quiet': True,
            'no_warnings': True,
        }
        
        # 檢測網站類型
        is_bilibili = 'bilibili' in url.lower()
        
        if is_bilibili:
            print(f"[{task_id}] 檢測到 Bilibili")
            ydl_opts['referer'] = 'https://www.bilibili.com'
        
        # 提取信息
        print(f"[{task_id}] 提取視頻信息...")
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    task['title'] = info.get('title', '視頻')
                    formats = info.get('formats', [])
                    print(f"[{task_id}] 標題: {task['title']}")
                    print(f"[{task_id}] 可用格式: {len(formats)}")
        except Exception as e:
            print(f"[{task_id}] 提取信息失敗: {e}")
            task['title'] = '視頻'
        
        # 下載
        print(f"[{task_id}] 開始下載...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # 查找文件
        print(f"[{task_id}] 查找下載的文件...")
        found_file = None
        
        # 搜索所有可能的擴展名
        for ext in ['.mp4', '.webm', '.mkv', '.flv', '.m4a', '.mp3']:
            f = DOWNLOAD_DIR / f'{task_id}{ext}'
            if f.exists() and f.stat().st_size > 1024:  # 至少1KB
                found_file = f
                break
        
        # 如果沒找到，搜索最近創建的文件
        if not found_file:
            files = sorted(DOWNLOAD_DIR.glob(f'{task_id}.*'), 
                          key=lambda x: x.stat().st_mtime, reverse=True)
            for f in files:
                if f.stat().st_size > 1024:
                    found_file = f
                    break
        
        if found_file:
            size_mb = found_file.stat().st_size / 1024 / 1024
            print(f"[{task_id}] 找到文件: {found_file.name} ({size_mb:.2f}MB)")
            
            # 檢查大小（50MB限制）
            if size_mb > 50:
                found_file.unlink()
                task['status'] = 'failed'
                task['error'] = f'視頻大小為 {size_mb:.1f}MB，超過 50MB 免費版限制。請選擇較短的視頻。'
                print(f"[{task_id}] 文件超過限制，已刪除")
                return
            
            # 重命名
            safe_title = re.sub(r'[<>:"/\\|?*]', '_', task.get('title', 'video'))[:40]
            new_name = f"{safe_title}{found_file.suffix}"
            new_path = DOWNLOAD_DIR / new_name
            
            # 處理重名
            counter = 1
            while new_path.exists():
                new_name = f"{safe_title}_{counter}{found_file.suffix}"
                new_path = DOWNLOAD_DIR / new_name
                counter += 1
            
            found_file.rename(new_path)
            task['filename'] = new_name
            task['status'] = 'completed'
            print(f"[{task_id}] 完成: {new_name}")
            
        else:
            task['status'] = 'failed'
            task['error'] = '下載完成但未找到文件。可能是視頻格式不支持或文件為空。'
            print(f"[{task_id}] 錯誤: 未找到文件")
            
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"[{task_id}] 錯誤: {error_msg}")
        print(error_trace)
        
        task = download_tasks.get(task_id)
        if task:
            task['status'] = 'failed'
            
            # 簡單的錯誤分類
            if 'format is not available' in error_msg.lower():
                task['error'] = '該視頻無可用下載格式。可能是會員專屬、版權保護或需要登錄。'
            elif 'unable to extract' in error_msg.lower():
                task['error'] = '無法提取視頻信息。請檢查網址是否正確，或嘗試使用非短鏈接。'
            elif '403' in error_msg:
                task['error'] = '訪問被拒絕(403)。服務器IP可能被Bilibili限制。'
            elif '404' in error_msg:
                task['error'] = '視頻不存在(404)。請檢查網址。'
            elif 'timeout' in error_msg.lower():
                task['error'] = '連接超時，請重試。'
            else:
                task['error'] = f'下載失敗: {error_msg[:100]}'


@app.errorhandler(404)
def not_found(e):
    return render_template('login.html'), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
