# ✅ Pulumi Command Fix - RESOLVED

## Issue
```
❌ Pulumi revert failed for i-03fd43cd135f6135d
error: unknown flag: --force
```

## Root Cause
Pulumi CLI does not support `--force` flag. The correct flags are:
- `--yes` - Auto-approve updates without confirmation
- `--skip-preview` - Skip the preview step and apply directly

## Fix Applied

### Files Modified:

1. **revert_utils.py** (Line 60)
   ```python
   # BEFORE:
   ["pulumi", "up", "--force", "--yes"]
   
   # AFTER:
   ["pulumi", "up", "--yes", "--skip-preview"]
   ```

2. **dashboard.py** (Line 537)
   ```python
   # BEFORE:
   st.info("📦 Running: `pulumi up --force` to restore baseline")
   
   # AFTER:
   st.info("📦 Running: `pulumi up --yes --skip-preview` to restore baseline")
   ```

3. **BOTO3_REVERT_CAPABILITIES.md** (Line 33)
   ```python
   # BEFORE:
   pulumi up --force  # Revert to baseline state
   
   # AFTER:
   pulumi up --yes --skip-preview  # Revert to baseline state
   ```

4. **HYBRID_APPROACH_GUIDE.md** (Lines 52, 380)
   ```
   # BEFORE:
   - **Method**: `pulumi up --force`
   
   # AFTER:
   - **Method**: `pulumi up --yes --skip-preview`
   ```

5. **ARCHITECTURE_DIAGRAM.md** (Lines 54, 96)
   ```
   # BEFORE:
   subprocess.run(["pulumi", "up", "--force", "--yes"])
   
   # AFTER:
   subprocess.run(["pulumi", "up", "--yes", "--skip-preview"])
   ```

## Verification

```bash
$ python test_pulumi_fix.py

🧪 Testing Pulumi command fix...

Status: error
Message: ❌ Pulumi revert failed for i-test-123

Error details:
error: no Pulumi.yaml project file found (searching upwards from ...)

✅ --force error is FIXED!
```

**Result:** No more `--force` flag error! ✅

The new error about missing `Pulumi.yaml` is **expected** and correct behavior when Pulumi project is not initialized.

## Pulumi Flags Explanation

| Flag | Purpose |
|------|---------|
| `--yes` | Auto-approve the update without prompting for confirmation |
| `--skip-preview` | Skip the preview phase and apply changes directly |
| `--stack <name>` | Select which stack to operate on (optional) |
| `--config <key>=<value>` | Set configuration values (optional) |

**Note:** There is NO `--force` flag in Pulumi CLI.

## Next Steps to Use Pulumi Revert

1. **Initialize Pulumi Project:**
   ```bash
   pulumi new aws-python
   # or
   pulumi new aws-typescript
   ```

2. **Configure Stack:**
   ```bash
   pulumi stack init baseline-stack
   pulumi config set aws:region us-east-1
   ```

3. **Define Infrastructure:**
   Create resources in your Pulumi program that match baseline_state.json

4. **Deploy Baseline:**
   ```bash
   pulumi up --yes
   ```

5. **Use Dashboard:**
   Now the "🔄 Revert with Pulumi" button will work correctly!

## Status

✅ **FIXED and VERIFIED**

All documentation updated. Ready for Pulumi integration once project is initialized.
