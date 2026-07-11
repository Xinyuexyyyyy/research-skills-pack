#Requires -Version 5.1
<#
.SYNOPSIS
  一键安装 AI 编码工具链（Windows 10/11，x64）。
  安装内容：Node.js LTS、Git、Claude Code、Codex CLI、CC Switch、OpenCove、skills。

.DESCRIPTION
  只负责"装"，不碰账号登录。装完后请手动运行 claude / codex 自行登录。
  每一步独立容错：某个组件装失败不会中断其余安装，最后打印清单。

.PARAMETER SkipNode      跳过 Node.js
.PARAMETER SkipGit       跳过 Git
.PARAMETER SkipClaude    跳过 Claude Code
.PARAMETER SkipCodex     跳过 Codex CLI
.PARAMETER SkipCCSwitch  跳过 CC Switch
.PARAMETER SkipOpenCove  跳过 OpenCove（最新 nightly）
.PARAMETER SkipSkills    跳过 skills（接入 Claude Code）
.PARAMETER SkipPptDeps   跳过 ppt-master Python 依赖（python-pptx 等；pandoc 不在此装）
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
  [switch]$SkipOpenCove,
  [switch]$SkipSkills,
  [switch]$SkipPptDeps,
  [string]$Proxy,
  [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'

# ===== 代理支持（国内网络关键）=====
# 优先用 -Proxy 传入；没传就自动读 Windows 系统代理（客户端开了“系统代理”即可）。
# 让 .NET(Invoke-WebRequest/RestMethod)、环境变量(curl)、npm 全部走同一个代理。
function Set-ProxyEnv($p) {
  if (-not $p) { return }
  if ($p -notmatch '^\w+://') { $p = "http://$p" }   # 只给了 127.0.0.1:7890 就补 http://
  $env:HTTP_PROXY = $p; $env:HTTPS_PROXY = $p
  $env:http_proxy = $p; $env:https_proxy = $p
  try { [System.Net.WebRequest]::DefaultWebProxy = New-Object System.Net.WebProxy($p, $true) } catch {}
  Write-Host "  已启用代理：$p" -ForegroundColor Green
  $script:ProxyUrl = $p
}
if (-not $Proxy) {
  try {
    $reg = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
    if ($reg.ProxyEnable -eq 1 -and $reg.ProxyServer) {
      $Proxy = ($reg.ProxyServer -split ';' | Where-Object { $_ -notmatch '=' -or $_ -match 'http=' } | Select-Object -First 1) -replace '^http=',''
    }
  } catch {}
}
Set-ProxyEnv $Proxy

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
  $env:Path = ($machine, $user, "$env:USERPROFILE\.local\bin", "$env:APPDATA\npm", "$env:LOCALAPPDATA\Microsoft\WindowsApps") -join ';'
}

function Test-CommandExists($name) {
  Update-SessionPath
  $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

# 网络操作通用重试：$Action 是脚本块，返回 $true=成功 / $false=失败（或抛异常）。
# 最多 $Max 次，间隔递增（5s/10s/20s），专治不稳定网络下的偶发失败。
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
  try {
    winget install -e --id $id --accept-source-agreements --accept-package-agreements --silent 2>&1 | Out-Null
    $rc = $LASTEXITCODE
  } catch {
    Add-Result $display '失败' "winget 无法启动（$($_.Exception.Message)）；可手动 winget install -e --id $id"
    return
  }
  if ($rc -eq 0 -or $rc -eq -1978335189) {
    # -1978335189 = 已安装最新版
    Add-Result $display '成功' $id
  } else {
    Add-Result $display '失败' "winget 退出码 $rc"
  }
}

