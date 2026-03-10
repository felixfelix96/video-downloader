#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
視頻下載器 - 雲端部署版
支持部署到 Render、PythonAnywhere 等免費服務器
"""

import os
import re
import json
import uuid
import threading
from pathlib import Path
from datetime import datetime, timedelta
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

# 限制請求頻率（防止濫用）
try:
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["30 per hour"]
    )
except:
    # 如果 limiter 初始化失敗，創建一個假的
    class FakeLimiter:
        def limit(self, *args, **kwargs):
            def decorator(f):
                return f
            return decorator
    limiter = FakeLimiter()

# 存儲下載任務狀態
download_tasks = {}

# 支持的網站列表
SUPPORTED_SITES = {
    'bilibili.com': 'Bilibili',
    'bilibili.tv': 'Bilibili',
    'b23.tv': 'Bilibili',
    'douyin.com': '抖音',
    'iesdouyin.com': '抖音',
    'kuaishou.com': '快手',
    'kuaishouapp.com': '快手',
    'chenzhongtech.com': '快手',
    'youtube.com': 'YouTube',
    'youtu.be': 'YouTube',
    'toutiao.com': '頭條',
    'ixigua.com': '西瓜視頻',
    'weibo.com': '微博',
    'weibo.cn': '微博',
}


def login_required(f):
    """登錄驗證裝飾器"""
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
    """主頁面"""
    if not session.get('logged_in'):
        return render_template('login.html')
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """登錄頁面和驗證"""
    if request.method == 'GET':
        return render_template('login.html')
    
    # POST 請求處理登錄
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
    """退出登錄"""
    session.clear()
    return jsonify({'success': True})


@app.route('/api/extract', methods=['POST'])
@login_required
def extract_video():
    """提取視頻信息"""
    data = request.json
    url = data.get('url', '').strip()
    
    if not url:
        return jsonify({'success': False, 'error': '請輸入視頻網址'}), 400
    
    # 驗證URL格式
    if not url.startswith(('http://', 'https://')):
        return jsonify({'success': False, 'error': '請輸入正確的網址格式'}), 400
    
    # 生成任務ID
    task_id = str(uuid.uuid4())
    
    # 啟動後台下載任務
    thread = threading.Thread(
        target=download_video_task,
        args=(task_id, url)
    )
    thread.daemon = True
    thread.start()
    
    # 保存任務信息
    download_tasks[task_id] = {
        'id': task_id,
        'url': url,
        'status': 'processing',  # processing, completed, failed
        'progress': 0,
        'filename': None,
        'title': None,
        'error': None,
        'created_at': datetime.now(),
        'estimated_time': '2-5分鐘'
    }
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'message': '開始提取視頻，請稍候...',
        'estimated_time': '2-5分鐘'
    })


@app.route('/api/status/<task_id>')
@login_required
def get_status(task_id):
    """獲取任務狀態"""
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
            'estimated_time': task['estimated_time']
        }
    })


@app.route('/api/download/<task_id>')
@login_required
def download_file(task_id):
    """下載文件"""
    task = download_tasks.get(task_id)
    if not task or task['status'] != 'completed':
        return jsonify({'success': False, 'error': '文件尚未準備就緒'}), 400
    
    filepath = DOWNLOAD_DIR / task['filename']
    if not filepath.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=task['filename']
    )


def get_site_name(url):
    """獲取網站名稱"""
    url_lower = url.lower()
    for domain, name in SUPPORTED_SITES.items():
        if domain in url_lower:
            return name
    return '未知網站'


def download_video_task(task_id, url):
    """後台下載視頻任務"""
    try:
        import yt_dlp
        
        task = download_tasks[task_id]
        site_name = get_site_name(url)
        print(f"[{task_id}] 開始下載 {site_name} 視頻: {url}")
        
        # 進度回調
        def progress_hook(d):
            if d['status'] == 'downloading':
                if d.get('total_bytes'):
                    progress = int(d['downloaded_bytes'] / d['total_bytes'] * 100)
                    task['progress'] = progress
                elif d.get('total_bytes_estimate'):
                    progress = int(d['downloaded_bytes'] / d['total_bytes_estimate'] * 100)
                    task['progress'] = progress
            elif d['status'] == 'finished':
                task['progress'] = 100
        
        # 下載選項 - 支持多個主流視頻網站
        ydl_opts = {
            # 增加多個回退格式選項，避免 "Requested format is not available" 錯誤
            # 優先嘗試 mp4 格式，大小限制 50MB
            'format': 'best[filesize<50M][ext=mp4]/best[ext=mp4][filesize<50M]/best[filesize<50M]/worst[filesize<50M]/best/worst',
            'outtmpl': str(DOWNLOAD_DIR / f'{task_id}.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 52428800,  # 50MB
            'merge_output_format': 'mp4',
            # 添加 cookies 支持（某些網站需要）
            'cookiesfrombrowser': None,
            # 設置用戶代理
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        url_lower = url.lower()
        
        # Bilibili 特殊處理
        if 'bilibili' in url_lower:
            ydl_opts['extractor_args'] = {
                'bilibili': {
                    'prefer_flv': False,
                    'formats': 'mp4',
                }
            }
        
        # 抖音/快手特殊處理 - 使用更寬鬆的格式選擇
        elif any(x in url_lower for x in ['douyin', 'iesdouyin', 'kuaishou', 'chenzhongtech']):
            # 移除嚴格的格式限制，讓 yt-dlp 自動選擇
            ydl_opts['format'] = 'best/worst'
            # 這些網站通常有水印，我們嘗試獲取最佳可用質量
            ydl_opts['format_sort'] = ['res', 'ext:mp4:m4a', 'size', 'br']
        
        # 開始下載
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # 獲取實際文件名
            if info:
                task['title'] = info.get('title', '未知標題')
                
                # 查找下載的文件
                for ext in ['mp4', 'webm', 'mkv']:
                    filepath = DOWNLOAD_DIR / f'{task_id}.{ext}'
                    if filepath.exists():
                        # 重命名為可讀文件名
                        safe_title = re.sub(r'[<>:"/\\|?*]', '_', task['title'])[:50]
                        new_filename = f"{safe_title}.{ext}"
                        new_filepath = DOWNLOAD_DIR / new_filename
                        
                        # 如果文件已存在，添加序號
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
        import traceback
        task = download_tasks.get(task_id)
        if task:
            task['status'] = 'failed'
            error_msg = str(e)
            
            # 提供更友好的錯誤提示
            if 'format is not available' in error_msg.lower():
                task['error'] = '該視頻格式暫不支持，請嘗試其他視頻'
            elif 'unable to extract' in error_msg.lower():
                task['error'] = '無法提取視頻信息，請檢查網址是否正確'
            elif 'sign in' in error_msg.lower() or 'login' in error_msg.lower():
                task['error'] = '該視頻需要登錄才能訪問'
            elif 'copyright' in error_msg.lower() or 'restricted' in error_msg.lower():
                task['error'] = '該視頻因版權原因無法下載'
            elif 'filesize' in error_msg.lower() or '50m' in error_msg.lower():
                task['error'] = '視頻超過 50MB 限制，無法下載'
            elif 'network' in error_msg.lower() or 'urlopen' in error_msg.lower():
                task['error'] = '網絡連接失敗，請重試'
            else:
                task['error'] = f'下載失敗: {error_msg[:100]}'
            
            print(f"[{task_id}] 下載失敗: {error_msg}")
            print(traceback.format_exc())


@app.errorhandler(404)
def not_found(e):
    """404 錯誤處理"""
    return render_template('login.html'), 404


if __name__ == '__main__':
    # 本地開發時使用
    print("=" * 60)
    print("  🎬 視頻下載器 - 雲端版")
    print("=" * 60)
    print("\n訪問地址: http://localhost:5000")
    print("密碼: felix96\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
