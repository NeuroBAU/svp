<#
.SYNOPSIS
    Per-user SVP activation WITHOUT pip (profile-function method).

.DESCRIPTION
    Makes the `svp` command work for the CURRENT Windows user by:
      1. Validating the shared toolchain (python>=3.11 + pytest, claude, git, conda).
      2. Setting the SVP_PLUGIN_ROOT user env var (so the launcher's
         _find_plugin_root() always resolves the plugin in this repo).
      3. Adding a `svp` function to the user's PowerShell profile that invokes
         svp\scripts\svp_launcher.py directly (this replaces the pip-generated
         svp.exe console-script -- no `pip install` required).
      4. Optionally registering this repo as a Claude Code marketplace.

    This does NOT modify PATH or touch ~/.claude/settings.json. The svp launcher
    handles project-scoped plugin activation automatically on the first
    `svp new` / `svp` / `svp restore`.

    Run this AS the target user (e.g. cfusco), in Windows PowerShell 5.1, from
    inside a copy of the SVP repo that THIS user can read. The repo root is
    auto-detected from the script's own location.

.PARAMETER SvpRepo
    SVP repo root. Defaults to the directory containing this script.

.PARAMETER Python
    Python interpreter the `svp` function will call. Defaults to the machine-wide
    Miniconda base (Python 3.13, shared across users, already has pytest).

.PARAMETER RegisterMarketplace
    If set, also runs `claude plugin marketplace add <repo>` for this user.

.EXAMPLE
    # As cfusco, from inside the clone:
    cd C:\Users\cfusco\Documents\projects\svp
    .\setup_svp_user.ps1

.EXAMPLE
    .\setup_svp_user.ps1 -RegisterMarketplace
#>

[CmdletBinding()]
param(
    [string]$SvpRepo = $PSScriptRoot,
    [string]$Python  = 'C:\ProgramData\miniconda3\python.exe',
    [switch]$RegisterMarketplace
)

$ErrorActionPreference = 'Stop'
function Ok   { param($m) Write-Host "    OK:   $m" -ForegroundColor Green }
function Fail { param($m) Write-Host "    FAIL: $m" -ForegroundColor Red }
function Step { param($m) Write-Host "==> $m" -ForegroundColor Cyan }

# --- Resolve paths -------------------------------------------------------
$SvpRepo    = (Resolve-Path $SvpRepo).Path
$launcher   = Join-Path $SvpRepo 'svp\scripts\svp_launcher.py'
$pluginRoot = Join-Path $SvpRepo 'svp'
$market     = Join-Path $SvpRepo '.claude-plugin\marketplace.json'

Step "Validating repo copy at: $SvpRepo"
foreach ($p in @($launcher, $pluginRoot, $market)) {
    if (Test-Path $p) { Ok (Split-Path $p -Leaf) }
    else { Fail "missing: $p"; Fail "Is this a complete SVP repo this user can read?"; exit 1 }
}

# --- Validate shared toolchain (mirrors launcher preflight) --------------
Step "Validating shared toolchain"
if (-not (Test-Path $Python)) { Fail "python not found: $Python"; exit 1 }
& $Python -c "import sys, pytest; assert sys.version_info >= (3, 11)"
if (-not $?) { Fail "$Python is not >=3.11 or pytest is not importable"; exit 1 }
Ok "$Python (>=3.11, pytest importable)"
foreach ($c in 'claude','git','conda') {
    if (Get-Command $c -ErrorAction SilentlyContinue) { Ok "$c on PATH" }
    else { Fail "$c not on PATH for this user"; exit 1 }
}

# --- 1. Persistent fallback for plugin discovery -------------------------
Step "Setting SVP_PLUGIN_ROOT (User scope)"
[Environment]::SetEnvironmentVariable('SVP_PLUGIN_ROOT', $pluginRoot, 'User')
Ok "SVP_PLUGIN_ROOT = $pluginRoot  (new shells only)"

# --- 2. Add the `svp` function to this user's profile (idempotent) -------
Step "Installing `svp` function into `$PROFILE"
$fn  = "function svp { & `"$Python`" `"$launcher`" @args }"
$dir = Split-Path $PROFILE
if (-not (Test-Path $dir))     { New-Item -ItemType Directory -Force $dir | Out-Null }
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File $PROFILE | Out-Null }
$existing = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($existing -notmatch 'function svp\b') {
    Add-Content $PROFILE "`r`n# SVP launcher (profile-function method, no pip)`r`n$fn"
    Ok "added to $PROFILE"
} else {
    Write-Host "    WARN: a `svp` function already exists in $PROFILE -- left as-is." -ForegroundColor Yellow
    Write-Host "          If it points elsewhere, edit it to:" -ForegroundColor Yellow
    Write-Host "          $fn" -ForegroundColor Yellow
}

# --- 3. Optional marketplace registration --------------------------------
if ($RegisterMarketplace) {
    Step "Registering Claude Code marketplace"
    claude plugin marketplace add $SvpRepo
    if ($?) { Ok "marketplace registered: $SvpRepo" }
    else    { Write-Host "    WARN: marketplace add returned non-zero (may already exist)." -ForegroundColor Yellow }
}

# --- Next steps ----------------------------------------------------------
Write-Host ""
Write-Host "===================================================================" -ForegroundColor Green
Write-Host " SVP activated for user: $env:USERNAME" -ForegroundColor Green
Write-Host "===================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Open a NEW PowerShell window (so the profile + env var load), then:"
Write-Host "    cd <a workspace dir outside this repo>" -ForegroundColor Yellow
Write-Host "    svp new test-project" -ForegroundColor Yellow
Write-Host ""
Write-Host "Verify resolution with:  Get-Command svp   (should say CommandType: Function)"