# ===== 直连下载安装辅助（不依赖 winget）=====
function Save-Download($url, $name) {
  $tmp = Join-Path $env:TEMP ("dl-" + [System.IO.Path]::GetRandomFileName())
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  $out = Join-Path $tmp $name
  Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing -TimeoutSec 600
  return $out
}
# 从 GitHub 最新 release 找匹配资产（$pattern 用 -like 通配）
function Get-GitHubAsset($repo, $pattern) {
  $rel = Invoke-RestMethod "https://api.github.com/repos/$repo/releases/latest" -Headers @{ 'User-Agent' = 'setup-windows' } -TimeoutSec 120
  ($rel.assets | Where-Object { $_.name -like $pattern } | Select-Object -First 1).browser_download_url
}
# 静默装 MSI（0=成功，3010=成功需重启）
function Install-Msi($path) {
  $p = Start-Process msiexec.exe -ArgumentList "/i `"$path`" /qn /norestart" -Wait -PassThru
  return ($p.ExitCode -eq 0 -or $p.ExitCode -eq 3010)
}

function Install-NodeDirect {
  return (Invoke-WithRetry -Label 'Node直连' -Action {
    $idx = Invoke-RestMethod 'https://nodejs.org/dist/index.json' -TimeoutSec 120
    $lts = ($idx | Where-Object { $_.lts } | Select-Object -First 1).version   # 形如 v24.18.0
    if (-not $lts) { throw '取不到 Node LTS 版本号' }
    $msi = Save-Download "https://nodejs.org/dist/$lts/node-$lts-x64.msi" "node-$lts-x64.msi"
    if (-not (Install-Msi $msi)) { throw 'msiexec 装 Node 失败' }
    Update-SessionPath
    Test-CommandExists 'node'
  })
}

function Install-Node {
  if (Test-CommandExists 'node') {
    Add-Result 'Node.js' '已装' (node -v)
    return
  }
  Write-Host "  下载官方 Node.js LTS MSI 直连安装 ..."
  if (Install-NodeDirect) { Add-Result 'Node.js' '成功' (node -v); return }
  # 兜底：若恰好有 winget 再试一把
  if (Test-CommandExists 'winget') {
    Install-ViaWinget 'OpenJS.NodeJS.LTS' 'Node.js'; Update-SessionPath
  } else {
    Add-Result 'Node.js' '失败' '直连安装失败；可手动装 https://nodejs.org/en/download'
  }
}

function Install-GitDirect {
  return (Invoke-WithRetry -Label 'Git直连' -Action {
    $url = Get-GitHubAsset 'git-for-windows/git' '*64-bit.exe'
    if (-not $url) { throw '未找到 Git for Windows 安装包' }
    $exe = Save-Download $url 'git-setup.exe'
    $p = Start-Process $exe -ArgumentList '/VERYSILENT /NORESTART /NOCANCEL /SP- /SUPPRESSMSGBOXES' -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Git 安装退出码 $($p.ExitCode)" }
    Update-SessionPath
    Test-CommandExists 'git'
  })
}

function Install-Git {
  if (Test-CommandExists 'git') {
    Add-Result 'Git' '已装' (git --version)
    return
  }
  Write-Host "  下载 Git for Windows 官方安装包直连安装 ..."
  if (Install-GitDirect) { Add-Result 'Git' '成功' (git --version); return }
  if (Test-CommandExists 'winget') {
    Install-ViaWinget 'Git.Git' 'Git'; Update-SessionPath
  } else {
    Add-Result 'Git' '失败' '直连安装失败；可手动装 https://git-scm.com/download/win'
  }
}

function Install-ClaudeCode {
  if (Test-CommandExists 'claude') {
    Add-Result 'Claude Code' '已装' (claude --version)
    return
  }
  $ok = $false
  # 途径1（国内首选，真机实测最快最稳）：npm 淘宝镜像装。需 Node（步骤1已装）。
  if (Test-CommandExists 'npm') {
    Write-Host "  途径1：npm 淘宝镜像装 @anthropic-ai/claude-code ..."
    $ok = Invoke-WithRetry -Label 'Claude Code(npm镜像)' -Max 2 -Action {
      npm install -g @anthropic-ai/claude-code --registry=https://registry.npmmirror.com 2>&1 | Out-Null
      Update-SessionPath; Test-CommandExists 'claude'
    }
  }
  # 途径2（兜底）：官方安装脚本，走代理时可用
  if (-not $ok) {
    Write-Host "  途径2：官方安装脚本 (claude.ai/install.ps1) ..." -ForegroundColor DarkYellow
    $ok = Invoke-WithRetry -Label 'Claude Code(官方)' -Max 2 -Action {
      Invoke-RestMethod -Uri 'https://claude.ai/install.ps1' -TimeoutSec 90 | Invoke-Expression
      Update-SessionPath; Test-CommandExists 'claude'
    }
  }
  if ($ok) {
    Add-Result 'Claude Code' '成功' (claude --version)
  } elseif (Test-Path "$env:USERPROFILE\.local\bin\claude.exe") {
    Add-Result 'Claude Code' '需重开终端' '已安装，PATH 未刷新'
  } else {
    Add-Result 'Claude Code' '失败' 'npm镜像+官方脚本均失败（见上方报错）；手动: npm i -g @anthropic-ai/claude-code --registry=https://registry.npmmirror.com'
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
  Write-Host "  npm 淘宝镜像安装 @openai/codex ..."
  $ok = Invoke-WithRetry -Label 'Codex(镜像)' -Action {
    npm install -g @openai/codex --registry=https://registry.npmmirror.com 2>&1 | Out-Null
    Update-SessionPath
    Test-CommandExists 'codex'
  }
  # 镜像失败再退回默认源
  if (-not $ok) {
    Write-Host "  镜像失败，改用默认源 registry.npmjs.org 重试 ..." -ForegroundColor DarkYellow
    $ok = Invoke-WithRetry -Label 'Codex(默认源)' -Max 2 -Action {
      npm install -g @openai/codex 2>&1 | Out-Null
      Update-SessionPath
      Test-CommandExists 'codex'
    }
  }
  if ($ok) {
    Add-Result 'Codex CLI' '成功' (codex --version)
  } else {
    Add-Result 'Codex CLI' '失败' '默认源与镜像均失败；可手动 npm install -g @openai/codex'
  }
}

function Install-CCSwitchDirect {
  return (Invoke-WithRetry -Label 'CCSwitch直连' -Action {
    # 匹配 x64 的 CC-Switch-vX.Y.Z-Windows.msi（arm64 是 -Windows-arm64.msi，通配不会命中）
    $url = Get-GitHubAsset 'farion1231/cc-switch' 'CC-Switch-*-Windows.msi'
    if (-not $url) { throw '未找到 CC Switch 安装包' }
    $msi = Save-Download $url 'cc-switch.msi'
    if (-not (Install-Msi $msi)) { throw 'msiexec 装 CC Switch 失败' }
    return $true
  })
}

function Install-CCSwitch {
  # CC Switch 是 GUI 应用，不进 PATH：先查注册表卸载项判断是否已装
  $installed = Get-ItemProperty @(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
  ) -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match 'CC.?Switch' } | Select-Object -First 1
  if ($installed) { Add-Result 'CC Switch' '已装' $installed.DisplayVersion; return }

  Write-Host "  下载 CC Switch 官方 MSI 直连安装 ..."
  if (Install-CCSwitchDirect) { Add-Result 'CC Switch' '成功' '官方 MSI'; return }
  if (Test-CommandExists 'winget') {
    Install-ViaWinget 'farion1231.CC-Switch' 'CC Switch'
  } else {
    Add-Result 'CC Switch' '失败' '直连安装失败；可手动装 https://github.com/farion1231/cc-switch/releases'
  }
}

# OpenCove：上游每天出 nightly 预发布，含现成 win-x64.exe。
# 这里动态抓最新 nightly 的 .exe 静默安装，不写死版本（始终最新夜间版）。
# 放在最后安装：它最重，且失败不应影响前面的 CLI 工具链。
function Install-OpenCove {
  $repo = 'DeadWaveWave/opencove'
  Write-Host "  查询 $repo 最新 nightly 版本 ..."
  try {
    $headers = @{ 'User-Agent' = 'setup-windows-ps1'; 'Accept' = 'application/vnd.github+json' }
    # 取最新一个 release（nightly 是 prerelease，列表按时间倒序，第一个即最新）
    $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/$repo/releases?per_page=1" -Headers $headers -TimeoutSec 20
    $rel = $rel | Select-Object -First 1
    if (-not $rel) { Add-Result 'OpenCove' '失败' '未取到任何 release'; return }
    $asset = $rel.assets | Where-Object { $_.name -match 'win-x64\.exe$' } | Select-Object -First 1
    if (-not $asset) { Add-Result 'OpenCove' '失败' "release $($rel.tag_name) 无 win-x64.exe 资产"; return }
  } catch {
    Add-Result 'OpenCove' '失败' "查询 release 失败：$($_.Exception.Message)"
    return
  }

  $url = $asset.browser_download_url
  $out = Join-Path $env:TEMP $asset.name
  # 国内访问 GitHub 下载常慢/断；按顺序尝试原站 + 加速镜像
  $sources = @($url, "https://ghproxy.com/$url", "https://mirror.ghproxy.com/$url")
  Write-Host "  下载 $($asset.name)（$([math]::Round($asset.size/1MB,1)) MB）..."
  $dl = $false
  foreach ($src in $sources) {
    Write-Host "    源：$src"
    $dl = Invoke-WithRetry -Label 'OpenCove下载' -Max 2 -Action {
      Invoke-WebRequest -Uri $src -OutFile $out -TimeoutSec 600 -UseBasicParsing
      (Test-Path $out) -and ((Get-Item $out).Length -gt 0)
    }
    if ($dl) { break }
  }
  if (-not $dl) {
    Add-Result 'OpenCove' '失败' "原站与镜像均下载失败（网络问题）；可手动下载 $url"
    return
  }

  # SHA256 校验（release 含 SHA256SUMS.txt）：防下出半截/损坏文件
  $sumAsset = $rel.assets | Where-Object { $_.name -eq 'SHA256SUMS.txt' } | Select-Object -First 1
  if ($sumAsset) {
    try {
      $sums = Invoke-RestMethod -Uri $sumAsset.browser_download_url -TimeoutSec 30
      # 精确匹配"以该文件名结尾"的整行，避免误匹配 .exe.blockmap 那行
      $line = ($sums -split "`n") | Where-Object { ($_ -split '\s+')[-1].Trim() -eq $asset.name } | Select-Object -First 1
      $expect = (($line -split '\s+')[0]).ToLower()
      $actual = (Get-FileHash $out -Algorithm SHA256).Hash.ToLower()
      if ($expect -and $actual -ne $expect) {
        Remove-Item $out -Force -ErrorAction SilentlyContinue
        Add-Result 'OpenCove' '失败' 'SHA256 不匹配（文件损坏），已删除；请重跑'
        return
      }
      Write-Host "  SHA256 校验通过" -ForegroundColor Green
    } catch {
      Write-Host "  SHA256 校验跳过（取校验和失败，不阻断安装）" -ForegroundColor DarkYellow
    }
  }

  Write-Host "  静默安装 $($asset.name) ..."
  try {
    # electron-builder NSIS 安装包：/S 静默
    $p = Start-Process -FilePath $out -ArgumentList '/S' -Wait -PassThru
    if ($p.ExitCode -eq 0) {
      Add-Result 'OpenCove' '成功' "$($rel.tag_name)（最新 nightly）"
    } else {
      Add-Result 'OpenCove' '需手动' "安装器退出码 $($p.ExitCode)，安装包在 $out"
    }
  } catch {
    Add-Result 'OpenCove' '失败' "启动安装器失败：$($_.Exception.Message)；包在 $out"
  }
}

