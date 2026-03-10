# 視頻下載器 - 阿里云 ECS 部署指南

## 🎉 優勢

- ✅ 國內服務器，無 Bilibili 地區限制
- ✅ 無 50MB 文件大小限制
- ✅ 24小時在線，無需保持電腦開機
- ✅ 固定公網 IP，隨時訪問

---

## 🚀 快速部署（Windows Server 2022）

### 1. 遠程連接服務器

1. 在阿里云控制台點擊 **"遠程連接"**
2. 或使用 Windows 遠程桌面連接：
   - 按 `Win + R`，輸入 `mstsc`
   - 輸入公網 IP：`47.110.83.76`
   - 用戶名：`Administrator`
   - 密碼：你的實例密碼

### 2. 安裝 Python

在服務器上打開 PowerShell 或 CMD：

```powershell
# 下載 Python 安裝包
Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe" -OutFile "python-installer.exe"

# 安裝 Python（靜默安裝，添加到 PATH）
.\python-installer.exe /quiet InstallAllUsers=1 PrependPath=1

# 驗證安裝
python --version
```

或手動下載安裝：https://python.org/downloads

### 3. 下載項目代碼

```powershell
# 創建目錄
mkdir C:\video-downloader
cd C:\video-downloader

# 下載代碼（需要安裝 git，或手動下載 ZIP）
# 方法1：使用 git
git clone https://github.com/felixfelix96/video-downloader.git .

# 方法2：手動下載 ZIP 並解壓到 C:\video-downloader
```

### 4. 安裝依賴

```powershell
cd C:\video-downloader

# 安裝 Python 依賴
pip install flask flask-limiter yt-dlp requests gunicorn
```

### 5. 配置安全組（重要！）

1. 回到阿里云控制台
2. 點擊 **"網絡與安全組"**
3. 點擊 **"安全組配置"**
4. 點擊 **"配置規則"**
5. 添加以下規則：

| 類型 | 協議 | 端口範圍 | 授權對象 | 說明 |
|------|------|---------|---------|------|
| 自定義 TCP | TCP | 5000 | 0.0.0.0/0 | 視頻下載器服務 |
| 自定義 TCP | TCP | 3389 | 你的IP/32 | 遠程桌面（限制IP更安全）|

### 6. 啟動服務

```powershell
cd C:\video-downloader
python app.py
```

看到以下輸出表示成功：
```
========================================
視頻下載器 v3.5 啟動中...
========================================
 * Running on http://0.0.0.0:5000
```

### 7. 訪問服務

在瀏覽器中打開：
```
http://47.110.83.76:5000
```

**密碼：** `felix96`

---

## 🔧 設置開機自啟動

### 方法：使用任務計劃程序

1. 打開 **"任務計劃程序"**（Task Scheduler）
2. 點擊 **"創建基本任務"**
3. 名稱：`VideoDownloader`
4. 觸發器：**"當計算機啟動時"**
5. 操作：**"啟動程序"**
6. 程序：`C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe`
7. 參數：`C:\video-downloader\app.py`
8. 完成並勾選 **"打開屬性對話框"**
9. 在屬性中：
   - 勾選 **"使用最高權限運行"**
   - 選擇 **"不管用戶是否登錄都要運行"**

---

## 🛡️ 使用 Nginx 反向代理（推薦，可綁定域名）

### 1. 安裝 Nginx

```powershell
# 下載 Nginx
Invoke-WebRequest -Uri "http://nginx.org/download/nginx-1.24.0.zip" -OutFile "nginx.zip"
Expand-Archive -Path "nginx.zip" -DestinationPath "C:\"
Rename-Item "C:\nginx-1.24.0" "C:\nginx"
```

### 2. 配置 Nginx

編輯 `C:\nginx\conf\nginx.conf`，在 `server` 段添加：

```nginx
server {
    listen 80;
    server_name 47.110.83.76;  # 或你的域名

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 3. 啟動 Nginx

```powershell
cd C:\nginx
start nginx
```

### 4. 修改安全組

- 開放 **80** 端口（HTTP）
- 可以關閉 5000 端口（只能通過 Nginx 訪問）

---

## 📋 常用命令

```powershell
# 查看服務是否運行
Get-Process python

# 停止服務
Stop-Process -Name python -Force

# 重新啟動服務
cd C:\video-downloader
python app.py

# 查看磁盤空間
cd C:\video-downloader\downloads
dir

# 清理下載文件
Remove-Item "C:\video-downloader\downloads\*" -Recurse -Force
```

---

## 🔒 安全建議

1. **修改默認密碼**
   - 編輯 `app.py`，修改 `PASSWORD = "felix96"`

2. **限制訪問 IP**
   - 在安全組中，將 5000 端口的授權對象改為你的 IP 地址

3. **使用 HTTPS**
   - 申請免費 SSL 證書（Let's Encrypt）
   - 或購買阿里云 SSL 證書

4. **定期備份**
   - 創建 ECS 快照
   - 或備份 `downloads` 文件夾

---

## ❓ 常見問題

### Q: 為什麼訪問不了？
**A:** 檢查安全組是否開放了 5000 端口

### Q: 如何查看日誌？
**A:** 服務器上運行 Python 的窗口會顯示實時日誌

### Q: 下載的文件在哪？
**A:** `C:\video-downloader\downloads\`

### Q: 如何升級 yt-dlp？
**A:** 
```powershell
pip install -U yt-dlp
```

---

## 🎉 完成！

現在你有了一個 24 小時在線的視頻下載服務！

**訪問地址：** http://47.110.83.76:5000
**密碼：** felix96
