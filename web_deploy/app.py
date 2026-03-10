#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
視頻下載器 - 雲端部署版 (v3.2)
支持部署到 Render、PythonAnywhere 等免費服務器
支持 Bilibili、抖音、快手等主流網站
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
        'status': 'processing',
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


def expand_short_url(url):
    """展開短鏈接"""
    import requests
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
        if response.status_code in [200, 301, 302]:
            expanded = response.url
            if expanded != url:
                print(f"[URL] 短鏈接已展開: {url} -> {expanded}")
                return expanded
    except Exception as e:
        print(f"[URL] 展開短鏈接失敗: {e}")
    
    return url


def find_downloaded_file(task_id):
    """查找已下載的文件 - 擴展搜索範圍"""
    # 搜索所有可能的視頻擴展名
    extensions = ['.mp4', '.webm', '.mkv', '.flv', '.mov', '.avi', '.m4v', '.3gp', '.ts']
    
    print(f"[FILE] 開始搜索任務 {task_id} 的文件...")
    print(f"[FILE] 搜索目錄: {DOWNLOAD_DIR.absolute()}")
    
    # 方法1: 按擴展名搜索
    for ext in extensions:
        filepath = DOWNLOAD_DIR / f'{task_id}{ext}'
        if filepath.exists():
            size = filepath.stat().st_size
            print(f"[FILE] 找到文件(方法1): {filepath.name}, 大小: {size} bytes")
            return filepath
    
    # 方法2: 搜索目錄中所有包含 task_id 的文件
    for file in DOWNLOAD_DIR.iterdir():
        if file.is_file() and task_id in file.name:
            size = file.stat().st_size
            print(f"[FILE] 找到文件(方法2): {file.name}, 大小: {size} bytes")
            return file
    
    # 方法3: 搜索最近修改的文件（60秒內）
    current_time = datetime.now().timestamp()
    recent_files = []
    for file in DOWNLOAD_DIR.iterdir():
        if file.is_file():
            mtime = file.stat().st_mtime
            if current_time - mtime < 60:  # 60秒內修改的文件
                recent_files.append((file, mtime))
    
    if recent_files:
        # 返回最近修改的文件
        recent_files.sort(key=lambda x: x[1], reverse=True)
        file = recent_files[0][0]
        size = file.stat().st_size
        print(f"[FILE] 找到文件(方法3-最近修改): {file.name}, 大小: {size} bytes")
        return file
    
    # 方法4: 列出目錄內容供調試
    print(f"[FILE] 未找到文件，當前目錄內容:")
    for file in DOWNLOAD_DIR.iterdir():
        if file.is_file():
            print(f"[FILE]   - {file.name} ({file.stat().st_size} bytes)")
    
    return None


