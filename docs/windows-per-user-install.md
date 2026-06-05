# Completing SVP Installation for a Windows User (No-Pip)

This guide covers what to do **after cloning the SVP repo** to finish activating
the `svp` command for a specific Windows user account, using the no-pip
profile-function method (`setup_svp_user.ps1`). It is the recommended path when
`pip install` is broken on the machine.

The worked example uses the user **`cfusco`**; substitute your own username and
paths as needed.

> See also: README → **"Native Windows (PowerShell + Conda)"**
> (sections *Option 2 — No-pip fallback* and *Multi-user machines*).

## Prerequisites (verify, don't reinstall)

These are machine-wide and are almost certainly already present. The setup
script checks each one and aborts with a clear message if any is missing, so you
do not need to verify them by hand first.

- `python` ≥ 3.11 with `pytest` importable — e.g. the shared
  `C:\ProgramData\miniconda3` base interpreter.
- `claude`, `git`, and `conda` on the user's PATH.

Machine-wide tools are reused across users; only the `svp` command binding and
the per-user `~/.claude` plugin cache are account-specific.

## Checklist

Run all of these **while logged into the target account** (`cfusco`), in
**Windows PowerShell 5.1**.

```powershell
# 1. Clone into the user's OWN profile (Windows locks cross-user access,
#    so cfusco cannot read another user's C:\Users\<other>\... copy)
New-Item -ItemType Directory -Force C:\Users\cfusco\Documents\projects | Out-Null
git clone https://github.com/NeuroBAU/svp.git C:\Users\cfusco\Documents\projects\svp

# 2. Run the no-pip activator from inside the clone
cd C:\Users\cfusco\Documents\projects\svp
.\setup_svp_user.ps1            # add -RegisterMarketplace to also register the marketplace

# 3. Open a NEW PowerShell window (so $PROFILE + SVP_PLUGIN_ROOT load)

# 4. Verify the command resolves
Get-Command svp                 # -> CommandType: Function

# 5. First real run — this is what activates the plugin for this user
cd C:\Users\cfusco\Documents\workspaces   # any directory OUTSIDE the repo
svp new test-project
```

## What each step does / why it matters

1. **Own copy of the repo** — each user needs a clone in their own profile (or a
   shared, world-readable path). Pointing at another user's copy fails on
   permissions.
2. **`setup_svp_user.ps1`** — auto-detects the repo root, validates the shared
   toolchain, sets the `SVP_PLUGIN_ROOT` environment variable, and appends a
   `svp` function to the user's PowerShell `$PROFILE`. This function replaces the
   pip-generated `svp.exe`:
   ```powershell
   function svp { & "C:\ProgramData\miniconda3\python.exe" "<repo>\svp\scripts\svp_launcher.py" @args }
   ```
3. **New window** — the profile function and environment variable only load in
   shells started *after* the script runs.
4. **`Get-Command svp`** — confirms the name resolves to the function (rather
   than "command not found").
5. **`svp new`** — the launcher's `ensure_project_settings()` writes the
   project-scoped `.claude/settings.json` here. This is the moment SVP's
   `/svp:*` commands and agents become available — not before.

## Gotchas

- **Run as the target user**, not via `runas` from another account — `$PROFILE`
  resolves per-user, so it must be that user's own interactive session.
- **Windows PowerShell 5.1 vs PowerShell 7** have different `$PROFILE` files. Run
  the setup in the same host you will use for `svp` (the reference setup uses
  5.1 / `powershell.exe`).
- If the user's `claude` has never loaded the SVP marketplace, `/svp:*` commands
  appear only **after** the first `svp new` (step 5). This is expected.
