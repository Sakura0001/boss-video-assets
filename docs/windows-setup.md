# Windows 迁移与运行

本项目在 Windows 上采用原生 Claude Code + PowerShell + 本地 Chrome/Edge。业务规则仍来自仓库的 `skills/boss-zhaopin/`，Claude Code 通过项目级 `.claude/skills/boss-zhaopin/` 桥接加载；日间招聘提示词位于 `.claude/loop.md`。

## 1. 安装依赖

使用 64 位 Windows 10 1809 或更高版本，安装：

- Git for Windows
- Node.js 20 或更高版本
- 64 位 Python 3.9 或更高版本，并启用 `py` launcher
- Google Chrome 或 Microsoft Edge
- Claude Code

Claude Code 必须为 2.1.72 或更高版本，且不能设置 `CLAUDE_CODE_DISABLE_CRON=1`，否则 `/loop` 不可用。Git for Windows 用于克隆仓库；Claude Code 在安装 Git Bash 后可能使用 Bash 工具，在未启用 Git Bash 时使用 PowerShell。本项目的 Loop 提示词不依赖固定 shell。

Claude Code 官方推荐的 PowerShell 安装命令：

```powershell
irm https://claude.ai/install.ps1 | iex
```

关闭并重新打开 PowerShell，然后验证：

```powershell
git --version
node --version
npm --version
py -3 --version
claude --version
claude doctor
```

## 2. 克隆并准备项目

```powershell
git clone https://github.com/Sakura0001/boss-video-assets.git
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

如需改变招聘状态目录，可在启动 Claude Code 前设置：

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

1. 停止 macOS 上的招聘 Loop 和所有 `boss` 命令。
2. 确认 Windows 上也没有正在运行的招聘 Loop。
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

## 4. 首次登录

```powershell
boss login
```

在打开的浏览器中完成 Boss 登录，然后验证：

```powershell
boss list --unread
```

不要复制 macOS 的 Chrome 登录缓存到 Windows。Windows 上重新登录更安全，也避免跨系统 profile 锁和版本不兼容。

## 5. 每天手动启动招聘 Loop

每天需要运行时，在项目根目录打开 PowerShell：

```powershell
Set-Location C:\path\to\boss-video-assets
claude
```

首次进入项目时接受目录信任，然后在 Claude Code 中输入：

```text
/loop 1m
```

Claude Code 会读取项目级 `.claude/loop.md`，每分钟调度一次招聘提示。当前回合超过一分钟时，下一次提示会等当前回合结束，不会在回合中途并行执行。

`/loop` 的调度粒度为一分钟，固定任务可能带有最多约半个间隔的确定性抖动。长回合期间错过的触发不会逐次补跑；Claude Code 空闲后只执行一次。因此单轮超过一分钟不会产生并行招聘执行器。

运行条件：

- 保持 Claude Code 会话打开。
- 保持电脑唤醒并联网。
- 只在 Asia/Shanghai 09:00–21:00发送。
- 按 `Esc` 可停止等待中的 `/loop`。
- 达到150个招呼后只停止新招呼，未读和到期跟进继续处理。
- 每天只在一台电脑、一个 Claude Code 会话中运行。

小时报告写在：

```text
%USERPROFILE%\.codex\state\boss-zhaopin\hourly-reports\
```

### 只执行主动打招呼和三条知识库消息

如果当天不处理未读、跟进、简历和微信，不必启动 Claude Code `/loop`。
在仓库根目录的 PowerShell 中先校验配置：

```powershell
py -3 .\scripts\greet_only.py
```

校验通过后执行：

```powershell
py -3 .\scripts\greet_only.py --execute --job "ai应用研发工程师" --target 150
```

这个脚本使用 `boss recommend --json` 获取结构化候选人数据，按仓库
`skills\boss-zhaopin\references\` 中的学校、专业和话术原文判断并发送。
它会读取本机状态库中的今日招呼数，从已有计数继续；每批十人没有合格人选
时执行推荐页刷新。每位候选人操作前会随机等待 1–2 秒，进度输出会显示
本次等待时间和该候选人的完整流程耗时。它不会调用 Claude、处理未读、
执行跟进或交换微信。

脚本运行期间：

- 不要同时启动 `/loop`、第二个脚本或另一台电脑。
- 保持 Boss 专用浏览器、PowerShell、电脑和网络正常运行。
- `Ctrl+C` 可停止；已成功的招呼已经写入状态库，下一次从现有计数继续。
- 验证码、平台风控、登录异常、精确会话失败或消息验证失败会立即停止。
- 平台点击“打招呼”产生的默认开场白由 Boss 账号配置决定；脚本随后发送的
  三条消息严格读取 `references\greetings.md`，不自行生成。

## 6. 更新项目

更新前先停止 Loop，再执行：

```powershell
git pull
.\scripts\setup-windows.ps1
```

不要运行 `boss update` 覆盖仓库内可能尚未发布的 CLI 修复。

## 7. 常见问题

### `boss` 找不到

关闭并重新打开 PowerShell，再运行：

```powershell
Get-Command boss
```

仍找不到时，在 `tools\boss-cli` 下重新执行 `npm link`。

### Claude Code 找不到 `/loop`

确认 `claude --version` 不低于 2.1.72，并确认是在仓库根目录启动。项目必须包含 `.claude\loop.md`。同时检查：

```powershell
Get-ChildItem Env:CLAUDE_CODE_DISABLE_CRON
```

如果该变量的值为 `1`，请取消它后重新启动 Claude Code。

### Claude Code 找不到项目 skill

确认以下两个文件存在：

```text
.claude\skills\boss-zhaopin\SKILL.md
skills\boss-zhaopin\SKILL.md
```

如果 `.claude\skills` 是在 Claude Code 启动后首次创建，退出并重新启动 Claude Code。

### 登录或浏览器启动失败

关闭占用 `%USERPROFILE%\.boss-cli\.cache\browser-data` 的旧 Chrome/Edge 进程，再运行 `boss login`。不要删除目录，除非明确接受重新登录。

## 8. 官方参考

- [Claude Code Windows 安装](https://code.claude.com/docs/en/setup)
- [Claude Code `/loop` 定时任务](https://code.claude.com/docs/en/scheduled-tasks)
- [Claude Code 项目 Skills](https://code.claude.com/docs/en/skills)