def download_video_task(task_id, url):
    """後台下載視頻任務"""
    import traceback
    
    try:
        import yt_dlp
        
        task = download_tasks[task_id]
        
        # 處理短鏈接
        original_url = url
        url = expand_short_url(url)
        task['url'] = url
        
        site_name = get_site_name(url)
        print(f"[{task_id}] ====== 開始處理 ======")
        print(f"[{task_id}] 原始URL: {original_url}")
        print(f"[{task_id}] 展開後URL: {url}")
        print(f"[{task_id}] 網站類型: {site_name}")
        
        url_lower = url.lower()
        is_bilibili = 'bilibili' in url_lower
        is_douyin = any(x in url_lower for x in ['douyin', 'iesdouyin'])
        is_kuaishou = any(x in url_lower for x in ['kuaishou', 'chenzhongtech'])
        
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
                print(f"[{task_id}] yt-dlp 報告下載完成")
        
        # 基礎配置 - v3.2 版本：移除 max_filesize 限制
        ydl_opts = {
            'outtmpl': str(DOWNLOAD_DIR / f'{task_id}.%(ext)s'),
            'progress_hooks': [progress_hook],
            'quiet': False,
            'no_warnings': False,
            'merge_output_format': 'mp4',
            # 注意：不在這裡設置 max_filesize，讓 yt-dlp 先完成下載
        }
        
        # 構建請求頭
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        if is_bilibili:
            print(f"[{task_id}] 應用 Bilibili 專用配置")
            headers['Referer'] = 'https://www.bilibili.com'
            # 先不限制文件大小，讓下載完成後再檢查
            ydl_opts['format'] = 'best/worst'
            ydl_opts['extractor_args'] = {
                'bilibili': {
                    'prefer_flv': False,
                }
            }
            
        elif is_douyin:
            print(f"[{task_id}] 應用抖音專用配置")
            headers['Referer'] = 'https://www.douyin.com/'
            ydl_opts['format'] = 'best/worst'
            
        elif is_kuaishou:
            print(f"[{task_id}] 應用快手專用配置")
            headers['Referer'] = 'https://www.kuaishou.com/'
            ydl_opts['format'] = 'best/worst'
            
        else:
            print(f"[{task_id}] 應用通用配置")
            ydl_opts['format'] = 'best[filesize<100M]/worst'
        
        ydl_opts['headers'] = headers
        
        print(f"[{task_id}] 格式選項: {ydl_opts.get('format')}")
        
        # 提取視頻信息（不下載）
        print(f"[{task_id}] 步驟1: 提取視頻信息...")
        info = None
        try:
            info_opts = ydl_opts.copy()
            info_opts['quiet'] = True
            
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
            if info:
                formats = info.get('formats', [])
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)
                
                print(f"[{task_id}] 視頻標題: {title}")
                print(f"[{task_id}] 視頻時長: {duration}秒")
                print(f"[{task_id}] 可用格式數: {len(formats)}")
                
                # 估算文件大小
                if formats:
                    for f in formats[:3]:
                        filesize = f.get('filesize') or f.get('filesize_approx', 0)
                        if filesize:
                            print(f"[{task_id}] 格式 {f.get('format_id')}: {filesize/1024/1024:.2f}MB")
                        
        except Exception as extract_err:
            print(f"[{task_id}] 提取信息失敗: {extract_err}")
            info = None
        
        # 下載視頻
        print(f"[{task_id}] 步驟2: 開始下載...")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                if info:
                    task['title'] = info.get('title', '未知標題')
                    print(f"[{task_id}] yt-dlp 報告提取完成: {task['title']}")
                    
                    # 嘗試找到下載的文件
                    found_file = find_downloaded_file(task_id)
                    
                    if found_file:
                        file_size = found_file.stat().st_size
                        file_size_mb = file_size / 1024 / 1024
                        print(f"[{task_id}] 找到文件: {found_file.name}, 大小: {file_size_mb:.2f}MB")
                        
                        # 檢查文件大小（50MB限制）
                        if file_size > 52 * 1024 * 1024:  # 52MB，留點餘量
                            print(f"[{task_id}] 文件超過50MB限制，刪除")
                            found_file.unlink()
                            task['status'] = 'failed'
                            # 詳細的錯誤提示
                            task['error'] = (
                                f'❌ 視頻大小超過免費版限制\n\n'
                                f'• 視頻大小: {file_size_mb:.1f} MB\n'
                                f'• 免費限制: 50 MB\n\n'
                                f'原因說明：\n'
                                f'1. Render 免費服務器存儲空間有限\n'
                                f'2. 該視頻時長較長或畫質較高\n\n'
                                f'建議：\n'
                                f'• 選擇較短的視頻（3分鐘以內）\n'
                                f'• 或使用其他工具下載'
                            )
                            return
                        
                        # 重命名文件
                        safe_title = re.sub(r'[<>:\"/\\|?*]', '_', task['title'])[:50]
                        new_filename = f"{safe_title}{found_file.suffix}"
                        new_filepath = DOWNLOAD_DIR / new_filename
                        
                        counter = 1
                        while new_filepath.exists():
                            new_filename = f"{safe_title}_{counter}{found_file.suffix}"
                            new_filepath = DOWNLOAD_DIR / new_filename
                            counter += 1
                        
                        found_file.rename(new_filepath)
                        task['filename'] = new_filename
                        print(f"[{task_id}] 文件重命名為: {new_filename}")
                    else:
                        print(f"[{task_id}] 錯誤: 未找到下載的文件")
                        task['status'] = 'failed'
                        # 詳細的錯誤提示
                        task['error'] = (
                            f'❌ 下載失敗 - 無法找到下載文件\n\n'
                            f'可能原因：\n'
                            f'1. 視頻格式不支持（嘗試了 mp4/webm/mkv/flv 等格式）\n'
                            f'2. yt-dlp 下載過程中出錯\n'
                            f'3. 服務器存儲權限問題\n\n'
                            f'建議：\n'
                            f'• 嘗試其他視頻鏈接\n'
                            f'• 複製完整的 Bilibili 視頻網址（非短鏈接）\n'
                            f'• 如持續失敗，請聯繫管理員查看服務器日誌'
                        )
                        return
                        
        except Exception as download_err:
            print(f"[{task_id}] 下載過程出錯: {download_err}")
            raise download_err
        
        task['status'] = 'completed'
        task['progress'] = 100
        print(f"[{task_id}] ====== 任務完成 ======")
        
    except Exception as e:
        task = download_tasks.get(task_id)
        if task:
            task['status'] = 'failed'
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            print(f"[{task_id}] ====== 任務失敗 ======")
            print(f"[{task_id}] 錯誤信息: {error_msg}")
            print(f"[{task_id}] 錯誤追蹤:\n{error_trace}")
            
            # 分析錯誤類型，提供詳細的錯誤提示
            error_lower = error_msg.lower()
            url_lower = url.lower() if 'url' in locals() else ''
            is_bilibili = 'bilibili' in url_lower
            
            if 'format is not available' in error_lower:
                if is_bilibili:
                    task['error'] = (
                        f'❌ Bilibili 視頻無可用格式\n\n'
                        f'可能原因：\n'
                        f'1. 會員專屬視頻（需要大會員）\n'
                        f'2. 版權保護的番劇/電影\n'
                        f'3. 視頻已被刪除或下架\n\n'
                        f'建議：\n'
                        f'• 嘗試其他公開的普通視頻\n'
                        f'• 確保視頻不需要登錄即可觀看'
                    )
                else:
                    task['error'] = (
                        f'❌ 該視頻無可用格式\n\n'
                        f'可能原因：\n'
                        f'• 視頻網站不支持\n'
                        f'• 視頻已被刪除\n\n'
                        f'建議：嘗試其他視頻'
                    )
            elif 'unable to extract' in error_lower:
                if is_bilibili and 'b23.tv' in original_url:
                    task['error'] = (
                        f'❌ 無法提取短鏈接視頻信息\n\n'
                        f'可能原因：\n'
                        f'• b23.tv 短鏈接已過期（有效期通常24小時）\n'
                        f'• 短鏈接被限制訪問\n\n'
                        f'建議：\n'
                        f'• 在 Bilibili App/網頁中重新複製視頻鏈接\n'
                        f'• 使用完整的視頻網址：\n'
                        f'  https://www.bilibili.com/video/BVxxxxx'
                    )
                else:
                    task['error'] = (
                        f'❌ 無法提取視頻信息\n\n'
                        f'可能原因：\n'
                        f'• 視頻網址錯誤或無效\n'
                        f'• 視頻已被刪除或設為私密\n\n'
                        f'建議：\n'
                        f'• 檢查網址是否正確\n'
                        f'• 在瀏覽器中確認視頻可以正常播放'
                    )
            elif 'not available in your country' in error_lower or 'region' in error_lower:
                task['error'] = (
                    f'❌ 地區限制錯誤\n\n'
                    f'說明：\n'
                    f'該視頻僅限特定地區觀看\n\n'
                    f'原因：\n'
                    f'• 服務器位於美國（Render）\n'
                    f'• 某些視頻僅限中國大陸訪問\n\n'
                    f'建議：\n'
                    f'• 嘗試其他無地區限制的視頻\n'
                    f'• 或使用其他下載工具'
                )
            elif 'sign in' in error_lower or 'login' in error_lower:
                task['error'] = (
                    f'❌ 需要登錄才能訪問\n\n'
                    f'說明：\n'
                    f'該視頻僅限登錄用戶觀看\n\n'
                    f'可能原因：\n'
                    f'• UP主設置了觀看權限\n'
                    f'• 敏感內容限制\n\n'
                    f'建議：\n'
                    f'• 嘗試其他公開視頻\n'
                    f'• 該工具不支持登錄功能'
                )
            elif 'copyright' in error_lower:
                task['error'] = (
                    f'❌ 版權保護限制\n\n'
                    f'說明：\n'
                    f'該視頻受版權保護，無法下載\n\n'
                    f'常見情況：\n'
                    f'• 電影、電視劇\n'
                    f'• 音樂MV\n'
                    f'• 有版權聲明的內容'
                )
            elif 'filesize' in error_lower or '50m' in error_lower:
                task['error'] = (
                    f'❌ 視頻超過 50MB 限制\n\n'
                    f'說明：\n'
                    f'免費版服務器存儲空間有限，\n'
                    f'無法下載大文件。\n\n'
                    f'建議：\n'
                    f'• 選擇較短的視頻（3分鐘以內）\n'
                    f'• 或降低視頻畫質後再試'
                )
            elif '403' in error_msg:
                task['error'] = (
                    f'❌ 訪問被拒絕 (403)\n\n'
                    f'可能原因：\n'
                    f'• 服務器IP被視頻網站封禁\n'
                    f'• 需要登錄才能訪問\n'
                    f'• 訪問頻率過高被限制\n\n'
                    f'建議：\n'
                    f'• 稍後重試\n'
                    f'• 嘗試其他視頻'
                )
            elif '404' in error_msg:
                task['error'] = (
                    f'❌ 視頻不存在 (404)\n\n'
                    f'可能原因：\n'
                    f'• 視頻已被刪除\n'
                    f'• 視頻網址錯誤\n'
                    f'• UP主設為私密\n\n'
                    f'建議：檢查網址是否正確'
                )
            elif 'timeout' in error_lower:
                task['error'] = (
                    f'❌ 連接超時\n\n'
                    f'可能原因：\n'
                    f'• 網絡不穩定\n'
                    f'• 視頻網站響應慢\n'
                    f'• 服務器資源繁忙\n\n'
                    f'建議：請重試'
                )
            else:
                # 未知錯誤，顯示簡短的錯誤信息
                task['error'] = (
                    f'❌ 下載失敗\n\n'
                    f'錯誤信息：{error_msg[:100]}\n\n'
                    f'建議：\n'
                    f'• 嘗試其他視頻\n'
                    f'• 檢查網址是否正確\n'
                    f'• 稍後重試'
                )


@app.errorhandler(404)
def not_found(e):
    """404 錯誤處理"""
    return render_template('login.html'), 404


if __name__ == '__main__':
    print("=" * 60)
    print("  視頻下載器 - 雲端版 v3.2")
    print("=" * 60)
    print("\n訪問地址: http://localhost:5000")
    print("密碼: felix96\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
