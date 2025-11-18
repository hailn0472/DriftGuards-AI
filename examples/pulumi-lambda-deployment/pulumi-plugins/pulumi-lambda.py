#!/usr/bin/env python3
"""
Pulumi CLI Plugin: lambda
Deploys Lambda function and tests it
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
    
    # Initialize stack if it doesn't exist
    stdout, stderr, exit_code = run_command("pulumi stack ls", capture_output=True)
    if exit_code != 0 or "dev" not in stdout:
        print("Initializing Pulumi stack...")
        exit_code = run_command("pulumi stack init dev")
        if exit_code != 0:
            print("Failed to initialize Pulumi stack!")
            sys.exit(1)
    
    print_section("🚀 Deploying Lambda Function")
    
    # Run pulumi up
    if len(sys.argv) > 1 and sys.argv[1] == "--yes":
        exit_code = run_command("pulumi up --yes")
    else:
        exit_code = run_command("pulumi up")
    
    if exit_code != 0:
        print("❌ Pulumi deployment failed!")
        sys.exit(1)
    
    print_section("📊 Getting Stack Outputs")
    
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
    
    # Extract outputs
    function_name = outputs.get('lambda_function_name')
    function_arn = outputs.get('lambda_function_arn')
    function_url = outputs.get('lambda_function_url')
    api_gateway_url = outputs.get('api_gateway_url')
    log_group_name = outputs.get('log_group_name')
    
    # Display deployment info
    print("\n✅ Lambda Function Deployed Successfully!")
    print(f"\n📦 Function Details:")
    print(f"  Name: {function_name}")
    print(f"  ARN:  {function_arn}")
    
    if function_url:
        print(f"\n🔗 Function URL (Public Endpoint):")
        print(f"  {function_url}")
    
    if api_gateway_url:
        print(f"\n🌐 API Gateway URL:")
        print(f"  {api_gateway_url}")
    
    if log_group_name:
        print(f"\n📝 CloudWatch Logs:")
        print(f"  {log_group_name}")
    
    # Test the Lambda function
    if function_url:
        print_section("🧪 Testing Lambda Function")
        
        print("Testing Function URL with curl...\n")
        
        # Test GET request
        stdout, stderr, exit_code = run_command(f'curl -s "{function_url}"', capture_output=True)
        
        if exit_code == 0:
            print("Response:")
            try:
                response = json.loads(stdout)
                print(json.dumps(response, indent=2))
            except:
                print(stdout)
        else:
            print(f"Test failed: {stderr}")
        
        # Test POST request
        print("\n" + "-"*80)
        print("Testing POST request with sample data...\n")
        
        test_data = json.dumps({"test": "data", "message": "Hello Lambda!"})
        stdout, stderr, exit_code = run_command(
            f'curl -s -X POST "{function_url}" -H "Content-Type: application/json" -d \'{test_data}\'',
            capture_output=True
        )
        
        if exit_code == 0:
            print("Response:")
            try:
                response = json.loads(stdout)
                print(json.dumps(response, indent=2))
            except:
                print(stdout)
    
    # Show useful commands
    print_section("📚 Useful Commands")
    
    print("View logs:")
    print(f'  aws logs tail "{log_group_name}" --follow\n')
    
    print("Invoke function directly:")
    print(f'  aws lambda invoke --function-name {function_name} --payload \'{{"test":"data"}}\' response.json\n')
    
    print("Test Function URL:")
    print(f'  curl "{function_url}"\n')
    
    if api_gateway_url:
        print("Test API Gateway:")
        print(f'  curl "{api_gateway_url}"\n')
    
    print("View all outputs:")
    print(f'  pulumi stack output\n')
    
    print("Destroy infrastructure:")
    print(f'  pulumi-lambda-down\n')
    
    print_section("✅ Deployment Complete")
    
    print("Your Lambda function is now live and ready to use!")
    print(f"\nFunction URL: {function_url}\n")

if __name__ == "__main__":
    main()
