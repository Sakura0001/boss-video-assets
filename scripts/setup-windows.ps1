[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Require-Command {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "缺少命令 '$Name'。$InstallHint"
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$CliRoot = Join-Path $RepoRoot "tools\boss-cli"
$SkillRoot = Join-Path $RepoRoot "skills\boss-zhaopin"

Require-Command -Name "git" -InstallHint "请安装 Git for Windows。"
Require-Command -Name "node" -InstallHint "请安装 Node.js 20 或更高版本。"
Require-Command -Name "npm" -InstallHint "npm 应随 Node.js 一起安装。"
Require-Command -Name "py" -InstallHint "请安装 64 位 Python 3，并启用 py launcher。"
Require-Command -Name "claude" -InstallHint "请先安装 Claude Code，然后打开新的 PowerShell。"

if ($env:CLAUDE_CODE_DISABLE_CRON -eq "1") {
    throw "CLAUDE_CODE_DISABLE_CRON=1 会禁用 /loop。请取消该环境变量后重试。"
}

$NodeMajor = [int](& node -p "Number(process.versions.node.split('.')[0])")
if ($LASTEXITCODE -ne 0 -or $NodeMajor -lt 20) {
    throw "boss-cli 要求 Node.js 20 或更高版本，当前主版本为 $NodeMajor。"
}

& py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "boss-zhaopin 要求 Python 3.9 或更高版本。"
}

$ClaudeVersionText = (& claude --version | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    throw "无法读取 Claude Code 版本。"
}
$ClaudeVersionMatch = [regex]::Match($ClaudeVersionText, '(?<!\d)(\d+)\.(\d+)\.(\d+)')
if (-not $ClaudeVersionMatch.Success) {
    throw "无法解析 Claude Code 版本：$ClaudeVersionText"
}
$ClaudeVersion = [version]$ClaudeVersionMatch.Value
if ($ClaudeVersion -lt [version]'2.1.72') {
    throw "Claude Code /loop 要求 2.1.72 或更高版本，当前为 $ClaudeVersion。"
}

$ProgramFilesX86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
$ChromeCandidates = @()
if ($env:CHROME_PATH) {
    $ChromeCandidates += $env:CHROME_PATH
}
foreach ($BrowserRoot in @($env:LOCALAPPDATA, $env:ProgramFiles, $ProgramFilesX86)) {
    if (-not $BrowserRoot) { continue }
    $ChromeCandidates += Join-Path $BrowserRoot "Google\Chrome\Application\chrome.exe"
    $ChromeCandidates += Join-Path $BrowserRoot "Microsoft\Edge\Application\msedge.exe"
}
$ChromeCandidates = @($ChromeCandidates | Where-Object { Test-Path $_ } | Select-Object -Unique)

if ($ChromeCandidates.Count -eq 0) {
    throw "没有找到 Chrome 或 Edge。请安装浏览器，或把 CHROME_PATH 设置为浏览器 exe 的完整路径。"
}

Push-Location $CliRoot
try {
    & npm ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci 失败。" }

    & npm test
    if ($LASTEXITCODE -ne 0) { throw "boss-cli 构建或测试失败。" }

    & npm link
    if ($LASTEXITCODE -ne 0) { throw "npm link 失败。" }
}
finally {
    Pop-Location
}

$StateRoot = if ($env:BOSS_ZHAOPIN_STATE_DIR) {
    $env:BOSS_ZHAOPIN_STATE_DIR
} else {
    Join-Path $env:USERPROFILE ".codex\state\boss-zhaopin"
}

New-Item -ItemType Directory -Path $StateRoot -Force | Out-Null
$CurrentIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
& icacls $StateRoot /inheritance:r /grant:r "${CurrentIdentity}:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "无法收紧状态目录 ACL：$StateRoot"
}

& py -3 (Join-Path $SkillRoot "scripts\test_runtime_store.py")
if ($LASTEXITCODE -ne 0) { throw "runtime_store 测试失败。" }

& py -3 (Join-Path $SkillRoot "scripts\test_skill_contract.py")
if ($LASTEXITCODE -ne 0) { throw "skill contract 测试失败。" }

& boss help | Out-Null
if ($LASTEXITCODE -ne 0) { throw "boss 命令验证失败。" }

Write-Host "Windows 环境准备完成。" -ForegroundColor Green
Write-Host "Claude Code 版本：$ClaudeVersion"
Write-Host "下一步："
Write-Host "  1. 在当前用户下运行 boss login 并完成 Boss 登录。"
Write-Host "  2. 运行 boss list --unread 验证登录。"
Write-Host "  3. 回到仓库根目录运行 claude。"
Write-Host "  4. 在 Claude Code 中输入 /loop 1m。"
Write-Host "本地状态目录：$StateRoot"
