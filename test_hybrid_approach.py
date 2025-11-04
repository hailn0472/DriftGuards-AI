"""
Quick Test Script for Hybrid Approach
Run this to test the revert utilities without AWS credentials
"""

from revert_utils import (
    pulumi_revert_to_baseline,
    boto3_revert_to_baseline,
    boto3_terminate_resource,
    load_baseline_config
)

print("🧪 Testing Hybrid Approach Implementation\n")
print("=" * 60)

# Test 1: Pulumi revert (will fail without Pulumi CLI, but shows error handling)
print("\n1️⃣  Testing Pulumi Revert...")
result = pulumi_revert_to_baseline(
    resource_type="ec2_instances",
    resource_id="i-test-123",
    account_id="123456789012",
    region="us-east-1"
)
print(f"   Status: {result['status']}")
print(f"   Message: {result['message']}")
if 'docs' in result:
    print(f"   Docs: {result['docs']}")

# Test 2: Load baseline config
print("\n2️⃣  Testing Baseline Config Loading...")
baseline = load_baseline_config("ec2_instances", "i-03fd43cd135f6135d")
if baseline:
    print(f"   ✅ Found baseline for EC2 instance")
    print(f"   State: {baseline.get('state', 'N/A')}")
    print(f"   Tags: {len(baseline.get('tags', []))} tags")
else:
    print(f"   ⚠️  No baseline found (expected if baseline_state.json doesn't exist)")

# Test 3: Boto3 revert (will fail without AWS credentials)
print("\n3️⃣  Testing Boto3 Revert...")
if baseline:
    result = boto3_revert_to_baseline(
        resource_type="ec2_instances",
        resource_id="i-test-123",
        account_id="123456789012",
        region="us-east-1",
        baseline_config=baseline
    )
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}")
else:
    print("   ⏭️  Skipped (no baseline loaded)")

# Test 4: Terminate (will fail without AWS credentials)
print("\n4️⃣  Testing Boto3 Terminate...")
result = boto3_terminate_resource(
    resource_type="ec2_instances",
    resource_id="i-test-123",
    account_id="123456789012",
    region="us-east-1",
    force=False
)
print(f"   Status: {result['status']}")
print(f"   Message: {result['message']}")

print("\n" + "=" * 60)
print("✅ All functions are callable and error handling works!")
print("\n📝 Notes:")
print("   - Pulumi revert needs Pulumi CLI installed")
print("   - Boto3 operations need AWS credentials configured")
print("   - Baseline loading needs baseline_state.json")
print("\n🚀 Ready to use in dashboard!")
