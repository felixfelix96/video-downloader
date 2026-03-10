# 阿里云 ECS 运行部署脚本详细步骤

## 前提

已成功远程连接到阿里云 Windows Server 2022 服务器

---

## 方法一：直接在服务器上下载并运行（推荐）

### 1. 在服务器上打开浏览器

- 点击任务栏的 Edge 浏览器图标
- 或按 `Win` 键搜索 "Edge"

### 2. 下载项目文件

- 访问：https://github.com/felixfelix96/video-downloader
- 点击绿色的 **"Code"** 按钮
- 点击 **"Download ZIP"**
- 下载完成后，解压到 `C:\video-downloader`

### 3. 以管理员身份运行脚本

**步骤：**

1. 按 `Win` 键，搜索 **"cmd"** 或 **"PowerShell"**
2. 右侧选择 **"以管理员身份运行"**
   
   或
   
   右键点击 CMD/PowerShell → **"以管理员身份运行"**

3. 在打开的窗口中输入：

```cmd
cd C:\video-downloader
deploy_to_aliyun.bat
```

4. 按回车，按提示操作

---

## 方法二：从你电脑上传文件到服务器

### 1. 复制文件

在你的电脑上，选中这些文件：
- `app.py`
- `requirements.txt`
- `templates` 文件夹（包含 index.html 和 login.html）
- `deploy_to_aliyun.bat`

### 2. 粘贴到服务器

- 在远程桌面窗口中
- 打开 `C:\` 盘
- 创建文件夹 `video-downloader`
- 把文件粘贴进去

### 3. 运行脚本

在服务器上：
1. 打开 `C:\video-downloader` 文件夹
2. 右键点击 `deploy_to_aliyun.bat`
3. 选择 **"以管理员身份运行"**

---

## 方法三：使用 PowerShell 一键下载并安装

在服务器上以管理员身份运行 PowerShell，然后复制粘贴以下命令：

```powershell
# 创建目录
New-Item -ItemType Directory -Force -Path C:\video-downloader
Set-Location C:\video-downloader

# 下载文件
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/felixfelix96/video-downloader/master/app.py" -OutFile "app.py"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/felixfelix96/video-downloader/master/requirements.txt" -OutFile "requirements.txt"

# 创建 templates 目录并下载
New-Item -ItemType Directory -Force -Path C:\video-downloader\templates
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/felixfelix96/video-downloader/master/templates/index.html" -OutFile "templates\index.html"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/felixfelix96/video-downloader/master/templates/login.html" -OutFile "templates\login.html"

# 安装依赖
pip install flask flask-limiter yt-dlp requests

# 启动服务
python app.py
```

---

## 运行后看到什么表示成功？

```
========================================
視頻下載器 v3.5 啟動中...
========================================
 * Running on http://0.0.0.0:5000
```

看到这一行就表示启动成功了！

---

## 然后做什么？

### 1. 配置安全组（关键！）

在阿里云控制台：
1. 找到你的 ECS 实例
2. 点击 **"网络与安全组"**
3. 点击 **"配置规则"**
4. 点击 **"手动添加"**
5. 填写：
   - 协议类型：自定义 TCP
   - 端口范围：5000
   - 授权对象：0.0.0.0/0
6. 点击 **"保存"**

### 2. 访问网站

在浏览器打开：
```
http://47.110.83.76:5000
```

输入密码：`felix96`

---

## 常见问题

### Q: 提示 "请以管理员身份运行"
**A:** 右键点击 CMD 或 PowerShell，选择 "以管理员身份运行"

### Q: 提示 "pip 不是内部或外部命令"
**A:** Python 没安装好，先安装 Python 并勾选 "Add to PATH"

### Q: 脚本运行到一半卡住
**A:** 可能是网络问题，按 `Ctrl + C` 取消，重新运行

### Q: 如何关闭服务？
**A:** 在 CMD 窗口按 `Ctrl + C`，或直接关闭 CMD 窗口

---

## 最简单的办法

如果你嫌麻烦，直接在服务器上：

1. 安装 Python（官网下载安装包）
2. `Win + R` 输入 `cmd`
3. 依次执行：

```cmd
cd C:\
mkdir video-downloader
cd video-downloader

# 手动把 app.py 和 templates 文件夹复制进来

pip install flask flask-limiter yt-dlp
python app.py
```

然后配置安全组即可！
