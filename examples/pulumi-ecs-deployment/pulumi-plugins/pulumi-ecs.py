#!/usr/bin/env python3
"""
ECS Cluster Deployment Script (Python version)
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
    print("🚀 Starting ECS cluster deployment...")
    
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
    
    # Deploy the ECS cluster
    print("⚡ Deploying ECS cluster...")
    auto_approve = "--yes" if len(sys.argv) > 1 and sys.argv[1] == "--yes" else ""
    
    try:
        run_command(f"pulumi up {auto_approve}")
        print("✅ ECS cluster deployment completed successfully!")
        print("")
        print("📊 Cluster Information:")
        
        # Get outputs
        cluster_name = run_command("pulumi stack output cluster_name", check=False)
        service_name = run_command("pulumi stack output service_name", check=False)
        load_balancer_url = run_command("pulumi stack output load_balancer_url", check=False)
        service_status_cmd = run_command("pulumi stack output service_status_command", check=False)
        task_logs_cmd = run_command("pulumi stack output task_logs_command", check=False)
        scale_service_cmd = run_command("pulumi stack output scale_service_command", check=False)
        
        if cluster_name:
            print(f"Cluster Name: {cluster_name}")
        if service_name:
            print(f"Service Name: {service_name}")
        if load_balancer_url:
            print(f"Load Balancer URL: {load_balancer_url}")
        
        print("")
        print("🌐 Test your application:")
        if load_balancer_url:
            print(f"curl {load_balancer_url}")
        
        print("")
        print("📋 Service status:")
        if service_status_cmd:
            print(service_status_cmd)
        
        print("")
        print("📝 View logs:")
        if task_logs_cmd:
            print(task_logs_cmd)
        
        print("")
        print("📈 Scale service:")
        if scale_service_cmd:
            print(scale_service_cmd)
        
        print("")
        print("🗑️  To destroy cluster:")
        print("pulumi-ecs-down")
        
    except Exception as e:
        print(f"❌ ECS cluster deployment failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()