#!/usr/bin/env python3
"""
EKS Cluster Destruction Script (Python version)
"""

import subprocess
import sys
import os

def run_command(cmd, check=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, 
                              capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {cmd}")
        print(f"Error: {e.stderr}")
        if check:
            sys.exit(1)
        return None

def main():
    print("🗑️  Starting EKS cluster destruction...")
    
    # Check if Pulumi project exists
    if not os.path.exists("Pulumi.yaml"):
        print("❌ No Pulumi project found in current directory")
        sys.exit(1)
    
    # Set AWS region if not set
    aws_region = os.environ.get("AWS_REGION", "ap-southeast-1")
    os.environ["AWS_REGION"] = aws_region
    print(f"🌍 Using AWS region: {aws_region}")
    
    # Show current stack info
    print("📊 Current EKS cluster info:")
    cluster_name = run_command("pulumi stack output cluster_name", check=False)
    cluster_endpoint = run_command("pulumi stack output cluster_endpoint", check=False)
    
    if cluster_name:
        print(f"Cluster Name: {cluster_name}")
    else:
        print("No cluster name found")
        
    if cluster_endpoint:
        print(f"Cluster Endpoint: {cluster_endpoint}")
    else:
        print("No cluster endpoint found")
    
    print("")
    print("⚠️  WARNING: This will destroy the EKS cluster and all associated resources!")
    print("This action cannot be undone.")
    
    # Destroy the EKS cluster
    print("💥 Destroying EKS cluster...")
    auto_approve = "--yes" if len(sys.argv) > 1 and sys.argv[1] == "--yes" else ""
    
    try:
        run_command(f"pulumi destroy {auto_approve}")
        print("✅ EKS cluster destroyed successfully!")
        print("")
        print("🧹 Cleanup completed. All resources have been removed.")
        print("")
        print("💡 Note: You may want to clean up any remaining:")
        print("   - kubectl contexts")
        print("   - AWS Load Balancers (if any were created by services)")
        print("   - EBS volumes (if any persistent volumes were created)")
        
    except Exception as e:
        print(f"❌ EKS cluster destruction failed: {e}")
        print("Please check the error messages above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()