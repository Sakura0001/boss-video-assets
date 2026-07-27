# Windows 迁移与运行

本项目在 Windows 上采用 PowerShell + Python + 本地 Chrome/Edge。业务规则
来自仓库的 `skills/boss-zhaopin/`；登录、岗位识别、候选人筛选、打招呼、
三条知识库消息和断点续跑都封装在 `scripts/greet_only.py` 中。

## 1. 安装依赖

使用 64 位 Windows 10 1809 或更高版本，安装：

- Git for Windows
- Node.js 20 或更高版本
- 64 位 Python 3.9 或更高版本，并启用 `py` launcher
- Google Chrome 或 Microsoft Edge

关闭并重新打开 PowerShell，然后验证：

```powershell
git --version
node --version
npm --version
py -3 --version
```

## 2. 克隆并准备项目

```powershell
$ProjectHome = Join-Path $env:USERPROFILE "boss-recruiting"
New-Item -ItemType Directory -Path $ProjectHome -Force | Out-Null
Set-Location $ProjectHome
git clone -b codex/ai-greet-only-python --single-branch https://github.com/Sakura0001/boss-video-assets.git
Set-Location .\boss-video-assets
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-windows.ps1
```

安装脚本会从本仓库源码构建并链接 `boss` 命令，不会执行 `boss update`，也不会把登录数据或候选人数据写入仓库。

默认本地状态位置：

```text
%USERPROFILE%\.codex\state\boss-zhaopin\
```

Boss 浏览器数据位置：

```text
%USERPROFILE%\.boss-cli\
```

如需改变招聘状态目录，可在运行 Python 前设置：

```powershell
$env:BOSS_ZHAOPIN_STATE_DIR = "D:\PrivateData\boss-zhaopin"
```

如脚本找不到浏览器，可设置：

```powershell
$env:CHROME_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

## 3. 从旧电脑迁移招聘状态

这一步强烈建议执行。`state.sqlite3` 保存当日招呼计数、长期去重、候选人阶段和微信交换台账；如果直接使用空库，Windows 无法知道旧电脑已经联系过谁，存在重复触达风险。

迁移前：

1. 停止 macOS 上的招聘 Python 执行器和所有 `boss` 命令。
2. 确认 Windows 上也没有正在运行的招聘执行器。
3. 不通过 Git、网盘公开链接或聊天附件传输状态库；使用加密U盘、受控内网或其他私密通道。

macOS 源文件：

```text
/Users/yuyu/.codex/state/boss-zhaopin/state.sqlite3
```

把它复制到 Windows 的私密临时位置，再在项目根目录的 PowerShell 中执行：

```powershell
$StateRoot = if ($env:BOSS_ZHAOPIN_STATE_DIR) {
    $env:BOSS_ZHAOPIN_STATE_DIR
} else {
    Join-Path $env:USERPROFILE ".codex\state\boss-zhaopin"
}

New-Item -ItemType Directory -Path $StateRoot -Force | Out-Null
Copy-Item "E:\PrivateTransfer\state.sqlite3" (Join-Path $StateRoot "state.sqlite3")
$CurrentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $StateRoot /inheritance:r /grant:r "${CurrentIdentity}:(OI)(CI)F"

$Today = Get-Date -Format "yyyy-MM-dd"
py -3 .\skills\boss-zhaopin\scripts\runtime_store.py greeting-count --date $Today
```

核对输出的当天招呼数是否符合旧电脑记录。迁移完成后删除私密临时副本。不要同时在两台电脑上运行招聘；本地锁不能跨电脑阻止重复发送。

如果确定不迁移旧状态，必须明确接受长期去重和历史台账缺失，并建议从新的一天开始运行。

## 4. 首次登录与每天运行

每天需要运行时，在项目根目录打开 PowerShell：

```powershell
Set-Location C:\path\to\boss-video-assets
py -3 .\scripts\greet_only.py
```

这是唯一的日常启动命令。程序会：

1. 检查 `boss` CLI 是否可用。
2. 检查当前登录状态。
3. 未登录时自动打开 Boss 登录页，并最多等待 10 分钟。
4. 用户在浏览器完成登录后自动继续，无需回到终端按键。
5. 读取 Boss 推荐页当前选中的默认岗位，不要求输入岗位名。
6. 按知识库筛选候选人，打招呼并发送三条知识库原文。
7. 从本机当天已有计数继续，达到累计 150 个后退出。

不要复制 macOS 的 Chrome 登录缓存到 Windows。Windows 上重新登录更安全，
也避免跨系统 profile 锁和版本不兼容。

如只想验证安装和知识库，不登录、不发送：

```powershell
py -3 .\scripts\greet_only.py --validate-only
```

脚本使用 `boss recommend --json` 获取结构化候选人数据和页面右侧全部教育
经历；硕士或博士显示多所学校时，任意一所精确命中目标名单即可。它按仓库
`skills\boss-zhaopin\references\` 中的学校、专业和话术原文判断并发送。
每批十人没有合格人选时刷新推荐页；每位候选人操作前随机等待 1–2 秒。

每位候选人的三条消息只打开一次精确会话，并在同一浏览器会话内逐条发送
和验证。程序不调用 Claude、不处理未读、不跟进、不交换微信，也不自行生成
消息。

脚本运行期间：

- 保持 Boss 专用浏览器、PowerShell、电脑和网络正常运行。
- 不要同时启动第二个脚本、其他 Boss 自动化或在另一台电脑运行。
- `Ctrl+C` 可安全停止；下次会从本机已有计数继续。
- 只在 Asia/Shanghai 09:00–21:00 发送。
- 验证码、平台风控、登录异常、岗位意外变化或消息验证失败会立即停止。
- 平台点击“打招呼”产生的默认开场白由 Boss 账号配置决定；随后三条消息
  严格读取 `references\greetings.md`。

## 5. 更新项目

更新前先停止 Python 执行器，再执行：

```powershell
git pull
.\scripts\setup-windows.ps1
```

不要运行 `boss update` 覆盖仓库内可能尚未发布的 CLI 修复。

## 6. 常见问题

### `boss` 找不到

关闭并重新打开 PowerShell，再运行：

```powershell
Get-Command boss
```

仍找不到时，在 `tools\boss-cli` 下重新执行 `npm link`。

### 登录或浏览器启动失败

关闭占用 `%USERPROFILE%\.boss-cli\.cache\browser-data` 的旧 Chrome/Edge 进程，
再重新运行 `py -3 .\scripts\greet_only.py`。不要删除目录，除非明确接受
重新登录。
