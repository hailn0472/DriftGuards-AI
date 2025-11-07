# Selective Field Revert - Usage Examples

## Problem
You have a drift like this:
```json
{
  "state": {
    "baseline": "running",
    "current": "stopping"
  },
  "tags": {
    "baseline": [
      {"Key": "Name", "Value": "my-ec2-instance"}
    ],
    "current": [
      {"Key": "Name", "Value": "my-ec2-instance1"}
    ]
  }
}
```

You **only** want to revert the `Name` tag, **not** the state.

## Solution: Selective Revert

### Example 1: Revert Only Name Tag

```python
from selective_revert import selective_revert, get_available_fields

# Your drift diff
drift_diff = {
    "state": {
        "baseline": "running",
        "current": "stopping"
    },
    "tags": {
        "baseline": [
            {"Key": "Name", "Value": "my-ec2-instance"}
        ],
        "current": [
            {"Key": "Name", "Value": "my-ec2-instance1"}
        ]
    }
}

# Only revert the Name tag, ignore state
result = selective_revert(
    resource_type='ec2_instances',
    resource_id='i-03fd43cd135f6135d',
    region='ap-southeast-1',
    diff=drift_diff,
    selected_fields=['tags.Name']  # ✅ Only this field
)

# Result:
# {
#     "status": "success",
#     "message": "✅ Selectively reverted EC2 i-03fd43cd135f6135d",
#     "reverted_fields": ["tags.Name"],
#     "actions": [
#         "✅ Changed tag 'Name': 'my-ec2-instance1' → 'my-ec2-instance'"
#     ]
# }
```

### Example 2: Revert Multiple Specific Tags

```python
drift_diff = {
    "tags": {
        "baseline": [
            {"Key": "Name", "Value": "prod-server"},
            {"Key": "Environment", "Value": "production"},
            {"Key": "Owner", "Value": "team-a"}
        ],
        "current": [
            {"Key": "Name", "Value": "prod-server-old"},
            {"Key": "Environment", "Value": "staging"},
            {"Key": "Owner", "Value": "team-b"}
        ]
    }
}

# Only revert Name and Environment, keep Owner as-is
result = selective_revert(
    resource_type='ec2_instances',
    resource_id='i-123456',
    region='ap-southeast-1',
    diff=drift_diff,
    selected_fields=[
        'tags.Name',         # ✅ Revert this
        'tags.Environment'   # ✅ Revert this
        # Owner not listed, so it won't be reverted
    ]
)
```

### Example 3: Revert State Only, Ignore Tags

```python
drift_diff = {
    "state": {
        "baseline": "running",
        "current": "stopped"
    },
    "tags": {
        "baseline": [{"Key": "Name", "Value": "original"}],
        "current": [{"Key": "Name", "Value": "changed"}]
    }
}

# Only revert state, keep tags as they are
result = selective_revert(
    resource_type='ec2_instances',
    resource_id='i-123456',
    region='ap-southeast-1',
    diff=drift_diff,
    selected_fields=['state']  # ✅ Only state
)
```

### Example 4: Revert Instance Type and One Tag

```python
drift_diff = {
    "state": {
        "baseline": "running",
        "current": "stopped"
    },
    "instance_type": {
        "baseline": "t2.micro",
        "current": "t2.small"
    },
    "tags": {
        "baseline": [{"Key": "Name", "Value": "web-server"}],
        "current": [{"Key": "Name", "Value": "web-server-test"}]
    }
}

# Revert type and Name tag, ignore state
result = selective_revert(
    resource_type='ec2_instances',
    resource_id='i-123456',
    region='ap-southeast-1',
    diff=drift_diff,
    selected_fields=[
        'instance_type',  # ✅ Revert this
        'tags.Name'       # ✅ Revert this
        # state not listed, so won't be reverted
    ]
)
```

### Example 5: See All Available Fields

