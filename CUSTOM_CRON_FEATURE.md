# Custom Cron Expression Feature

## Overview
Added custom cron expression support to the CloudDrift-AI dashboard, allowing users to define flexible scan schedules beyond preset options.

## Features Implemented

### 1. Schedule Type Selection
- **Preset Schedule**: Choose from predefined intervals (15min, hourly, daily, weekly, monthly)
- **Custom Cron**: Enter custom cron expressions for maximum flexibility

### 2. Cron Expression Input
- Text input field for entering cron expressions
- Default value: `0 * * * *` (every hour)
- Helpful placeholder showing format
- Real-time validation using `croniter` library

### 3. Cron Expression Guide
Collapsible helper showing:
- Format: `minute hour day month weekday`
- Common examples:
  - `*/15 * * * *` - Every 15 minutes
  - `0 * * * *` - Every hour
  - `0 */6 * * *` - Every 6 hours
  - `0 0 * * *` - Daily at midnight
  - `0 9 * * 1` - Every Monday at 9 AM
  - `0 0 1 * *` - First day of month
  - `0 0 * * 0` - Every Sunday
- Field explanations (ranges for each field)

### 4. Real-time Validation
- Validates cron expression on input
- Shows success message if valid
- Displays error message with details if invalid
- Uses `croniter.is_valid()` for validation

### 5. Configuration Persistence
- Cron expression saved to `drift_config.json`
- Loaded automatically on dashboard startup
- Stored in session state: `st.session_state.cron_expression`
- Default constant: `DEFAULT_CRON_EXPRESSION = "0 * * * *"`

## Code Structure

### Constants
```python
DEFAULT_CRON_EXPRESSION = "0 * * * *"  # Every hour
```

### Session State Initialization
```python
if "cron_expression" not in st.session_state:
    st.session_state.cron_expression = DEFAULT_CRON_EXPRESSION
```

### UI Components
```python
# Schedule type selector
schedule_type = st.sidebar.radio(
    "Schedule Type",
    ["Preset Schedule", "Custom Cron"],
    horizontal=True
)

if schedule_type == "Custom Cron":
    # Cron expression input
    cron_expr = st.sidebar.text_input(
        "⏰ Cron Expression",
        value=st.session_state.get("cron_expression", DEFAULT_CRON_EXPRESSION),
        help="Enter cron expression (minute hour day month weekday)",
        placeholder=DEFAULT_CRON_EXPRESSION,
    )
    
    # Validation
    try:
        from croniter import croniter
        if croniter.is_valid(cron_expr):
            st.sidebar.success("✅ Valid cron expression")
        else:
            st.sidebar.error("❌ Invalid cron expression format")
    except Exception as e:
        st.sidebar.error(f"❌ Validation error: {str(e)}")
```

### Configuration Save/Load
```python
# Save
config = {
    "auto_scan_enabled": st.session_state.auto_scan_enabled,
    "scan_schedule": st.session_state.scan_schedule,
    "cron_expression": st.session_state.cron_expression,
    "notifications_enabled": st.session_state.notifications_enabled,
    "auto_remediation": st.session_state.auto_remediation,
}

# Load
st.session_state.cron_expression = config.get("cron_expression", DEFAULT_CRON_EXPRESSION)
```

## Dependencies
- `croniter`: Python library for cron expression parsing and validation
  ```bash
  pip install croniter
  ```

## Usage Examples

### Example 1: Every 30 Minutes
```
*/30 * * * *
```

### Example 2: Business Hours Only (9 AM - 5 PM, Mon-Fri)
```
0 9-17 * * 1-5
```

### Example 3: Weekly on Wednesdays at 2 PM
```
0 14 * * 3
```

### Example 4: Twice Daily (6 AM and 6 PM)
```
0 6,18 * * *
```

### Example 5: Every Quarter Hour
```
*/15 * * * *
```

## Next Steps (TODO)

### High Priority
1. **Implement Scheduler Backend**
   - Use APScheduler or similar library
   - Create background task scheduler
   - Connect cron expression to actual scan execution
   - Handle long-running scans without blocking UI

2. **Scheduler Status Display**
   - Show "Scheduler Active/Inactive" indicator
   - Display next scheduled run time
   - Show last run time and result
   - Scheduler history/logs

### Medium Priority
3. **Enhanced Validation**
   - Show next 5 run times
   - Warn about very frequent schedules (< 5 min)
   - Validate against reasonable limits
   - Suggest optimizations for complex expressions

4. **Cron Expression Builder**
   - Visual cron builder interface
   - Dropdown-based field selection
   - Preview of generated expression
   - Switch between builder and text input

### Low Priority
5. **Scheduler Management**
   - Pause/resume scheduler without clearing config
   - Manual "Run Now" button
   - Skip next scheduled run
   - View upcoming scheduled runs (next 10)

6. **Advanced Features**
   - Multiple schedules (different cron for different severity levels)
   - Time zone selection
   - Schedule templates (save/load common patterns)
   - Schedule analytics (execution history, duration, success rate)

## Testing Checklist
- [ ] Cron validation works for valid expressions
- [ ] Error messages shown for invalid expressions
- [ ] Configuration persists across dashboard restarts
- [ ] Save/Load configuration includes cron expression
- [ ] Default value loads correctly on first run
- [ ] Session state updates properly when expression changes
- [ ] Preset schedules still work correctly
- [ ] Switch between preset and custom modes
- [ ] Helper guide displays correctly
- [ ] Examples in guide are accurate

## Known Issues
- None currently

## Files Modified
1. `dashboard.py`:
   - Added `DEFAULT_CRON_EXPRESSION` constant
   - Added cron expression to session state
   - Added Custom Cron radio option
   - Added cron input field with validation
   - Added cron expression guide
   - Updated save/load configuration
   - Fixed lint issues (f-string, constant usage)

## Related Documentation
- [PULUMI_FIX.md](./PULUMI_FIX.md) - Pulumi command fixes
- [FIX_INSTANCE_NOT_FOUND.md](./FIX_INSTANCE_NOT_FOUND.md) - AWS configuration fixes
- [REGION_VS_AZ.md](./REGION_VS_AZ.md) - Region vs Availability Zone fix
- [Croniter Documentation](https://github.com/kiorky/croniter) - Cron library reference