# 第 7 步：装 skills —— 把 research-skills-pack 的 skill 复制进 Claude Code 的目录。
# 与 OpenCove 无关：skills 是 Claude Code 的 SKILL.md，放 ~/.claude/skills/ 即被加载。
# 离线优先：skills 就在脚本旁边的 skills/ 目录，直接复制（零网络、零认证）；
# 找不到才退回 git clone（私有仓库需凭据）。Windows 上用复制而非软链。
function Install-Skills {
  $repo = 'https://github.com/Xinyuexyyyyy/research-skills-pack.git'
  $dest = Join-Path $env:USERPROFILE '.claude\skills'
  $src  = $null

  # 1) 离线优先：脚本同目录下的 skills/
  $localSkills = Join-Path $PSScriptRoot 'skills'
  if (Test-Path $localSkills) {
    $src = $localSkills
    Write-Host "  发现脚本旁的 skills/（离线安装，无需联网）"
  } else {
    # 2) 退回：git clone 私有仓库
    if (-not (Test-CommandExists 'git')) {
      Add-Result 'Skills' '跳过' '脚本旁无 skills/ 且 git 不可用'
      return
    }
    Write-Host "  脚本旁无 skills/，尝试 git clone ..."
    $work = Join-Path $env:TEMP 'research-skills-pack'
    $ok = Invoke-WithRetry -Label 'Skills拉取' -Max 2 -Action {
      Remove-Item $work -Recurse -Force -ErrorAction SilentlyContinue
      git clone --depth 1 $repo $work 2>&1 | Out-Null
      Test-Path (Join-Path $work 'skills')
    }
    if (-not $ok) {
      Add-Result 'Skills' '失败' "脚本旁无 skills/，clone 也失败；把整个 research-skills-pack 文件夹拷到本机再跑即可离线安装"
      return
    }
    $src = Join-Path $work 'skills'
  }

  # 复制每个 skill 到 ~/.claude/skills/（覆盖同名）
  # 注意：Copy-Item 到"已存在的同名目录"会嵌套成 dest/x/x，所以先删目标再拷
  if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
  $count = 0
  Get-ChildItem $src -Directory | ForEach-Object {
    $target = Join-Path $dest $_.Name
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
    Copy-Item $_.FullName $target -Recurse -Force
    $count++
  }
  Add-Result 'Skills' '成功' "$count 个 skill 已复制到 ~/.claude/skills/"
}

