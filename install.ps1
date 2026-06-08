#Requires -Version 5.1
<#
.SYNOPSIS
  一键接入：从公开 GitHub tarball 装 research-skills-pack 的 24 个 skill +
  可选初始化 LiveWithOpenCove 工作区骨架。零认证、零 git、走网络。

.DESCRIPTION
  用法（在目标工作区目录里跑）：
    irm https://raw.githubusercontent.com/Xinyuexyyyyy/research-skills-pack/main/install.ps1 | iex

  做两件事：
   1. 下载 research-skills-pack tarball，把 skills/* 装进 ~/.claude/skills/
   2. 下载 LiveWithOpenCove，在【当前目录】铺工作区骨架（.claude/memory 6文件 + CLAUDE.md + AGENTS.md）
  全程公开 tarball，不需要登录、不需要 git。
#>
$ErrorActionPreference = 'Stop'

function Get-Tarball($url, $label) {
  $tmp = Join-Path $env:TEMP ("rsp-" + [System.IO.Path]::GetRandomFileName())
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  $tgz = Join-Path $tmp 'src.tar.gz'
  Write-Host "  下载 $label ..." -ForegroundColor Cyan
  Invoke-WebRequest -Uri $url -OutFile $tgz -TimeoutSec 120 -UseBasicParsing
  # Windows 10/11 自带 tar，可解 .tar.gz
  tar -xzf $tgz -C $tmp
  # GitHub tarball 解出来是 <repo>-<branch>/ 单层目录
  $inner = Get-ChildItem $tmp -Directory | Select-Object -First 1
  return $inner.FullName
}

Write-Host "========================================================"
Write-Host "  research-skills-pack 一键接入（公开 tarball，零认证）"
Write-Host "========================================================"

# ===== 第 1 件：装 skills =====
Write-Host ""
Write-Host "[1/2] 安装 skills 到 ~/.claude/skills/" -ForegroundColor Cyan
$rspUrl = 'https://codeload.github.com/Xinyuexyyyyy/research-skills-pack/tar.gz/refs/heads/main'
$rspRoot = Get-Tarball $rspUrl 'research-skills-pack'
$skillSrc = Join-Path $rspRoot 'skills'
$skillDest = Join-Path $env:USERPROFILE '.claude\skills'
if (-not (Test-Path $skillDest)) { New-Item -ItemType Directory -Path $skillDest -Force | Out-Null }
$count = 0
Get-ChildItem $skillSrc -Directory | ForEach-Object {
  $target = Join-Path $skillDest $_.Name
  if (Test-Path $target) { Remove-Item $target -Recurse -Force }
  Copy-Item $_.FullName $target -Recurse -Force
  $count++
}
# 顺带把共享的 workspace-layout.md 也带过去（init/tidy 要读）
$layout = Join-Path $skillSrc 'workspace-layout.md'
if (Test-Path $layout) { Copy-Item $layout (Join-Path $skillDest 'workspace-layout.md') -Force }
Write-Host "  ✓ 已装 $count 个 skill 到 ~/.claude/skills/" -ForegroundColor Green

# ===== 第 2 件：铺 LiveWithOpenCove 工作区骨架（在当前目录）=====
Write-Host ""
Write-Host "[2/2] 在当前目录铺工作区骨架（LiveWithOpenCove）" -ForegroundColor Cyan
$here = (Get-Location).Path
Write-Host "  目标目录：$here"

$lwoUrl = 'https://codeload.github.com/Xinyuexyyyyy/LiveWithOpenCove/tar.gz/refs/heads/main'
$lwoRoot = Get-Tarball $lwoUrl 'LiveWithOpenCove'

# 用 researcher-workspace 作为骨架模板（含 .claude/memory 6文件 + CLAUDE.md + AGENTS.md + skills/）
$tmpl = Join-Path $lwoRoot 'examples\researcher-workspace'
if (-not (Test-Path $tmpl)) { $tmpl = Join-Path $lwoRoot 'examples/researcher-workspace' }

if (-not (Test-Path $tmpl)) {
  Write-Host "  ⚠ 没找到骨架模板，跳过工作区初始化（skills 已装好）" -ForegroundColor Yellow
} else {
  # 只铺缺失的：已存在的文件一律不覆盖（保护用户已有内容）
  $made = 0; $skipped = 0
  Get-ChildItem $tmpl -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($tmpl.Length).TrimStart('\','/')
    $dst = Join-Path $here $rel
    if (Test-Path $dst) {
      $skipped++
    } else {
      $dstDir = Split-Path $dst -Parent
      if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
      Copy-Item $_.FullName $dst -Force
      $made++
    }
  }
  Write-Host "  ✓ 工作区骨架：新建 $made 个文件，跳过 $skipped 个已存在" -ForegroundColor Green
}

# ===== 收尾 =====
Write-Host ""
Write-Host "===== 完成 =====" -ForegroundColor Cyan
Write-Host "  • skills  → ~/.claude/skills/（$count 个）"
Write-Host "  • 工作区  → $here（.claude/memory 6文件 + CLAUDE.md + AGENTS.md + skills/）"
Write-Host ""
Write-Host "下一步：" -ForegroundColor Cyan
Write-Host "  1. 编辑 .claude/memory/workspace-brief.md，写明这个工作区是干什么的"
Write-Host "  2. 在 Claude Code 或 Codex 里打开当前目录开始干活"
Write-Host "  3. skills 已全局可用（~/.claude/skills/），无需软链"
