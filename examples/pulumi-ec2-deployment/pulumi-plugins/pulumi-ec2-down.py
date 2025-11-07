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
    # Use the current working directory (where user runs the command)
    project_dir = os.getcwd()
    
    # Verify we're in a Pulumi project
    if not os.path.exists(os.path.join(project_dir, 'Pulumi.yaml')):
        print("Error: Not in a Pulumi project directory!")
        sys.exit(1)
    
    # Get instance ID and stop it before destroying
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
                # Check instance state
                result = subprocess.run(
                    f"aws ec2 describe-instances --instance-ids {instance_id} --query 'Reservations[0].Instances[0].State.Name' --output text",
                    shell=True,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    instance_state = result.stdout.strip()
                    
                    if instance_state == "running":
                        subprocess.run(f"aws ec2 stop-instances --instance-ids {instance_id}", shell=True)
                        subprocess.run(f"aws ec2 wait instance-stopped --instance-ids {instance_id}", shell=True)
                    elif instance_state == "stopping":
                        subprocess.run(f"aws ec2 wait instance-stopped --instance-ids {instance_id}", shell=True)
        except Exception as e:
            pass
    
    # Clean up SSH keys before destroying
    ssh_dir = os.path.join(project_dir, '.ssh')
    key_path = os.path.join(ssh_dir, 'my-ec2-key.pem')
    
    if os.path.exists(key_path):
        os.remove(key_path)
    
    # Run pulumi destroy
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        exit_code = run_command("pulumi destroy --yes")
    else:
        exit_code = run_command("pulumi destroy")
    
    if exit_code != 0:
        print("Pulumi destroy failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
