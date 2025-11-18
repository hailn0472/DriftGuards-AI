#!/usr/bin/env python3
"""
Pulumi CLI Plugin: s3
Deploys S3 bucket infrastructure and displays bucket information
"""
import subprocess
import sys
import json
import os

def run_command(cmd, capture_output=False):
    """Run a shell command"""
    if capture_output:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    else:
        return subprocess.run(cmd, shell=True).returncode

def main():
    # Use the current working directory (where user runs the command)
    project_dir = os.getcwd()
    
    # Verify we're in a Pulumi project
    if not os.path.exists(os.path.join(project_dir, 'Pulumi.yaml')):
        print("Error: Not in a Pulumi project directory!")
        sys.exit(1)
    
    # Initialize stack if it doesn't exist
    stdout, stderr, exit_code = run_command("pulumi stack ls", capture_output=True)
    if exit_code != 0 or "dev" not in stdout:
        print("Initializing Pulumi stack...")
        exit_code = run_command("pulumi stack init dev")
        if exit_code != 0:
            print("Failed to initialize Pulumi stack!")
            sys.exit(1)
    
    # Run pulumi up
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        exit_code = run_command("pulumi up --yes")
    else:
        exit_code = run_command("pulumi up")
    
    if exit_code != 0:
        print("Pulumi deployment failed!")
        sys.exit(1)
    
    # Get stack outputs
    stdout, stderr, exit_code = run_command("pulumi stack output --json", capture_output=True)
    if exit_code != 0:
        print(f"Failed to get stack outputs: {stderr}")
        sys.exit(1)
    
    try:
        outputs = json.loads(stdout)
    except json.JSONDecodeError:
        print("Failed to parse stack outputs")
        sys.exit(1)
    
    # Display S3 bucket information
    bucket_name = outputs.get('bucket_name')
    bucket_arn = outputs.get('bucket_arn')
    bucket_domain_name = outputs.get('bucket_domain_name')
    
    if bucket_name:
        print("\n" + "="*50)
        print("S3 BUCKET DEPLOYMENT SUCCESSFUL")
        print("="*50)
        print(f"Bucket Name: {bucket_name}")
        if bucket_arn:
            print(f"Bucket ARN: {bucket_arn}")
        if bucket_domain_name:
            print(f"Bucket Domain: {bucket_domain_name}")
        print("\nUseful commands:")
        print(f"  List bucket contents: aws s3 ls s3://{bucket_name}/")
        print(f"  Copy file to bucket:  aws s3 cp <file> s3://{bucket_name}/")
        print(f"  Sync directory:       aws s3 sync <dir> s3://{bucket_name}/")
        print("="*50)
    else:
        print("Could not retrieve bucket information")
        sys.exit(1)

if __name__ == "__main__":
    main()