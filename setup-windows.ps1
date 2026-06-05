#Requires -Version 5.1
<#
.SYNOPSIS
  一键安装 AI 编码 CLI 工具链（Windows 10/11，x64）。
  安装内容：Node.js LTS、Git、Claude Code、Codex CLI、CC Switch。

.DESCRIPTION
  只负责"装"，不碰账号登录。装完后请手动运行 claude / codex 自行登录。
  每一步独立容错：某个组件装失败不会中断其余安装，最后打印清单。

.PARAMETER SkipNode      跳过 Node.js
.PARAMETER SkipGit       跳过 Git
.PARAMETER SkipClaude    跳过 Claude Code
.PARAMETER SkipCodex     跳过 Codex CLI
.PARAMETER SkipCCSwitch  跳过 CC Switch
.PARAMETER CheckOnly     只自检，不安装

.EXAMPLE
  # 在 PowerShell 里运行（如被执行策略拦住，用下面这行）：
  powershell -ExecutionPolicy Bypass -File .\setup-windows.ps1

.NOTES
  组件官方安装方式（截至 2026-06）：
   - Node.js LTS : winget OpenJS.NodeJS.LTS
   - Git         : winget Git.Git
   - Claude Code : irm https://claude.ai/install.ps1 | iex（自带运行时，不依赖 Node）
   - Codex CLI   : npm install -g @openai/codex（需 Node 18+）
   - CC Switch   : winget farion1231.CC-Switch
