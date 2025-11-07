#!/usr/bin/env python3
"""
Pulumi CLI Plugin: lambda-down
Destroys Lambda infrastructure
"""
import subprocess
import sys
import os
import json

def run_command(cmd, capture_output=False):
    """Run a shell command"""
    if capture_output:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    else:
        return subprocess.run(cmd, shell=True).returncode

def print_section(title):
    """Print a section header"""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")

def main():
    # Use the current working directory
    project_dir = os.getcwd()
    
    # Verify we're in a Pulumi project
    if not os.path.exists(os.path.join(project_dir, 'Pulumi.yaml')):
        print("Error: Not in a Pulumi project directory!")
        sys.exit(1)
    
    print_section("🗑️  Destroying Lambda Infrastructure")
    
    # Get stack outputs before destroying
    stdout, stderr, exit_code = run_command("pulumi stack output --json", capture_output=True)
    
    if exit_code == 0:
        try:
            outputs = json.loads(stdout)
            function_name = outputs.get('lambda_function_name')
            function_url = outputs.get('lambda_function_url')
            log_group_name = outputs.get('log_group_name')
            
            print("Resources to be destroyed:")
            if function_name:
                print(f"  ❌ Lambda Function: {function_name}")
            if function_url:
                print(f"  ❌ Function URL: {function_url}")
            if log_group_name:
                print(f"  ❌ CloudWatch Logs: {log_group_name}")
            print(f"  ❌ IAM Role")
            print(f"  ❌ API Gateway")
            print(f"  ❌ CloudWatch Alarms")
            print()
        except Exception as e:
            print(f"Could not parse outputs: {e}")
    
    # Run pulumi destroy
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        exit_code = run_command("pulumi destroy --yes")
    else:
        exit_code = run_command("pulumi destroy")
    
    if exit_code != 0:
        print("\n❌ Pulumi destroy failed!")
        sys.exit(1)
    
    print_section("✅ Cleanup Complete")
    
    print("All Lambda resources have been destroyed.")
    print("Your AWS account is now clean.\n")

if __name__ == "__main__":
    main()