```python
from selective_revert import get_available_fields

drift_diff = {
    "state": {"baseline": "running", "current": "stopped"},
    "instance_type": {"baseline": "t2.micro", "current": "t2.small"},
    "tags": {
        "baseline": [
            {"Key": "Name", "Value": "server1"},
            {"Key": "Environment", "Value": "prod"}
        ],
        "current": [
            {"Key": "Name", "Value": "server2"},
            {"Key": "Environment", "Value": "dev"}
        ]
    }
}

# Get all available fields
available = get_available_fields(drift_diff)
print(available)
# Output:
# ['state', 'instance_type', 'tags', 'tags.Name', 'tags.Environment']

# Now you can select which ones to revert
```

## Supported Fields by Resource Type

### EC2 Instances
- `state` - Instance state (running/stopped)
- `type` or `instance_type` - Instance type (t2.micro, etc.)
- `tags` - All tags at once
- `tags.TagName` - Specific tag (e.g., `tags.Name`, `tags.Environment`, `tags.Owner`)

### S3 Buckets
- `versioning` - Bucket versioning
- `encryption` - Server-side encryption
- `public_access_blocked` - Public access block

### RDS Instances
- `publicly_accessible` - Public accessibility
- `backup_retention_period` - Backup retention days
- `multi_az` - Multi-AZ deployment

## Dashboard Integration

### Option 1: Checkboxes for Each Field

```python
import streamlit as st
from selective_revert import selective_revert, get_available_fields

# Show drift
st.json(drift_record['diff'])

# Get available fields
available_fields = get_available_fields(drift_record['diff'])

# Let user select which fields to revert
st.subheader("Select fields to revert:")
selected = []
for field in available_fields:
    if st.checkbox(field, key=f"revert_{field}"):
        selected.append(field)

# Revert button
if st.button("🔄 Revert Selected Fields"):
    if not selected:
        st.warning("Please select at least one field")
    else:
        result = selective_revert(
            resource_type=drift_record['resource_type'],
            resource_id=drift_record['resource_id'],
            region=drift_record['region'],
            diff=drift_record['diff'],
            selected_fields=selected
        )
        
        if result['status'] == 'success':
            st.success(result['message'])
            for action in result['actions']:
                st.info(action)
        else:
            st.error(result['message'])
```

### Option 2: Multi-select Dropdown

```python
import streamlit as st
from selective_revert import selective_revert, get_available_fields

# Get available fields
available_fields = get_available_fields(drift_record['diff'])

# Multi-select
selected_fields = st.multiselect(
    "Select fields to revert:",
    options=available_fields,
    help="Choose which specific fields to revert to baseline"
)

if st.button("🔄 Revert Selected"):
    result = selective_revert(
        resource_type=drift_record['resource_type'],
        resource_id=drift_record['resource_id'],
        region=drift_record['region'],
        diff=drift_record['diff'],
        selected_fields=selected_fields
    )
    st.json(result)
```

### Option 3: Quick Actions

```python
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("🔄 Revert All"):
        selected = get_available_fields(drift_record['diff'])
        result = selective_revert(..., selected_fields=selected)

with col2:
    if st.button("🏷️ Tags Only"):
        tag_fields = [f for f in available_fields if f.startswith('tags.')]
        result = selective_revert(..., selected_fields=tag_fields)

with col3:
    if st.button("⚡ State Only"):
        result = selective_revert(..., selected_fields=['state'])

with col4:
    if st.button("🔧 Config Only"):
        config_fields = [f for f in available_fields if not f.startswith('tags') and f != 'state']
        result = selective_revert(..., selected_fields=config_fields)
```

## Benefits

✅ **No hard-coding** - Works with any drift diff structure  
✅ **Granular control** - Revert only what you need  
✅ **Safe** - Preview available fields before reverting  
✅ **Flexible** - Support for nested fields (like `tags.Name`)  
✅ **Resource-aware** - Different fields for EC2, S3, RDS, etc.
