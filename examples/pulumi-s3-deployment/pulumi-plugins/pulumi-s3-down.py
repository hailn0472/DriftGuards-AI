#!/usr/bin/env python3
"""
Pulumi CLI Plugin: s3-down
Tears down S3 bucket infrastructure with bucket cleanup
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

def empty_bucket(bucket_name):
    """Empty S3 bucket before deletion"""
    print(f"Emptying bucket: {bucket_name}")
    
    # Remove all objects including versions
    stdout, stderr, exit_code = run_command(
        f"aws s3api list-object-versions --bucket {bucket_name} --output json",
        capture_output=True
    )
    
    if exit_code == 0:
        try:
            response = json.loads(stdout)
            
            # Delete all versions
            if 'Versions' in response:
                for version in response['Versions']:
                    key = version['Key']
                    version_id = version['VersionId']
                    run_command(f"aws s3api delete-object --bucket {bucket_name} --key \"{key}\" --version-id {version_id}")
            
            # Delete all delete markers
            if 'DeleteMarkers' in response:
                for marker in response['DeleteMarkers']:
                    key = marker['Key']
                    version_id = marker['VersionId']
                    run_command(f"aws s3api delete-object --bucket {bucket_name} --key \"{key}\" --version-id {version_id}")
                    
        except json.JSONDecodeError:
            # Fallback: try to empty using aws s3 rm
            run_command(f"aws s3 rm s3://{bucket_name} --recursive")
    else:
        # Bucket might not exist or might be empty, continue
        print(f"Could not list objects in {bucket_name} (bucket might be empty or not exist)")

def main():
    # Use the current working directory (where user runs the command)
    project_dir = os.getcwd()
    
    # Verify we're in a Pulumi project
    if not os.path.exists(os.path.join(project_dir, 'Pulumi.yaml')):
        print("Error: Not in a Pulumi project directory!")
        sys.exit(1)
    
    # Get stack outputs before destroying
    stdout, stderr, exit_code = run_command("pulumi stack output --json", capture_output=True)
    
    if exit_code == 0:
        try:
            outputs = json.loads(stdout)
            bucket_name = outputs.get('bucket_name')
            
            if bucket_name:
                print(f"Found bucket: {bucket_name}")
                empty_bucket(bucket_name)
            else:
                print("No bucket found in stack outputs")
        except json.JSONDecodeError:
            print("Could not parse stack outputs, continuing with destroy...")
    else:
        print("Could not get stack outputs, continuing with destroy...")
    
    # Run pulumi destroy
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        exit_code = run_command("pulumi destroy --yes")
    else:
        exit_code = run_command("pulumi destroy")
    
    if exit_code != 0:
        print("Pulumi destroy failed!")
        sys.exit(1)
    
    print("\nS3 bucket infrastructure has been successfully destroyed.")

if __name__ == "__main__":
    main()