function Install-PptDeps {
  # 装 ppt-master 的 Python 依赖（从公开仓库 hugohe3/ppt-master 拉 requirements）。
  # 只装 Python 依赖；pandoc 是可选项（仅转 .doc/.tex 等小众格式才需要），不在此装。
  $py = $null
  foreach ($cand in @('python','python3','py')) {
    if (Test-CommandExists $cand) { $py = $cand; break }
  }
  if (-not $py) {
    Add-Result 'PPT依赖' '跳过' '未检测到 Python，装 Python 3.10+ 后重跑 -SkipNode -SkipGit ... 仅补这步'
    return
  }
  $req = Join-Path $env:TEMP ("ppt-req-" + [System.IO.Path]::GetRandomFileName() + ".txt")
  try {
    Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/hugohe3/ppt-master/main/skills/ppt-master/requirements.txt' -OutFile $req -TimeoutSec 60 -UseBasicParsing
    & $py -m pip install -r $req --quiet --disable-pip-version-check 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
      Add-Result 'PPT依赖' '成功' "ppt-master Python 依赖已装（python-pptx/Pillow/PyMuPDF 等）"
    } else {
      Add-Result 'PPT依赖' '失败' "pip 返回非0；手动重试：$py -m pip install -r <ppt-master>/requirements.txt"
    }
  } catch {
    Add-Result 'PPT依赖' '失败' ("拉/装依赖出错：" + $_.Exception.Message)
  } finally {
    if (Test-Path $req) { Remove-Item $req -Force -ErrorAction SilentlyContinue }
  }
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
  # CC Switch 是 GUI 应用，查 winget 列表（winget 在非交互会话可能拒绝访问，优雅降级）
  try {
    $cc = winget list -e --id farion1231.CC-Switch 2>$null | Select-String 'CC-Switch'
    if ($cc) { Write-Host "  [OK]   CC Switch    已安装" -ForegroundColor Green }
    else     { Write-Host "  [缺]   CC Switch    未检测到" -ForegroundColor Yellow }
  } catch {
    Write-Host "  [?]    CC Switch    无法查询（winget 在当前会话不可用，请手动确认）" -ForegroundColor Yellow
  }
  # OpenCove：查注册表卸载项（electron-builder NSIS 安装会写入），不依赖 winget
  try {
    $keys = @(
      'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
      'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
      'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
    )
    $oc = Get-ItemProperty $keys -ErrorAction SilentlyContinue |
          Where-Object { $_.DisplayName -match 'OpenCove' } | Select-Object -First 1
    if ($oc) { Write-Host ("  [OK]   OpenCove     " + $oc.DisplayVersion) -ForegroundColor Green }
    else     { Write-Host "  [缺]   OpenCove     未检测到" -ForegroundColor Yellow }
  } catch {
    Write-Host "  [?]    OpenCove     无法查询" -ForegroundColor Yellow
  }
}

