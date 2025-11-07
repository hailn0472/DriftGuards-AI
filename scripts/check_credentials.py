"""Check where boto3 is getting credentials from."""

from dotenv import load_dotenv
load_dotenv()  # Load .env before checking

import os
import boto3
from botocore.credentials import (
    EnvProvider,
    SharedCredentialProvider,
    ConfigProvider,
    AssumeRoleProvider,
)


def check_credentials():
    """Check AWS credentials and their source."""
    print("🔍 Checking AWS Credentials Chain\n")
    print("=" * 60)
    
    # Check environment variables
    print("\n1️⃣ Environment Variables:")
    env_vars = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            masked = value[:8] + "..." if len(value) > 8 else value
            print(f"   ✅ {var}: {masked}")
        else:
            print(f"   ❌ {var}: Not set")
    
    # Check .env file
    print("\n2️⃣ .env File:")
    env_file = "d:\\github\\DriftGuards-AI\\.env"
    if os.path.exists(env_file):
        print(f"   ✅ .env file exists")
        # Note: .env is not automatically loaded by boto3
        print("   ⚠️  WARNING: boto3 does NOT automatically load .env files!")
        print("   💡 You need python-dotenv to load .env")
    else:
        print(f"   ❌ .env file not found")
    
    # Check AWS CLI credentials
    print("\n3️⃣ AWS CLI Credentials (~/.aws/credentials):")
    credentials_file = os.path.expanduser("~/.aws/credentials")
    if os.path.exists(credentials_file):
        print(f"   ✅ Credentials file exists: {credentials_file}")
        try:
            with open(credentials_file, 'r') as f:
                content = f.read()
                profiles = [line.strip('[]') for line in content.split('\n') if line.startswith('[')]
                print(f"   📋 Profiles found: {', '.join(profiles)}")
        except:
            print("   ⚠️  Could not read credentials file")
    else:
        print(f"   ❌ Credentials file not found")
    
    # Check AWS config
    print("\n4️⃣ AWS Config (~/.aws/config):")
    config_file = os.path.expanduser("~/.aws/config")
    if os.path.exists(config_file):
        print(f"   ✅ Config file exists: {config_file}")
    else:
        print(f"   ❌ Config file not found")
    
    # Get actual credentials being used
    print("\n5️⃣ Current Active Credentials:")
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        
        if credentials:
            # Get identity
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            
            print(f"   ✅ Account ID: {identity['Account']}")
            print(f"   ✅ User ARN: {identity['Arn']}")
            print(f"   ✅ User ID: {identity['UserId']}")
            
            # Try to determine source
            if os.getenv('AWS_ACCESS_KEY_ID'):
                print(f"\n   📍 Source: Environment Variables")
            elif os.getenv('AWS_PROFILE'):
                print(f"\n   📍 Source: AWS Profile (AWS_PROFILE={os.getenv('AWS_PROFILE')})")
            else:
                print(f"\n   📍 Source: Likely from ~/.aws/credentials (default profile)")
        else:
            print("   ❌ No credentials found!")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Solution
    print("\n" + "=" * 60)
    print("\n💡 SOLUTION:\n")
    print("To use .env file with boto3, you need to:")
    print("1. Install python-dotenv:")
    print("   pip install python-dotenv")
    print("\n2. Load .env at the start of your script:")
    print("   from dotenv import load_dotenv")
    print("   load_dotenv()")
    print("\nOR")
    print("\n3. Set environment variables manually:")
    print("   export AWS_ACCESS_KEY_ID=your_key")
    print("   export AWS_SECRET_ACCESS_KEY=your_secret")
    print("\nOR")
    print("\n4. Use AWS CLI to configure:")
    print("   aws configure")
    print("   # Enter credentials for account 961639320333")


if __name__ == "__main__":
    check_credentials()
