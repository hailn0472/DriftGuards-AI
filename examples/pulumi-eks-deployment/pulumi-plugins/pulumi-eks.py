#!/usr/bin/env python3
"""
EKS Cluster Deployment Script (Python version)
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
    print("🚀 Starting EKS cluster deployment...")
    
    # Initialize Pulumi stack if needed
    try:
        stacks = run_command("pulumi stack ls", check=False)
        if not stacks or "dev" not in stacks:
            print("📋 Creating Pulumi stack...")
            run_command("pulumi stack init dev")
    except:
        print("📋 Creating Pulumi stack...")
        run_command("pulumi stack init dev")
    
    # Select the dev stack
    run_command("pulumi stack select dev")
    
    # Set AWS region if not set
    aws_region = os.environ.get("AWS_REGION", "ap-southeast-1")
    os.environ["AWS_REGION"] = aws_region
    print(f"🌍 Using AWS region: {aws_region}")
    
    # Configure AWS region in Pulumi
    run_command(f"pulumi config set aws:region {aws_region}")
    
    # Deploy the EKS cluster
    print("⚡ Deploying EKS cluster...")
    auto_approve = "--yes" if len(sys.argv) > 1 and sys.argv[1] == "--yes" else ""
    
    try:
        run_command(f"pulumi up {auto_approve}")
        print("✅ EKS cluster deployment completed successfully!")
        print("")
        print("📊 Cluster Information:")
        
        # Get outputs
        cluster_name = run_command("pulumi stack output cluster_name", check=False)
        cluster_endpoint = run_command("pulumi stack output cluster_endpoint", check=False)
        cluster_version = run_command("pulumi stack output cluster_version", check=False)
        kubeconfig_cmd = run_command("pulumi stack output kubeconfig_command", check=False)
        status_cmd = run_command("pulumi stack output cluster_status_command", check=False)
        
        if cluster_name:
            print(f"Cluster Name: {cluster_name}")
        if cluster_endpoint:
            print(f"Cluster Endpoint: {cluster_endpoint}")
        if cluster_version:
            print(f"Cluster Version: {cluster_version}")
        
        print("")
        print("🔧 To configure kubectl:")
        if kubeconfig_cmd:
            print(kubeconfig_cmd)
        
        print("")
        print("🧪 To test cluster:")
        if status_cmd:
            print(status_cmd)
        
        print("")
        print("🗑️  To destroy cluster:")
        print("pulumi-eks-down")
        
    except Exception as e:
        print(f"❌ EKS cluster deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()