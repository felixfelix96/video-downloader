@echo off
chcp 65001 >nul
title 創建視頻下載器 Windows 服務
color 0a

echo ==========================================
echo 創建視頻下載器開機自啟動服務
echo ==========================================
echo.

:: 檢查管理員權限
net session >nul 2>&1
if errorlevel 1 (
    echo [錯誤] 請以管理員身份運行此腳本！
    pause
    exit /b 1
)

echo [1/4] 安裝 nssm（服務管理工具）...
if not exist "C:\nssm" (
    mkdir C:\nssm
    echo [提示] 正在下載 nssm...
    powershell -Command "Invoke-WebRequest -Uri 'https://nssm.cc/release/nssm-2.24.zip' -OutFile 'C:\Temp\nssm.zip'"
    powershell -Command "Expand-Archive -Path 'C:\Temp\nssm.zip' -DestinationPath 'C:\nssm' -Force"
    copy "C:\nssm\nssm-2.24\win64\nssm.exe" "C:\nssm\nssm.exe"
    echo [OK] nssm 安裝完成
) else (
    echo [OK] nssm 已存在
)

echo.
echo [2/4] 創建服務...
C:\nssm\nssm.exe install VideoDownloader "C:\Users\Administrator\AppData\Local\Programs\Python\Python311\python.exe"
C:\nssm\nssm.exe set VideoDownloader AppDirectory "C:\video-downloader"
C:\nssm\nssm.exe set VideoDownloader AppParameters "app.py"
C:\nssm\nssm.exe set VideoDownloader DisplayName "視頻下載器"
C:\nssm\nssm.exe set VideoDownloader Description "Bilibili/抖音/快手視頻下載服務"
C:\nssm\nssm.exe set VideoDownloader Start SERVICE_AUTO_START
echo [OK] 服務創建完成

echo.
echo [3/4] 啟動服務...
net start VideoDownloader
if errorlevel 1 (
    echo [警告] 服務啟動失敗，可能需要手動啟動
) else (
    echo [OK] 服務已啟動
)

echo.
echo [4/4] 設置開機自啟動...
sc config VideoDownloader start= auto
echo [OK] 開機自啟動已設置

echo.
echo ==========================================
echo 服務配置完成！
echo ==========================================
echo.
echo 服務名稱：VideoDownloader
echo.
echo 常用命令：
echo   啟動服務：net start VideoDownloader
echo   停止服務：net stop VideoDownloader
echo   查看狀態：sc query VideoDownloader
echo   刪除服務：sc delete VideoDownloader
echo.
echo 現在可以通過以下地址訪問：
echo   http://你的公網IP:5000
echo.
pause