# 自举 winget：Node/Git/CC Switch 都靠它。没有就从微软官方 appx 装 App Installer。
# 每步 try/catch，失败只降级不中断；装完把 WindowsApps 补进当前会话 PATH。
function Install-Winget {
  if (Test-CommandExists 'winget') { Add-Result 'winget' '已装' (winget --version); return }
  Write-Host "  未检测到 winget，尝试自举安装 App Installer ..." -ForegroundColor Yellow

  # 尝试 1：重新注册可能已存在但未注册的 App Installer（最省事，无需联网）
  try {
    Get-AppxPackage Microsoft.DesktopAppInstaller -ErrorAction SilentlyContinue | ForEach-Object {
      Add-AppxPackage -DisableDevelopmentMode -Register "$($_.InstallLocation)\AppXManifest.xml" -ErrorAction Stop
    }
    if (Test-CommandExists 'winget') { Add-Result 'winget' '成功' '重新注册已有 App Installer'; return }
  } catch {}

  # 尝试 2：联网下载 App Installer msixbundle + 依赖并安装
  $ok = Invoke-WithRetry -Label 'winget' -Action {
    $tmp = Join-Path $env:TEMP ("winget-" + [System.IO.Path]::GetRandomFileName())
    New-Item -ItemType Directory -Path $tmp -Force | Out-Null

    # 依赖：VCLibs（Add 失败通常是已装同版本，忽略）
    try {
      $vclibs = Join-Path $tmp 'vclibs.appx'
      Invoke-WebRequest 'https://aka.ms/Microsoft.VCLibs.x64.14.00.Desktop.appx' -OutFile $vclibs -UseBasicParsing -TimeoutSec 120
      Add-AppxPackage -Path $vclibs -ErrorAction Stop
    } catch {}

    # 主体 + Xaml 依赖：从 winget-cli 最新 release 取（含 Dependencies.zip）
    $rel = Invoke-RestMethod 'https://api.github.com/repos/microsoft/winget-cli/releases/latest' -Headers @{ 'User-Agent' = 'setup-windows' } -TimeoutSec 120
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
  }

  if ($ok) {
    Add-Result 'winget' '成功' (winget --version)
  } else {
    Add-Result 'winget' '失败' '自举失败；可从 Microsoft Store 装“应用安装程序”，或手动 Add-AppxPackage https://aka.ms/getwinget 后重跑本脚本'
  }
}

