#Requires -Version 5.1
<#
.SYNOPSIS
  在这台 Win 上装 OpenSSH 服务端（绕开慢/不吃代理的 Windows Update，直接从 GitHub 下官方 MSI）。
  装完起服务、放行防火墙、并授权指定公钥，让远端可免密 SSH 进来。

.DESCRIPTION
  必须在【管理员 PowerShell】里运行：
    powershell -ExecutionPolicy Bypass -File .\install-openssh.ps1
  有系统代理会自动用；也可手动：-Proxy http://127.0.0.1:7890

.PARAMETER Proxy   代理地址，不传则自动读 Windows 系统代理
.PARAMETER PubKey  要授权的 SSH 公钥（默认已内置 Mac 的 ed25519 公钥）
.NOTES
  ys112 是管理员账号 → 授权写进 %ProgramData%\ssh\administrators_authorized_keys（并锁 ACL）。
#>
param(
  [string]$Proxy,
  [string]$PubKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIA2fPF7a+yJXgt9W+ioLb7wkC9qcMBJYEdc9m67Pj+iv sure@local'
)
$ErrorActionPreference = 'Stop'

# ---- 自动提权：非管理员则弹 UAC 重开管理员窗口再跑 ----
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
  Write-Host "未以管理员运行，正在请求提权（会弹 UAC，点『是』）..." -ForegroundColor Yellow
  $argList = @('-NoExit','-ExecutionPolicy','Bypass','-File', "`"$PSCommandPath`"")
  if ($Proxy) { $argList += @('-Proxy', $Proxy) }
  Start-Process powershell -Verb RunAs -ArgumentList $argList
  return
}

# ---- 代理（GitHub 下载关键）----
if (-not $Proxy) {
  try {
    $reg = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
    if ($reg.ProxyEnable -eq 1 -and $reg.ProxyServer) {
      $Proxy = ($reg.ProxyServer -split ';' | Where-Object { $_ -notmatch '=' -or $_ -match 'http=' } | Select-Object -First 1) -replace '^http=',''
    }
  } catch {}
}
if ($Proxy) {
  if ($Proxy -notmatch '^\w+://') { $Proxy = "http://$Proxy" }
  $env:HTTP_PROXY = $Proxy; $env:HTTPS_PROXY = $Proxy
  try { [System.Net.WebRequest]::DefaultWebProxy = New-Object System.Net.WebProxy($Proxy, $true) } catch {}
  Write-Host "已启用代理：$Proxy" -ForegroundColor Green
} else {
  Write-Host "未检测到系统代理，将直连 GitHub（慢的话请开系统代理或传 -Proxy）。" -ForegroundColor Yellow
}

function Invoke-WithRetry($Action, $Label, $Max = 3) {
  for ($i = 1; $i -le $Max; $i++) {
    try { if (& $Action) { return $true } }
    catch { Write-Host "  [$Label] 第 $i 次出错：$($_.Exception.Message)" -ForegroundColor DarkYellow }
    if ($i -lt $Max) { Start-Sleep -Seconds (5 * $i) }
  }
  return $false
}

# ---- 1. 若已装则跳过下载 ----
$sshd = Get-Service sshd -ErrorAction SilentlyContinue
if (-not $sshd) {
  Write-Host "`n[1/4] 下载并安装 OpenSSH 官方 MSI ..." -ForegroundColor Cyan
  $ok = Invoke-WithRetry -Label 'OpenSSH下载' -Action {
    $rel = Invoke-RestMethod 'https://api.github.com/repos/PowerShell/Win32-OpenSSH/releases/latest' -Headers @{ 'User-Agent'='setup' } -TimeoutSec 120
    $url = ($rel.assets | Where-Object { $_.name -like 'OpenSSH-Win64-v*.msi' } | Select-Object -First 1).browser_download_url
    if (-not $url) { throw '未找到 OpenSSH-Win64 MSI' }
    $msi = Join-Path $env:TEMP 'openssh-win64.msi'
    Invoke-WebRequest -Uri $url -OutFile $msi -UseBasicParsing -TimeoutSec 300
    $p = Start-Process msiexec.exe -ArgumentList "/i `"$msi`" /qn /norestart" -Wait -PassThru
    if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) { throw "msiexec 退出码 $($p.ExitCode)" }
    $null -ne (Get-Service sshd -ErrorAction SilentlyContinue)
  }
  if (-not $ok) { Write-Host "OpenSSH 安装失败，见上方报错。" -ForegroundColor Red; exit 1 }
} else {
  Write-Host "`n[1/4] 已检测到 sshd 服务，跳过安装。" -ForegroundColor Green
}

# ---- 2. 启动服务 + 开机自启 ----
Write-Host "[2/4] 启动 sshd / ssh-agent 并设为自启 ..." -ForegroundColor Cyan
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd
Get-Service ssh-agent -ErrorAction SilentlyContinue | ForEach-Object { Set-Service ssh-agent -StartupType Automatic; Start-Service ssh-agent }
# 默认 shell 设为 PowerShell（免密登录后直接进 PS）
New-Item -Path 'HKLM:\SOFTWARE\OpenSSH' -Force | Out-Null
New-ItemProperty -Path 'HKLM:\SOFTWARE\OpenSSH' -Name DefaultShell -Value "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force | Out-Null

# ---- 3. 防火墙放行 22 ----
Write-Host "[3/4] 放行防火墙 22 端口 ..." -ForegroundColor Cyan
if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
  New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
}

# ---- 4. 授权公钥（管理员账号走 administrators_authorized_keys + 锁 ACL）----
Write-Host "[4/4] 授权公钥 ..." -ForegroundColor Cyan
$authKeys = Join-Path $env:ProgramData 'ssh\administrators_authorized_keys'
$existing = if (Test-Path $authKeys) { Get-Content $authKeys -ErrorAction SilentlyContinue } else { @() }
if ($existing -notcontains $PubKey) {
  Add-Content -Path $authKeys -Value $PubKey -Encoding ascii
}
# ACL：去继承，只留 SYSTEM(S-1-5-18) 和 Administrators(S-1-5-32-544) 完全控制，否则 sshd 会忽略此文件
icacls $authKeys /inheritance:r | Out-Null
icacls $authKeys /grant '*S-1-5-18:(F)' '*S-1-5-32-544:(F)' | Out-Null
Restart-Service sshd

# ---- 汇总 ----
$svc = Get-Service sshd
Write-Host "`n===== 完成 =====" -ForegroundColor Cyan
Write-Host ("  sshd 状态 : " + $svc.Status)
Write-Host ("  监听端口 : 22（防火墙已放行）")
Write-Host ("  授权文件 : $authKeys")
Write-Host ("  本机 Tailscale IP: " + ((tailscale ip -4 2>$null) -join ' '))
Write-Host "  远端现在可用: ssh ys112@<这台的Tailscale IP>" -ForegroundColor Green