#>
[CmdletBinding()]
param(
  [switch]$SkipNode,
  [switch]$SkipGit,
  [switch]$SkipClaude,
  [switch]$SkipCodex,
  [switch]$SkipCCSwitch,
  [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'

# 安装结果汇总（最后统一打印）
$script:Results = [System.Collections.Generic.List[object]]::new()
function Add-Result($Name, $Status, $Detail) {
  $script:Results.Add([pscustomobject]@{ 组件 = $Name; 结果 = $Status; 说明 = $Detail })
}

function Write-Step($n, $total, $msg) {
  Write-Host ""
  Write-Host "[$n/$total] $msg" -ForegroundColor Cyan
}

# 刷新当前会话 PATH（winget/installer 写的是系统 PATH，当前进程看不到）
function Update-SessionPath {
  $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
  $user    = [Environment]::GetEnvironmentVariable('Path', 'User')
  $env:Path = ($machine, $user, "$env:USERPROFILE\.local\bin", "$env:APPDATA\npm") -join ';'
}

function Test-CommandExists($name) {
  Update-SessionPath
  $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

# 确认 winget 可用（Win10 1809+/Win11 自带；缺失则提示）
function Test-Winget {
  if (Test-CommandExists 'winget') { return $true }
  Write-Host "  未检测到 winget（应用安装程序）。请从 Microsoft Store 安装 '应用安装程序' 后重试。" -ForegroundColor Yellow
  return $false
}

# 用 winget 装一个包，已装则跳过
function Install-ViaWinget($id, $display) {
  if (-not (Test-Winget)) { Add-Result $display '跳过' 'winget 不可用'; return }
  Write-Host "  winget 安装 $display ($id) ..."
  winget install -e --id $id --accept-source-agreements --accept-package-agreements --silent 2>&1 | Out-Null
  if ($LASTEXITCODE -eq 0 -or $LASTEXITCODE -eq -1978335189) {
    # -1978335189 = 已安装最新版
    Add-Result $display '成功' $id
  } else {
    Add-Result $display '失败' "winget 退出码 $LASTEXITCODE"
  }
}

function Install-Node {
  if (Test-CommandExists 'node') {
    Add-Result 'Node.js' '已装' (node -v)
    return
  }
  Install-ViaWinget 'OpenJS.NodeJS.LTS' 'Node.js'
  Update-SessionPath
}

function Install-Git {
  if (Test-CommandExists 'git') {
    Add-Result 'Git' '已装' (git --version)
    return
  }
  Install-ViaWinget 'Git.Git' 'Git'
  Update-SessionPath
}

function Install-ClaudeCode {
  if (Test-CommandExists 'claude') {
    Add-Result 'Claude Code' '已装' (claude --version)
    return
  }
  Write-Host "  运行官方安装脚本 (claude.ai/install.ps1) ..."
  try {
    Invoke-RestMethod -Uri 'https://claude.ai/install.ps1' | Invoke-Expression
    Update-SessionPath
    if (Test-CommandExists 'claude') {
      Add-Result 'Claude Code' '成功' (claude --version)
    } else {
      Add-Result 'Claude Code' '需重开终端' '已安装，PATH 未刷新'
    }
  } catch {
    Add-Result 'Claude Code' '失败' $_.Exception.Message
  }
}

function Install-Codex {
  if (-not (Test-CommandExists 'npm')) {
    Add-Result 'Codex CLI' '跳过' 'npm 不可用（Node 未装成功）'
    return
  }
  if (Test-CommandExists 'codex') {
    Add-Result 'Codex CLI' '已装' (codex --version)
    return
  }
  Write-Host "  npm 全局安装 @openai/codex ..."
  npm install -g @openai/codex 2>&1 | Out-Null
  Update-SessionPath
  if (Test-CommandExists 'codex') {
    Add-Result 'Codex CLI' '成功' (codex --version)
  } else {
    Add-Result 'Codex CLI' '失败' "npm 退出码 $LASTEXITCODE"
  }
}

function Install-CCSwitch {
  Install-ViaWinget 'farion1231.CC-Switch' 'CC Switch'
}

function Show-Doctor {
  Write-Host ""
  Write-Host "===== 自检：当前已装情况 =====" -ForegroundColor Cyan
  $tools = @(
    @{ cmd = 'node';   name = 'Node.js' },
    @{ cmd = 'npm';    name = 'npm' },
    @{ cmd = 'git';    name = 'Git' },
    @{ cmd = 'claude'; name = 'Claude Code' },
    @{ cmd = 'codex';  name = 'Codex CLI' }
  )
  foreach ($t in $tools) {
    if (Test-CommandExists $t.cmd) {
      $ver = & $t.cmd --version 2>$null | Select-Object -First 1
      Write-Host ("  [OK]   {0,-12} {1}" -f $t.name, $ver) -ForegroundColor Green
    } else {
      Write-Host ("  [缺]   {0,-12} 未检测到" -f $t.name) -ForegroundColor Yellow
    }
  }
  # CC Switch 是 GUI 应用，查 winget 列表
  $cc = winget list -e --id farion1231.CC-Switch 2>$null | Select-String 'CC-Switch'
  if ($cc) { Write-Host "  [OK]   CC Switch    已安装" -ForegroundColor Green }
  else     { Write-Host "  [缺]   CC Switch    未检测到" -ForegroundColor Yellow }
}

# ===== 主流程 =====
Write-Host "========================================================"
Write-Host "  AI 编码 CLI 工具链安装器 (Windows)"
Write-Host "  装: Node.js / Git / Claude Code / Codex CLI / CC Switch"
Write-Host "  说明: 只负责安装，不处理账号登录"
Write-Host "========================================================"

if ($CheckOnly) { Show-Doctor; return }

if (-not [Environment]::Is64BitOperatingSystem) {
  Write-Host "警告: 检测到非 64 位系统，部分组件可能不支持。" -ForegroundColor Yellow
}

$total = 5
if (-not $SkipNode)     { Write-Step 1 $total '安装 Node.js LTS';   Install-Node }     else { Add-Result 'Node.js' '跳过' '--SkipNode' }
if (-not $SkipGit)      { Write-Step 2 $total '安装 Git';            Install-Git }      else { Add-Result 'Git' '跳过' '--SkipGit' }
if (-not $SkipClaude)   { Write-Step 3 $total '安装 Claude Code';    Install-ClaudeCode } else { Add-Result 'Claude Code' '跳过' '--SkipClaude' }
if (-not $SkipCodex)    { Write-Step 4 $total '安装 Codex CLI';      Install-Codex }    else { Add-Result 'Codex CLI' '跳过' '--SkipCodex' }
if (-not $SkipCCSwitch) { Write-Step 5 $total '安装 CC Switch';      Install-CCSwitch } else { Add-Result 'CC Switch' '跳过' '--SkipCCSwitch' }

# ===== 结果汇总 =====
Write-Host ""
Write-Host "===== 安装结果 =====" -ForegroundColor Cyan
$script:Results | Format-Table -AutoSize

Write-Host ""
Write-Host "下一步（需你手动完成，脚本不碰账号）：" -ForegroundColor Cyan
Write-Host "  1. 关闭并重新打开 PowerShell（刷新 PATH）"
Write-Host "  2. 运行  claude   → 浏览器登录 Claude 账号"
Write-Host "  3. 运行  codex    → 登录 OpenAI 账号"
Write-Host "  4. 打开  CC Switch（开始菜单）→ 配置供应商"
Write-Host "  5. 验证：claude --version  /  codex --version"

