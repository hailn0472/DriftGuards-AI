#!/usr/bin/env python3
"""
Pulumi CLI Plugin: ec2-down
Destroys EC2 infrastructure
"""
import subprocess
import sys
import os

def run_command(cmd):
    """Run a shell command"""
    return subprocess.run(cmd, shell=True).returncode

def main():
    print("🛑 Shutting down Pulumi EC2 infrastructure...")
    
    # Use the current working directory (where user runs the command)
    project_dir = os.getcwd()
    
    # Verify we're in a Pulumi project
    if not os.path.exists(os.path.join(project_dir, 'Pulumi.yaml')):
        print("❌ Error: Not in a Pulumi project directory!")
        print("Please run this command from your Pulumi project root.")
        sys.exit(1)
    
    print(f"📁 Working directory: {project_dir}")
    
    # Get instance ID and stop it before destroying
    print("\n🔍 Getting instance information...")
    result = subprocess.run(
        "pulumi stack output --json",
        shell=True,
        capture_output=True,
        text=True
    )
    stdout = result.stdout
    stderr = result.stderr
    exit_code = result.returncode
    
    if exit_code == 0:
        try:
            import json
            outputs = json.loads(stdout)
            instance_id = outputs.get('instance_id')
            
            if instance_id:
                print(f"Instance ID: {instance_id}")
                
                # Check instance state
                print("\n🔍 Checking instance state...")
                result = subprocess.run(
                    f"aws ec2 describe-instances --instance-ids {instance_id} --query 'Reservations[0].Instances[0].State.Name' --output text",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    instance_state = result.stdout.strip()
                    print(f"Instance state: {instance_state}")
                    
                    if instance_state == "running":
                        print("🛑 Stopping instance...")
                        subprocess.run(f"aws ec2 stop-instances --instance-ids {instance_id}", shell=True)
                        print("⏳ Waiting for instance to stop...")
                        subprocess.run(f"aws ec2 wait instance-stopped --instance-ids {instance_id}", shell=True)
                        print("✅ Instance stopped!")
                    elif instance_state == "stopped":
                        print("✅ Instance is already stopped!")
                    elif instance_state == "stopping":
                        print("⏳ Instance is stopping, waiting...")
                        subprocess.run(f"aws ec2 wait instance-stopped --instance-ids {instance_id}", shell=True)
                        print("✅ Instance stopped!")
        except Exception as e:
            print(f"⚠️  Could not stop instance: {e}")
            print("Continuing with destroy...")
    
    # Clean up SSH keys before destroying
    ssh_dir = os.path.join(project_dir, '.ssh')
    key_path = os.path.join(ssh_dir, 'my-ec2-key.pem')
    
    if os.path.exists(key_path):
        print(f"\n🔑 Removing SSH key: {key_path}")
        os.remove(key_path)
    
    # Run pulumi destroy
    print("\n💥 Running pulumi destroy...")
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        exit_code = run_command("pulumi destroy --yes")
    else:
        exit_code = run_command("pulumi destroy")
    
    if exit_code != 0:
        print("\n❌ Pulumi destroy failed!")
        sys.exit(1)
    
    print("\n✅ EC2 infrastructure destroyed successfully!")
    print("💡 Run 'pulumi ec2' to deploy again")

if __name__ == "__main__":
    main()
