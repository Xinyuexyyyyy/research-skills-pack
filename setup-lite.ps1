#Requires -Version 5.1
<#
.SYNOPSIS
  轻量一键装：只给 Claude Code + CC Switch，外加一小撮零依赖 skill。
  适合「先跑起来」——不装 Node / Codex / OpenCove / Python 依赖。

.DESCRIPTION
  远程一行（PowerShell，新机推荐）：
    irm https://raw.githubusercontent.com/Xinyuexyyyyy/research-skills-pack/main/setup-lite.ps1 | iex

  或下载后本地跑（被执行策略拦住时）：
    powershell -ExecutionPolicy Bypass -File .\setup-lite.ps1

  做三件事，每步独立容错，某步失败不中断其余：
   1. 装 Claude Code —— 官方 install.ps1，自带运行时，不依赖 Node
   2. 装 CC Switch   —— winget farion1231.CC-Switch，管理供应商 / 中转
   3. 装 5 个零依赖 skill 到 ~/.claude/skills/（Claude Code 从这里读）
      白名单：task-analyze / task-decompose / closeout / idea-to-research / research
      全是纯 prompt 或仅用 Python 标准库，无第三方依赖。

  只负责“装”，不碰账号登录。装完手动运行 claude 登录、打开 CC Switch 配供应商。

.PARAMETER SkipClaude   跳过 Claude Code
.PARAMETER SkipSwitch   跳过 CC Switch
.PARAMETER SkipSkills   跳过 skills
.PARAMETER CheckOnly    只自检当前装了啥，不安装

.NOTES
  要求 Windows 10/11 x64、自带 winget（CC Switch 需要）。
  组件官方安装方式（截至 2026-07）：
   - Claude Code : irm https://claude.ai/install.ps1 | iex（自带运行时，不依赖 Node）
   - CC Switch   : winget farion1231.CC-Switch
