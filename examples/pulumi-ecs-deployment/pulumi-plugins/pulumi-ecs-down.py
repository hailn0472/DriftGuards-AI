#!/usr/bin/env python3
"""
ECS Cluster Destruction Script (Python version)
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
    print("🗑️  Starting ECS cluster destruction...")
    
    # Check if Pulumi project exists
    if not os.path.exists("Pulumi.yaml"):
        print("❌ No Pulumi project found in current directory")
        sys.exit(1)
    
    # Set AWS region if not set
    aws_region = os.environ.get("AWS_REGION", "ap-southeast-1")
    os.environ["AWS_REGION"] = aws_region
    print(f"🌍 Using AWS region: {aws_region}")
    
    # Show current stack info
    print("📊 Current ECS cluster info:")
    cluster_name = run_command("pulumi stack output cluster_name", check=False)
    service_name = run_command("pulumi stack output service_name", check=False)
    load_balancer_url = run_command("pulumi stack output load_balancer_url", check=False)
    
    if cluster_name:
        print(f"Cluster Name: {cluster_name}")
    else:
        print("No cluster name found")
        
    if service_name:
        print(f"Service Name: {service_name}")
    else:
        print("No service name found")
        
    if load_balancer_url:
        print(f"Load Balancer URL: {load_balancer_url}")
    else:
        print("No load balancer URL found")
    
    print("")
    print("⚠️  WARNING: This will destroy the ECS cluster and all associated resources!")
    print("This includes:")
    print("  - ECS Cluster and Services")
    print("  - Application Load Balancer")
    print("  - VPC and Networking components")
    print("  - CloudWatch Log Groups")
    print("  - IAM Roles and Policies")
    print("")
    print("This action cannot be undone.")
    
    # Destroy the ECS cluster
    print("💥 Destroying ECS cluster...")
    auto_approve = "--yes" if len(sys.argv) > 1 and sys.argv[1] == "--yes" else ""
    
    try:
        run_command(f"pulumi destroy {auto_approve}")
        print("✅ ECS cluster destroyed successfully!")
        print("")
        print("🧹 Cleanup completed. All resources have been removed.")
        print("")
        print("💡 Note: You may want to clean up any remaining:")
        print("   - ECR repositories (if any were created manually)")
        print("   - CloudWatch alarms (if any were created outside this stack)")
        print("   - Route53 records (if any were pointing to the load balancer)")
        
    except Exception as e:
        print(f"❌ ECS cluster destruction failed: {e}")
        print("Please check the error messages above and try again.")
        sys.exit(1)

if __name__ == "__main__":
    main()