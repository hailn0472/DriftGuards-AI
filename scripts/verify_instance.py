"""Verify if instance exists and check all regions."""

from dotenv import load_dotenv
load_dotenv()  # Load .env file

import boto3
from botocore.exceptions import ClientError


def check_instance_in_region(instance_id: str, region: str):
    """Check if instance exists in specific region."""
    try:
        ec2 = boto3.client("ec2", region_name=region)
        response = ec2.describe_instances(InstanceIds=[instance_id])
        
        if response["Reservations"]:
            instance = response["Reservations"][0]["Instances"][0]
            print(f"✅ Found in {region}:")
            print(f"   State: {instance['State']['Name']}")
            print(f"   Type: {instance['InstanceType']}")
            print(f"   VPC: {instance.get('VpcId', 'N/A')}")
            print(f"   Private IP: {instance.get('PrivateIpAddress', 'N/A')}")
            print(f"   Public IP: {instance.get('PublicIpAddress', 'N/A')}")
            return True
    except ClientError as e:
        if "InvalidInstanceID.NotFound" in str(e):
            return False
        print(f"❌ Error in {region}: {e}")
    return False


def check_all_regions(instance_id: str):
    """Check instance in all AWS regions."""
    print(f"🔍 Checking instance {instance_id} in all regions...\n")
    
    ec2 = boto3.client("ec2", region_name="ap-southeast-1")
    regions = [region["RegionName"] for region in ec2.describe_regions()["Regions"]]
    
    found = False
    for region in regions:
        if check_instance_in_region(instance_id, region):
            found = True
            break
    
    if not found:
        print(f"\n❌ Instance {instance_id} NOT FOUND in any region")
        print("   Possible reasons:")
        print("   - Instance was recently terminated")
        print("   - Instance ID is incorrect")
        print("   - AWS credentials don't have access")


def verify_current_account():
    """Verify current AWS account."""
    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        print(f"🔑 Current AWS Account:")
        print(f"   Account ID: {identity['Account']}")
        print(f"   User ARN: {identity['Arn']}")
        print()
    except Exception as e:
        print(f"❌ Cannot verify AWS account: {e}\n")


if __name__ == "__main__":
    verify_current_account()
    
    # Check the new instance
    instance_id = "i-07735a53d7e3968a3"
    check_all_regions(instance_id)
    
    print("\n" + "="*60)
    
    # Also check the old terminated instance
    old_instance = "i-0c186a4d4a8b6d08b"
    print(f"\n🔍 Checking old instance {old_instance}...")
    check_instance_in_region(old_instance, "ap-southeast-1")