# ===== 主流程 =====
Write-Host "========================================================"
Write-Host "  AI 编码 CLI 工具链安装器 (Windows)"
Write-Host "  装: Node.js / Git / Claude Code / Codex CLI / CC Switch / OpenCove / skills"
Write-Host "  说明: 只负责安装，不处理账号登录；OpenCove 最后装（最新 nightly），再接 skills"
Write-Host "========================================================"

if ($CheckOnly) { Show-Doctor; return }

if (-not [Environment]::Is64BitOperatingSystem) {
  Write-Host "警告: 检测到非 64 位系统，部分组件可能不支持。" -ForegroundColor Yellow
}

$total = 8
if (-not $SkipNode)     { Write-Step 1 $total '安装 Node.js LTS';   Install-Node }     else { Add-Result 'Node.js' '跳过' '--SkipNode' }
if (-not $SkipGit)      { Write-Step 2 $total '安装 Git';            Install-Git }      else { Add-Result 'Git' '跳过' '--SkipGit' }
if (-not $SkipClaude)   { Write-Step 3 $total '安装 Claude Code';    Install-ClaudeCode } else { Add-Result 'Claude Code' '跳过' '--SkipClaude' }
if (-not $SkipCodex)    { Write-Step 4 $total '安装 Codex CLI';      Install-Codex }    else { Add-Result 'Codex CLI' '跳过' '--SkipCodex' }
if (-not $SkipCCSwitch) { Write-Step 5 $total '安装 CC Switch';      Install-CCSwitch } else { Add-Result 'CC Switch' '跳过' '--SkipCCSwitch' }
# OpenCove 放最后的应用安装：它最重（下载+安装），且失败不应影响前面的 CLI 工具链
if (-not $SkipOpenCove) { Write-Step 6 $total '安装 OpenCove (最新 nightly)'; Install-OpenCove } else { Add-Result 'OpenCove' '跳过' '--SkipOpenCove' }
# 第 7 步：装 skills（接入 Claude Code），放在所有软件之后
if (-not $SkipSkills)   { Write-Step 7 $total '安装 skills (接入 Claude Code)'; Install-Skills } else { Add-Result 'Skills' '跳过' '--SkipSkills' }
if (-not $SkipPptDeps)  { Write-Step 8 $total '安装 ppt-master Python 依赖'; Install-PptDeps } else { Add-Result 'PPT依赖' '跳过' '--SkipPptDeps' }

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

