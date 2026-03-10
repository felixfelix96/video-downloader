@echo off
chcp 65001 >nul
title 視頻下載器 - 阿里云 ECS 部署腳本
color 0a

echo ==========================================
echo 視頻下載器 - 阿里云 ECS 一鍵部署腳本
echo ==========================================
echo.
echo [提示] 此腳本將在阿里云 Windows Server 上部署視頻下載器
echo.
pause

:: 檢查管理員權限
net session >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 請以管理員身份運行此腳本！
    pause
    exit /b 1
)

echo.
echo [1/6] 檢查 Python 環境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [提示] Python 未安裝，開始下載安裝...
    echo [提示] 正在下載 Python 3.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe' -OutFile 'C:\Temp\python-installer.exe'"
    echo [提示] 正在安裝 Python（請等待）...
    C:\Temp\python-installer.exe /quiet InstallAllUsers=1 PrependPath=1
    echo [提示] Python 安裝完成，請重新運行此腳本
    pause
    exit /b 0
)
echo [OK] Python 已安裝
python --version

echo.
echo [2/6] 創建項目目錄...
if not exist "C:\video-downloader" (
    mkdir C:\video-downloader
    echo [OK] 目錄創建成功
) else (
    echo [OK] 目錄已存在
)

echo.
echo [3/6] 下載項目代碼...
cd C:\video-downloader
echo [提示] 請手動將以下文件複製到 C:\video-downloader 目錄：
echo   - app.py
echo   - requirements.txt
echo   - templates\index.html
echo   - templates\login.html
echo.
echo 如果你已經複製了文件，請按任意鍵繼續...
pause >nul

echo.
echo [4/6] 安裝 Python 依賴...
pip install -r requirements.txt
if errorlevel 1 (
    echo [錯誤] 依賴安裝失敗，嘗試單獨安裝...
    pip install flask flask-limiter yt-dlp requests
)
echo [OK] 依賴安裝完成

echo.
echo [5/6] 創建下載目錄...
if not exist "C:\video-downloader\downloads" (
    mkdir C:\video-downloader\downloads
)
echo [OK] 下載目錄已準備

echo.
echo [6/6] 配置防火牆...
echo [提示] 正在開放 5000 端口...
netsh advfirewall firewall add rule name="VideoDownloader" dir=in action=allow protocol=TCP localport=5000
echo [OK] 防火牆規則已添加

echo.
echo ==========================================
echo 部署完成！
echo ==========================================
echo.
echo 現在可以啟動服務了：
echo.
echo 方法1 - 手動啟動：
echo   cd C:\video-downloader
echo   python app.py
echo.
echo 方法2 - 創建開機自啟動：
echo   運行 create_service.bat
echo.
echo 訪問地址：
echo   http://你的公網IP:5000
echo.
echo 默認密碼：felix96
echo.
echo [重要] 請確保在阿里云控制台的安全組中開放 5000 端口！
echo.
pause