#>
param(
  [switch]$SkipClaude,
  [switch]$SkipSwitch,
  [switch]$SkipSkills,
  [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'

# 装哪几个 skill：零依赖白名单
$script:SkillWhitelist = @(
  'task-analyze',
  'task-decompose',
  'closeout',
  'idea-to-research',
  'research'
)

# 安装结果汇总（最后统一打印）
$script:Results = [System.Collections.Generic.List[object]]::new()
function Add-Result($Name, $Status, $Detail) {
  $script:Results.Add([pscustomobject]@{ 组件 = $Name; 结果 = $Status; 说明 = $Detail })
}

function Write-Step($n, $total, $msg) {
  Write-Host ""
  Write-Host "[$n/$total] $msg" -ForegroundColor Cyan
}

# 刷新当前会话 PATH（installer 写的是系统 PATH，当前进程看不到）
function Update-SessionPath {
  $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
  $user    = [Environment]::GetEnvironmentVariable('Path', 'User')
  $env:Path = ($machine, $user, "$env:USERPROFILE\.local\bin", "$env:APPDATA\npm", "$env:LOCALAPPDATA\Microsoft\WindowsApps") -join ';'
}

function Test-CommandExists($name) {
  Update-SessionPath
  $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

# 网络操作通用重试：$Action 返回 $true=成功。最多 $Max 次，间隔递增。
function Invoke-WithRetry($Action, $Label, $Max = 3) {
  for ($i = 1; $i -le $Max; $i++) {
    try {
      if (& $Action) { return $true }
    } catch {
      Write-Host "    [$Label] 第 $i 次出错：$($_.Exception.Message)" -ForegroundColor DarkYellow
    }
    if ($i -lt $Max) {
      $wait = 5 * [math]::Pow(2, $i - 1)
      Write-Host "    [$Label] 第 $i/$Max 次未成功，$wait 秒后重试 ..." -ForegroundColor DarkYellow
      Start-Sleep -Seconds $wait
    }
  }
  return $false
}

function Test-Winget {
  if (Test-CommandExists 'winget') { return $true }
  Write-Host "  未检测到 winget（应用安装程序）。请从 Microsoft Store 安装 '应用安装程序' 后重试。" -ForegroundColor Yellow
  return $false
}

# 自举 winget：CC Switch 依赖它。没有就从微软官方 appx 装 App Installer。
# 每步 try/catch，失败只降级不中断；装完把 WindowsApps 补进当前会话 PATH。
function Install-Winget {
  if (Test-CommandExists 'winget') { return $true }
  Write-Host "  未检测到 winget，尝试自举安装 App Installer ..." -ForegroundColor Yellow

  # 尝试 1：重新注册可能已存在但未注册的 App Installer（无需联网）
  try {
    Get-AppxPackage Microsoft.DesktopAppInstaller -ErrorAction SilentlyContinue | ForEach-Object {
      Add-AppxPackage -DisableDevelopmentMode -Register "$($_.InstallLocation)\AppXManifest.xml" -ErrorAction Stop
    }
    if (Test-CommandExists 'winget') { return $true }
  } catch {}

  # 尝试 2：联网下载 App Installer msixbundle + 依赖并安装
  return (Invoke-WithRetry -Label 'winget' -Action {
    $tmp = Join-Path $env:TEMP ("winget-" + [System.IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null
    try {
      $vclibs = Join-Path $tmp 'vclibs.appx'
      Invoke-WebRequest 'https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx' -OutFile $vclibs -UseBasicParsing -TimeoutSec 120
      Add-AppxPackage -Path $vclibs -ErrorAction Stop
    } catch {}
    $rel = Invoke-RestMethod 'https://api.github.com/repos/microsoft/winget-cli/releases/latest' -Headers @{ 'User-Agent' = 'setup-lite' } -TimeoutSec 120
    $bundleUrl = ($rel.assets | Where-Object { $_.name -like '*.msixbundle' } | Select-Object -First 1).browser_download_url
    $depUrl    = ($rel.assets | Where-Object { $_.name -like '*Dependencies.zip' } | Select-Object -First 1).browser_download_url
    if ($depUrl) {
      $depZip = Join-Path $tmp 'deps.zip'
      Invoke-WebRequest $depUrl -OutFile $depZip -UseBasicParsing -TimeoutSec 180
      $depDir = Join-Path $tmp 'deps'
      Expand-Archive $depZip -DestinationPath $depDir -Force
      Get-ChildItem $depDir -Recurse -Filter '*x64*.appx' | ForEach-Object {
        try { Add-AppxPackage -Path $_.FullName -ErrorAction Stop } catch {}
      }
    }
    if (-not $bundleUrl) { throw 'winget-cli release 里没找到 msixbundle' }
    $bundle = Join-Path $tmp 'appinstaller.msixbundle'
    Invoke-WebRequest $bundleUrl -OutFile $bundle -UseBasicParsing -TimeoutSec 300
    Add-AppxPackage -Path $bundle -ErrorAction Stop
    Update-SessionPath
    Test-CommandExists 'winget'
  })
}

# ===== 1. Claude Code =====
function Install-ClaudeCode {
  if (Test-CommandExists 'claude') {
    Add-Result 'Claude Code' '已装' (claude --version)
    return
  }
  Write-Host "  运行官方安装脚本 (claude.ai/install.ps1) ..."
  $ok = Invoke-WithRetry -Label 'Claude Code' -Action {
    Invoke-RestMethod -Uri 'https://claude.ai/install.ps1' -TimeoutSec 60 | Invoke-Expression
    Update-SessionPath
    Test-CommandExists 'claude'
  }
  if ($ok) {
    Add-Result 'Claude Code' '成功' (claude --version)
  } elseif (Test-Path "$env:USERPROFILE\.local\bin\claude.exe") {
    Add-Result 'Claude Code' '需重开终端' '已安装，PATH 未刷新'
  } else {
    Add-Result 'Claude Code' '失败' '下载/安装多次失败；可手动 irm https://claude.ai/install.ps1 | iex'
  }
}

# ===== 2. CC Switch（winget）=====
function Install-CCSwitch {
  $id = 'farion1231.CC-Switch'
  if (-not (Install-Winget)) { Add-Result 'CC Switch' '跳过' 'winget 不可用（自举失败，见提示）'; return }
  Write-Host "  winget 安装 CC Switch ($id) ..."
  try {
    winget install -e --id $id --accept-source-agreements --accept-package-agreements --silent 2>&1 | Out-Null
    $rc = $LASTEXITCODE
  } catch {
    Add-Result 'CC Switch' '失败' "winget 无法启动（$($_.Exception.Message)）；可手动 winget install -e --id $id"
    return
  }
  if ($rc -eq 0 -or $rc -eq -1978335189) {
    # -1978335189 = 已安装最新版
    Add-Result 'CC Switch' '成功' $id
  } else {
    Add-Result 'CC Switch' '失败' "winget 退出码 $rc"
  }
}

# ===== 3. skills（只装白名单到 ~/.claude/skills/）=====
function Get-Tarball($url, $label) {
  $tmp = Join-Path $env:TEMP ("rsp-" + [System.IO.Path]::GetRandomFileName())
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  $tgz = Join-Path $tmp 'src.tar.gz'
  Write-Host "  下载 $label ..." -ForegroundColor Cyan
  Invoke-WebRequest -Uri $url -OutFile $tgz -TimeoutSec 120 -UseBasicParsing
  tar -xzf $tgz -C $tmp
  return (Get-ChildItem $tmp -Directory | Select-Object -First 1).FullName
}

function Install-Skills {
  $globalSkills = Join-Path $env:USERPROFILE '.claude\skills'
  if (-not (Test-Path $globalSkills)) {
    New-Item -ItemType Directory -Path $globalSkills -Force | Out-Null
  }
  $ok = Invoke-WithRetry -Label 'skills' -Action {
    $script:__rspRoot = Get-Tarball 'https://codeload.github.com/Xinyuexyyyyy/research-skills-pack/tar.gz/refs/heads/main' 'research-skills-pack'
    return $true
  }
  if (-not $ok) {
    Add-Result 'skills' '失败' '下载 tarball 多次失败'
    return
  }
  $skillSrc = Join-Path $script:__rspRoot 'skills'
  $installed = @()
  $missing = @()
  foreach ($name in $script:SkillWhitelist) {
    $src = Join-Path $skillSrc $name
    if (-not (Test-Path $src)) { $missing += $name; continue }
    $dst = Join-Path $globalSkills $name
    if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
    Copy-Item $src $dst -Recurse -Force
    $installed += $name
  }
  $detail = "$($installed.Count) 个 → $globalSkills"
  if ($missing.Count -gt 0) { $detail += "；缺 $($missing -join ',')" }
  Add-Result 'skills' $(if ($installed.Count -gt 0) { '成功' } else { '失败' }) $detail
}

# ===== CheckOnly：只报现状 =====
function Invoke-CheckOnly {
  Write-Host "======== 只自检，不安装 ========" -ForegroundColor Cyan
  # Claude
  if (Test-CommandExists 'claude') {
    Add-Result 'Claude Code' '已装' (claude --version)
  } else {
    Add-Result 'Claude Code' '未装' 'irm https://claude.ai/install.ps1 | iex'
  }
  # CC Switch
  $ccInstalled = $false
  if (Test-CommandExists 'winget') {
    try {
      $out = winget list --id farion1231.CC-Switch 2>&1 | Out-String
      if ($out -match 'CC-Switch') { $ccInstalled = $true }
    } catch {}
  }
  Add-Result 'CC Switch' $(if ($ccInstalled) { '已装' } else { '未装' }) 'winget farion1231.CC-Switch'
  # skills
  $globalSkills = Join-Path $env:USERPROFILE '.claude\skills'
  $have = @()
  foreach ($name in $script:SkillWhitelist) {
    if (Test-Path (Join-Path $globalSkills $name)) { $have += $name }
  }
  Add-Result 'skills' "$($have.Count)/$($script:SkillWhitelist.Count) 已装" $globalSkills
}

# ============ 主流程 ============
Write-Host "============================================================"
Write-Host "  轻量装：Claude Code + CC Switch + 5 个零依赖 skill"
Write-Host "============================================================"

if ($CheckOnly) {
  Invoke-CheckOnly
} else {
  $steps = @()
  if (-not $SkipClaude) { $steps += 'claude' }
  if (-not $SkipSwitch) { $steps += 'switch' }
  if (-not $SkipSkills) { $steps += 'skills' }
  $total = $steps.Count
  $i = 0

  if (-not $SkipClaude) { $i++; Write-Step $i $total '安装 Claude Code'; Install-ClaudeCode }
  if (-not $SkipSwitch) { $i++; Write-Step $i $total '安装 CC Switch';  Install-CCSwitch }
  if (-not $SkipSkills) { $i++; Write-Step $i $total '安装 skills';     Install-Skills }
}

# ============ 汇总 ============
Write-Host ""
Write-Host "===== 结果 =====" -ForegroundColor Cyan
$script:Results | Format-Table -AutoSize | Out-String | Write-Host

if (-not $CheckOnly) {
  Write-Host "下一步（手动，脚本不碰登录）：" -ForegroundColor Cyan
  Write-Host "  1. 重开一个 PowerShell（让 PATH 生效）"
  Write-Host "  2. 运行  claude   → 浏览器登录"
  Write-Host "  3. 打开 CC Switch → 配置供应商 / 中转"
  Write-Host "  4. 在任意目录开 Claude Code，输入 /  就能看到装好的 skill"
}
