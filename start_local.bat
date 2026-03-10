@echo off
chcp 65001 >nul
echo ========================================
echo 視頻下載器 - 本地部署啟動腳本
echo ========================================
echo.

:: 檢查 Python
echo [1/4] 檢查 Python 環境...
python --version >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 未檢測到 Python，請先安裝 Python 3.8+
    pause
    exit /b 1
)
echo [OK] Python 已安裝

:: 檢查依賴
echo [2/4] 檢查依賴包...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安裝依賴包，請稍候...
    pip install flask flask-limiter yt-dlp requests
)
echo [OK] 依賴包已就緒

:: 啟動服務
echo [3/4] 啟動視頻下載器服務...
echo [提示] 服務將在 http://localhost:5000 運行
echo.
start python app.py

:: 等待服務啟動
timeout /t 3 /nobreak >nul

:: 檢查 ngrok
echo [4/4] 檢查 ngrok...
where ngrok >nul 2>&1
if errorlevel 1 (
    echo.
    echo ========================================
    echo [警告] 未檢測到 ngrok
    echo ========================================
    echo.
    echo 如果你想讓朋友通過公網訪問，需要：
    echo.
    echo 1. 訪問 https://ngrok.com/download 下載 ngrok
    echo 2. 解壓 ngrok.exe 到任意文件夾
    echo 3. 訪問 https://dashboard.ngrok.com/signup 註冊賬號
    echo 4. 獲取 Authtoken 並執行：ngrok config add-authtoken YOUR_TOKEN
    echo 5. 然後運行：ngrok http 5000
    echo.
    echo 當前只能本機訪問：http://localhost:5000
    echo.
) else (
    echo [OK] ngrok 已安裝
    echo.
    echo ========================================
    echo 正在啟動 ngrok 內網穿透...
    echo ========================================
    echo.
    start ngrok http 5000
    timeout /t 2 /nobreak >nul
    echo [提示] ngrok 啟動後，請查看窗口中的 https://xxx.ngrok-free.app 鏈接
    echo [提示] 把這個鏈接發給朋友，他們就能使用了！
    echo.
)

echo ========================================
echo 啟動完成！
echo ========================================
echo.
echo 訪問地址：
echo   - 本機訪問：http://localhost:5000
echo   - 密碼：felix96
echo.
echo 注意：
echo   - 請保持此窗口和 ngrok 窗口運行
echo   - 關閉窗口後服務停止
echo   - 默認密碼可在 app.py 中修改
echo.
pause
