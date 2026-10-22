# venv Auto-Healing Implementation

## Problem
When Homebrew upgrades Python (e.g., 3.14.8 → 3.15.0), the venv becomes incompatible because:
- Old venv symlinks to old Python version
- Site-packages are compiled for old version
- Script breaks until venv is manually recreated

Users with sleep-mode laptops could go days without noticing the break.

## Solution: Two-Layer Monitoring

### Layer 1: Startup Check
- **When**: Every time RTO process starts (boot, manual restart, crash recovery)
- **How**: Wrapper script invokes venv Python → implicit check
- **Result**: Catches Python upgrades at next process start

### Layer 2: Periodic Health Check  
- **When**: Every 6 hours, regardless of sleep/wake state
- **How**: Separate LaunchAgent runs `venv_health_check.py`
- **Result**: Catches Python upgrades within 6 hours of occurrence

## Implementation Details

### Files Created

#### 1. `venv_health_check.py`
Location: `/Users/lip-kent.ng/Documents/Datadog Projects/RTO-Tracker/venv_health_check.py`

Functionality:
- Compares system Python version vs venv Python version
- If mismatch detected:
  - Removes old venv
  - Creates new venv with current Python
  - Reinstalls all requirements
  - Logs all steps to `~/.rto_tracker/venv_health_check.log`
- If versions match: Logs "healthy" and exits

Log output: `~/.rto_tracker/venv_health_check.log`

#### 2. LaunchAgent for Health Check
Location: `~/Library/LaunchAgents/com.datadog.rto-tracker-healthcheck.plist`

Configuration:
- **Label**: `com.datadog.rto-tracker-healthcheck`
- **Interval**: 21,600 seconds (6 hours)
- **Runs**: Every 6 hours automatically, even in sleep mode
- **Output**: 
  - stdout: `~/.rto_tracker/healthcheck_stdout.log`
  - stderr: `~/.rto_tracker/healthcheck_stderr.log`

## How It Works

```
Timeline of Python Upgrade Recovery:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User upgrades Python (e.g., via brew upgrade)
  ↓
Within 6 hours → Health check runs
  ├─ Detects version mismatch
  ├─ Rebuilds venv (~10 seconds)
  └─ Logs "rebuild complete"
  ↓
Next RTO process start (manual or crash recovery)
  └─ Uses freshly rebuilt venv ✅
  
OR

At next system boot
  ├─ LaunchAgent loads RTO process
  ├─ Startup wrapper runs
  └─ Uses freshly rebuilt venv ✅
```

## Testing & Verification

### Verify Health Check Works
```bash
# Run manually to test
/Users/lip-kent.ng/Documents/Datadog\ Projects/RTO-Tracker/.venv/bin/python3 \
  /Users/lip-kent.ng/Documents/Datadog\ Projects/RTO-Tracker/venv_health_check.py

# Check results
cat ~/.rto_tracker/venv_health_check.log | tail -20
```

### Verify LaunchAgent Is Loaded
```bash
launchctl list | grep healthcheck
# Should show: "-   0   com.datadog.rto-tracker-healthcheck"
```

### Monitor Health Checks
```bash
# Watch for health check runs
tail -f ~/.rto_tracker/venv_health_check.log
```

## Recovery Behavior

| Event | Behavior |
|-------|----------|
| Python upgrades | Health check detects within 6 hours, rebuilds silently |
| venv broken | Next process restart uses fresh venv |
| Process crashed | LaunchAgent auto-restarts with healthy venv |
| Mac sleeps | Health check still runs on schedule |
| Manual restart | Process uses current healthy venv |

## Maintenance

- **No manual intervention needed** — fully automated
- **Logs all actions** — check `venv_health_check.log` to verify it's working
- **Safe** — only rebuilds if version mismatch detected
- **Fast** — rebuild takes ~8-10 seconds

## Future: If Python Pinning Needed

If you want to prevent Python upgrades entirely:
```bash
# Pin Python version with pyenv (optional)
echo "3.15.0" > /Users/lip-kent.ng/Documents/Datadog\ Projects/RTO-Tracker/.python-version
# Install pyenv: brew install pyenv
```

This prevents Homebrew upgrades from affecting your project, but the auto-heal works regardless.
