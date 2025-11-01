#!/usr/bin/env python3
"""
Pulumi CLI Plugin: ec2
Deploys EC2 infrastructure and SSHs into the server
"""
import subprocess
import sys
import json
import os
import time

def run_command(cmd, capture_output=False):
    """Run a shell command"""
    if capture_output:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    else:
        return subprocess.run(cmd, shell=True).returncode

def main():
    print("🚀 Starting Pulumi EC2 deployment and SSH connection...")
    
    # Use the current working directory (where user runs the command)
    project_dir = os.getcwd()
    
    # Verify we're in a Pulumi project
    if not os.path.exists(os.path.join(project_dir, 'Pulumi.yaml')):
        print("❌ Error: Not in a Pulumi project directory!")
        print("Please run this command from your Pulumi project root.")
        sys.exit(1)
    
    print(f"📁 Working directory: {project_dir}")
    
    # Run pulumi up
    print("\n📦 Running pulumi up...")
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        exit_code = run_command("pulumi up --yes")
    else:
        exit_code = run_command("pulumi up")
    
    if exit_code != 0:
        print("❌ Pulumi deployment failed!")
        sys.exit(1)
    
    print("\n✅ Deployment complete! Fetching outputs...")
    
    # Get stack outputs (without secrets first)
    stdout, stderr, exit_code = run_command("pulumi stack output --json", capture_output=True)
    if exit_code != 0:
        print(f"❌ Failed to get stack outputs: {stderr}")
        sys.exit(1)
    
    try:
        outputs = json.loads(stdout)
    except json.JSONDecodeError:
        print("❌ Failed to parse stack outputs")
        sys.exit(1)
    
    # Extract public IP and instance ID
    public_ip = outputs.get('instance_public_ip')
    instance_id = outputs.get('instance_id')
    
    if not public_ip:
        print("❌ Could not retrieve instance public IP")
        sys.exit(1)
    
    # Create .ssh directory if it doesn't exist
    ssh_dir = os.path.join(project_dir, '.ssh')
    os.makedirs(ssh_dir, exist_ok=True)
    
    # Get private key with --show-secrets and save to file
    key_path = os.path.join(ssh_dir, 'my-ec2-key.pem')
    print("\n🔑 Saving private key...")
    
    # Capture the key output
    stdout, stderr, exit_code = run_command("pulumi stack output --show-secrets private_key_pem", capture_output=True)
    if exit_code != 0:
        print(f"❌ Failed to get private key: {stderr}")
        sys.exit(1)
    
    # Write key to file
    with open(key_path, 'w') as f:
        f.write(stdout)
    
    # Set proper permissions on the key file
    os.chmod(key_path, 0o600)
    print(f"✅ Private key saved to: {key_path}")
    
    print(f"\n🌐 Instance Public IP: {public_ip}")
    
    # Check and start instance if it's stopped
    print("\n🔍 Checking instance state...")
    instance_state = "unknown"
    stdout, stderr, exit_code = run_command(f"aws ec2 describe-instances --instance-ids {instance_id} --query 'Reservations[0].Instances[0].State.Name' --output text", capture_output=True)
    
    if exit_code == 0:
        instance_state = stdout.strip()
        print(f"Instance state: {instance_state}")
        
        if instance_state == "stopped":
            print("🚀 Starting instance...")
            run_command(f"aws ec2 start-instances --instance-ids {instance_id}")
            print("⏳ Waiting for instance to be running...")
            run_command(f"aws ec2 wait instance-running --instance-ids {instance_id}")
            print("✅ Instance is now running!")
            
            # Get new public IP after starting (IP changes after stop/start)
            print("🔄 Fetching new public IP...")
            stdout, stderr, exit_code = run_command(f"aws ec2 describe-instances --instance-ids {instance_id} --query 'Reservations[0].Instances[0].PublicIpAddress' --output text", capture_output=True)
            if exit_code == 0 and stdout.strip():
                public_ip = stdout.strip()
                print(f"🌐 New Public IP: {public_ip}")
        elif instance_state == "pending":
            print("⏳ Instance is pending, waiting for it to be running...")
            run_command(f"aws ec2 wait instance-running --instance-ids {instance_id}")
            print("✅ Instance is now running!")
        elif instance_state == "running":
            print("✅ Instance is already running!")
    
    
    # Wait a moment for SSH service to be ready
    print("\n⏳ Waiting for SSH service to be ready...")
    time.sleep(5)
    
    # SSH into the instance
    ssh_command = f'ssh -i {key_path} -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ec2-user@{public_ip}'
    print(f"\n🔌 Connecting to instance...")
    print(f"Command: {ssh_command}\n")
    
    os.system(ssh_command)

if __name__ == "__main__":
    main()
