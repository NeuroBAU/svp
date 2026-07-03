<#
.SYNOPSIS
    Automated native-Windows installer for SVP (pip-based).

.DESCRIPTION
    The recommended install path for native Windows (PowerShell + Anaconda/
    Miniconda, NOT WSL2). In one step it:
      1. Validates prerequisites (Python >= 3.11, conda, git, claude).
      2. Registers THIS repo as a Claude Code marketplace
         (`claude plugin marketplace add <repo>`), unless -SkipMarketplace.
      3. Runs `pip install -e .` into the target Conda environment
         (the currently active one by default; a dedicated env with -NewEnv).
      4. Confirms `svp --help` works.

    It does NOT edit your PATH, your PowerShell profile, or
    ~/.claude/settings.json. After a Windows `pip install -e .`, `svp.exe`
    lands in the Conda environment's `Scripts\` directory, which is already
    on PATH. The launcher handles project-scoped plugin activation
    automatically on your first `svp new`.

    If `pip install` is broken on your machine (some Windows + Conda setups
    have read-only or broken entry-point script generation), use the no-pip
    fallback `setup_svp_user.ps1` instead.

.PARAMETER NewEnv
    Create and install into a dedicated Conda environment (default name
    `svp`, Python 3.11) instead of the currently active environment. After
    install, run `conda activate <EnvName>` in new shells before `svp`.

.PARAMETER EnvName
    Name of the dedicated environment created by -NewEnv. Default: `svp`.

.PARAMETER PythonVersion
    Python version for the -NewEnv environment. Default: `3.11`.

.PARAMETER SkipMarketplace
    Skip `claude plugin marketplace add`. Use if the marketplace is already
    registered for this user.

.EXAMPLE
    # Install into the currently active conda env:
    git clone https://github.com/NeuroBAU/svp.git
    cd svp
    .\install_windows.ps1

.EXAMPLE
    # Install into a dedicated env named 'svp' (Python 3.11):
    .\install_windows.ps1 -NewEnv
    conda activate svp
#>

[CmdletBinding()]
param(
    [switch]$NewEnv,
    [string]$EnvName        = 'svp',
    [string]$PythonVersion  = '3.11',
    [switch]$SkipMarketplace
)

$ErrorActionPreference = 'Stop'
function Ok   { param($m) Write-Host "    OK:   $m" -ForegroundColor Green }
function Fail { param($m) Write-Host "    FAIL: $m" -ForegroundColor Red }
function Step { param($m) Write-Host "==> $m"      -ForegroundColor Cyan }

# --- Resolve + validate the repo copy -----------------------------------
$SvpRepo = (Resolve-Path $PSScriptRoot).Path
$market  = Join-Path $SvpRepo '.claude-plugin\marketplace.json'
Step "Validating SVP repo at: $SvpRepo"
foreach ($p in @((Join-Path $SvpRepo 'pyproject.toml'),
                 (Join-Path $SvpRepo 'svp\scripts\svp_launcher.py'),
                 $market)) {
    if (Test-Path $p) { Ok (Split-Path $p -Leaf) }
    else { Fail "missing: $p"; Fail "Is this a complete SVP repo this user can read?"; exit 1 }
}

# --- Validate machine-wide prerequisites --------------------------------
Step "Validating prerequisites (conda, git, claude)"
foreach ($c in 'conda','git','claude') {
    if (Get-Command $c -ErrorAction SilentlyContinue) { Ok "$c on PATH" }
    else { Fail "$c not on PATH for this user. Install it and re-run."; exit 1 }
}

# --- Select target environment ------------------------------------------
if ($NewEnv) {
    Step "Creating dedicated Conda env '$EnvName' (Python $PythonVersion)"
    conda create -n $EnvName "python=$PythonVersion" -y
    if (-not $?) { Fail "conda create failed for env '$EnvName'"; exit 1 }
    Ok "env '$EnvName' created"
    $pipCmd = @('conda','run','-n',$EnvName,'pip')
    $svpCmd = @('conda','run','-n',$EnvName,'svp')
    $pyCmd  = @('conda','run','-n',$EnvName,'python')
} else {
    if (-not $env:CONDA_PREFIX) {
        Fail "No Conda environment is active. Activate one (conda activate <env>) or pass -NewEnv."
        exit 1
    }
    Ok "using active Conda env: $env:CONDA_PREFIX"
    $pipCmd = @('pip')
    $svpCmd = @('svp')
    $pyCmd  = @('python')
}

# --- Verify Python >= 3.11 in the target env ----------------------------
Step "Checking Python >= 3.11 in the target environment"
& $pyCmd[0] $pyCmd[1..($pyCmd.Count-1)] -c "import sys; assert sys.version_info >= (3, 11), sys.version"
if (-not $?) { Fail "target environment Python is not >= 3.11"; exit 1 }
Ok "Python >= 3.11 confirmed"

# --- 1. Register the marketplace ----------------------------------------
if (-not $SkipMarketplace) {
    Step "Registering Claude Code marketplace"
    claude plugin marketplace add $SvpRepo
    if ($?) { Ok "marketplace registered: $SvpRepo" }
    else    { Write-Host "    WARN: marketplace add returned non-zero (may already exist)." -ForegroundColor Yellow }
} else {
    Write-Host "    (skipping marketplace registration -- -SkipMarketplace)" -ForegroundColor Yellow
}

# --- 2. Editable install into the target env ----------------------------
Step "Installing SVP (pip install -e .) into the target environment"
Push-Location $SvpRepo
try {
    & $pipCmd[0] $pipCmd[1..($pipCmd.Count-1)] install -e .
    if (-not $?) {
        Fail "pip install -e . failed."
        Write-Host "    If pip entry-point generation is broken on this machine, use the" -ForegroundColor Yellow
        Write-Host "    no-pip fallback instead:  .\setup_svp_user.ps1" -ForegroundColor Yellow
        exit 1
    }
} finally {
    Pop-Location
}
Ok "pip install -e . complete"

# --- 3. Verify svp --help -----------------------------------------------
Step "Verifying 'svp --help'"
& $svpCmd[0] $svpCmd[1..($svpCmd.Count-1)] --help | Out-Null
if (-not $?) {
    Fail "'svp --help' did not succeed."
    if (-not $NewEnv) {
        Write-Host "    svp.exe should be in this env's Scripts\ dir (already on PATH). Open a new shell and retry." -ForegroundColor Yellow
    } else {
        Write-Host "    Run 'conda activate $EnvName' in a new shell, then 'svp --help'." -ForegroundColor Yellow
    }
    exit 1
}
Ok "'svp --help' works"

# --- Next steps ----------------------------------------------------------
Write-Host ""
Write-Host "===================================================================" -ForegroundColor Green
Write-Host " SVP installed for user: $env:USERNAME" -ForegroundColor Green
Write-Host "===================================================================" -ForegroundColor Green
Write-Host ""
if ($NewEnv) {
    Write-Host "Activate the environment in new shells before using svp:"
    Write-Host "    conda activate $EnvName" -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "Then, from any directory OUTSIDE this repo:"
Write-Host "    svp new my-project" -ForegroundColor Yellow
Write-Host ""
Write-Host "The launcher activates the plugin project-scoped on your first 'svp new'."
Write-Host "It does not edit PATH, your PowerShell profile, or ~/.claude/settings.json."
