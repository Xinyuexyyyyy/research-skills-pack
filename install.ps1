#Requires -Version 5.1
<#
.SYNOPSIS
  一键接入：从公开 GitHub tarball 装 research-skills-pack 的 24 个 skill +
  初始化 LiveWithOpenCove 工作区骨架。零认证、零 git、走网络。

.DESCRIPTION
  在目标工作区目录里跑：
    irm https://raw.githubusercontent.com/Xinyuexyyyyy/research-skills-pack/main/install.ps1 | iex

  做两件事：
   1. 下载 research-skills-pack，把 skills/* 同时装进：
        - 当前工作区的 skills/    （Codex 从这里读）
        - ~/.claude/skills/        （Claude Code 从这里读）
      两个工具读的位置不同，所以两边都装，谁都不漏。
   2. 下载 LiveWithOpenCove，在当前目录铺工作区骨架
      （.claude/memory 6文件 + MEMORY.md + CLAUDE.md + AGENTS.md），
      但【不】复制模板里的 skills/（避免它的占位 README 盖掉上面装好的真 skill）。
#>
$ErrorActionPreference = 'Stop'
$here = (Get-Location).Path

function Get-Tarball($url, $label) {
  $tmp = Join-Path $env:TEMP ("rsp-" + [System.IO.Path]::GetRandomFileName())
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  $tgz = Join-Path $tmp 'src.tar.gz'
  Write-Host "  下载 $label ..." -ForegroundColor Cyan
  Invoke-WebRequest -Uri $url -OutFile $tgz -TimeoutSec 120 -UseBasicParsing
  tar -xzf $tgz -C $tmp
  return (Get-ChildItem $tmp -Directory | Select-Object -First 1).FullName
}

function Install-Skills($srcDir, $destDir) {
  if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
  $c = 0
  Get-ChildItem $srcDir -Directory | ForEach-Object {
    $t = Join-Path $destDir $_.Name
    if (Test-Path $t) { Remove-Item $t -Recurse -Force }
    Copy-Item $_.FullName $t -Recurse -Force
    $c++
  }
  $layout = Join-Path $srcDir 'workspace-layout.md'
  if (Test-Path $layout) { Copy-Item $layout (Join-Path $destDir 'workspace-layout.md') -Force }
  return $c
}

function Install-PptDeps {
  # 装 ppt-master 的 Python 依赖（从公开仓库 hugohe3/ppt-master 拉 requirements）。
  # 只装 Python 依赖；pandoc 是可选项（仅转 .doc/.tex 等小众格式才需要），不在此装。
  # 任何失败都只警告、不中断整体安装。
  $py = $null
  foreach ($cand in @('python','python3','py')) {
    if (Get-Command $cand -ErrorAction SilentlyContinue) { $py = $cand; break }
  }
  if (-not $py) {
    Write-Host "  ⚠ 未检测到 Python，跳过 ppt-master 依赖。装 Python 3.10+ 后重跑即可。" -ForegroundColor Yellow
    return $false
  }
  $req = Join-Path $env:TEMP ("ppt-req-" + [System.IO.Path]::GetRandomFileName() + ".txt")
  try {
    # 直接拉嵌套那份（自包含、列了所有真实包，避免根目录转发的相对路径断裂）
    Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/hugohe3/ppt-master/main/skills/ppt-master/requirements.txt' -OutFile $req -TimeoutSec 60 -UseBasicParsing
    Write-Host "  用 $py 装 ppt-master 依赖（python-pptx / Pillow / PyMuPDF 等）..." -ForegroundColor Cyan
    & $py -m pip install -r $req --quiet --disable-pip-version-check 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
      Write-Host "  ✓ ppt-master Python 依赖已装" -ForegroundColor Green
      return $true
    } else {
      Write-Host "  ⚠ pip 装依赖返回非0，可手动重试：$py -m pip install -r <ppt-master>/requirements.txt" -ForegroundColor Yellow
      return $false
    }
  } catch {
    Write-Host ("  ⚠ 拉/装 ppt-master 依赖失败：" + $_.Exception.Message) -ForegroundColor Yellow
    return $false
  } finally {
    if (Test-Path $req) { Remove-Item $req -Force -ErrorAction SilentlyContinue }
  }
}

Write-Host "========================================================"
Write-Host "  research-skills-pack 一键接入（公开 tarball，零认证）"
Write-Host "========================================================"

# ===== 第 1 件：装 skills（工作区 + 全局，双份）=====
Write-Host ""
Write-Host "[1/2] 安装 skills" -ForegroundColor Cyan
$rspRoot = Get-Tarball 'https://codeload.github.com/Xinyuexyyyyy/research-skills-pack/tar.gz/refs/heads/main' 'research-skills-pack'
$skillSrc = Join-Path $rspRoot 'skills'

# 1a. 装进【当前工作区的 skills/】—— Codex 从这里读
$wsSkills = Join-Path $here 'skills'
$nWs = Install-Skills $skillSrc $wsSkills
Write-Host "  ✓ 工作区 skills/：$nWs 个（Codex 读这里）" -ForegroundColor Green

# 1b. 装进【~/.claude/skills/】—— Claude Code 从这里读
$globalSkills = Join-Path $env:USERPROFILE '.claude\skills'
$nG = Install-Skills $skillSrc $globalSkills
Write-Host "  ✓ 全局 ~/.claude/skills/：$nG 个（Claude Code 读这里）" -ForegroundColor Green

# ===== 第 2 件：铺工作区骨架（跳过模板的 skills/，不盖真 skill）=====
Write-Host ""
Write-Host "[2/2] 铺工作区骨架（.claude/memory + AGENTS.md + CLAUDE.md）" -ForegroundColor Cyan
$lwoRoot = Get-Tarball 'https://codeload.github.com/Xinyuexyyyyy/LiveWithOpenCove/tar.gz/refs/heads/main' 'LiveWithOpenCove'
$tmpl = Join-Path $lwoRoot 'examples\researcher-workspace'
if (-not (Test-Path $tmpl)) { $tmpl = Join-Path $lwoRoot 'examples/researcher-workspace' }

if (-not (Test-Path $tmpl)) {
  Write-Host "  ⚠ 没找到骨架模板，跳过（skills 已装好）" -ForegroundColor Yellow
} else {
  $made = 0; $skipped = 0
  Get-ChildItem $tmpl -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($tmpl.Length).TrimStart('\','/')
    if ($rel -like 'skills*') { return }   # 跳过模板 skills/，别让占位 README 盖掉真 skill
    $dst = Join-Path $here $rel
    if (Test-Path $dst) { $skipped++; return }
    $dstDir = Split-Path $dst -Parent
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
    Copy-Item $_.FullName $dst -Force
    $made++
  }
  Write-Host "  ✓ 骨架：新建 $made 个文件，跳过 $skipped 个已存在" -ForegroundColor Green
}

# ===== 第 3 件：装 ppt-master Python 依赖（可选能力，失败不阻断）=====
Write-Host ""
Write-Host "[3/3] 安装 ppt-master Python 依赖" -ForegroundColor Cyan
$pptOk = Install-PptDeps

# ===== 收尾 =====
Write-Host ""
Write-Host "===== 完成 =====" -ForegroundColor Cyan
Write-Host "  • 工作区 skills/        → $nWs 个（Codex）"
Write-Host "  • 全局 ~/.claude/skills → $nG 个（Claude Code）"
Write-Host "  • 工作区骨架            → .claude/memory 6文件 + MEMORY.md + CLAUDE.md + AGENTS.md"
Write-Host ("  • ppt-master 依赖       → " + $(if ($pptOk) { '已装' } else { '未装（见上方提示）' }))
Write-Host ""
Write-Host "下一步：" -ForegroundColor Cyan
Write-Host "  1. 编辑 .claude/memory/workspace-brief.md，写明这个工作区是干什么的"
Write-Host "  2. 在 Claude Code 或 Codex 里打开当前目录，两边都能读到 skills 和记忆"
