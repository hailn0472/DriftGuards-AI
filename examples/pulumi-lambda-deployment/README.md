# 🚀 Pulumi Lambda Deployment Example

This example demonstrates how to deploy an AWS Lambda function using Pulumi infrastructure as code. The Lambda function is designed to work with DriftGuards AI for testing drift detection on serverless resources.

## 📦 What's Deployed

This Pulumi program creates:

1. **Lambda Function** - Python 3.11 runtime with custom handler
2. **IAM Role** - Execution role with CloudWatch Logs permissions
3. **Lambda Function URL** - Public HTTP endpoint (no auth)
4. **API Gateway** - REST API with Lambda integration
5. **CloudWatch Log Group** - 7-day retention for Lambda logs
6. **CloudWatch Alarms** - Monitoring for errors and throttles

## 🏗️ Architecture

```
┌─────────────────────┐
│  Lambda Function    │
│  (Python 3.11)      │
│  - handler.py       │
└──────┬──────────────┘
       │
       ├──► Function URL (Public)
       │    https://xxx.lambda-url.region.on.aws/
       │
       └──► API Gateway
            https://xxx.execute-api.region.amazonaws.com/dev/invoke

┌─────────────────────┐
│  CloudWatch Logs    │
│  /aws/lambda/...    │
└─────────────────────┘

┌─────────────────────┐
│  CloudWatch Alarms  │
│  - Error Alarm      │
│  - Throttle Alarm   │
└─────────────────────┘
```

## 📋 Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Pulumi CLI** installed
4. **Python 3.8+** installed

### Install Pulumi

```bash
# macOS/Linux
curl -fsSL https://get.pulumi.com | sh

# Windows (PowerShell)
choco install pulumi
```

### Verify Installation

```bash
pulumi version
aws configure list
```

## 🚀 Quick Start

### 1. Navigate to Directory

```bash
cd examples/pulumi-lambda-deployment
```

### 2. Install Dependencies

```bash
# Navigate to examples directory (parent folder)
cd ..

# Create virtual environment (if not already created)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install shared Pulumi packages (only once for all examples)
pip install -r requirements.txt

# Navigate back to lambda deployment
cd pulumi-lambda-deployment
```

> **Note**: The `requirements.txt` is shared across all Pulumi examples in the `examples/` directory. You only need to install it once to use all example projects (EC2, Lambda, etc.).

### 3. Configure Pulumi

```bash
# Login to Pulumi (use local backend or Pulumi Cloud)
pulumi login --local  # or just 'pulumi login' for cloud

# Select or create stack
pulumi stack select dev  # or 'pulumi stack init dev'

# Set AWS region
pulumi config set aws:region ap-southeast-1

# Optional: Customize app name
pulumi config set app_name my-lambda-app
```

### 4. Deploy

```bash
# Preview changes
pulumi preview

# Deploy infrastructure
pulumi up
```

### 5. Test the Lambda Function

After deployment, test using the exported Function URL:

```bash
# Get the function URL from outputs
pulumi stack output lambda_function_url

# Test with curl
curl "$(pulumi stack output lambda_function_url)"
```

Expected response:
```json
{
  "message": "Hello from driftguards-lambda!",
  "timestamp": "2025-11-07T14:00:00.000000",
  "environment": "dev",
  "request": {
    "path": "/",
    "method": "GET",
    "body": null
  },
  "function_info": {
    "function_name": "driftguards-lambda-function",
    "function_version": "$LATEST",
    "memory_limit": 256,
    "request_id": "..."
  }
}
```

## 🧪 Testing

### Test Function URL

```bash
# Simple GET request
curl "$(pulumi stack output lambda_function_url)"

# POST request with data
curl -X POST "$(pulumi stack output lambda_function_url)" \
  -H "Content-Type: application/json" \
  -d '{"test": "data", "message": "Hello Lambda"}'
```

### Test API Gateway

```bash
# Get API Gateway URL
pulumi stack output api_gateway_url

# Test API Gateway endpoint
curl "$(pulumi stack output api_gateway_url)"
```

### View CloudWatch Logs

```bash
# Get log group name
pulumi stack output log_group_name

# View logs with AWS CLI
aws logs tail "$(pulumi stack output log_group_name)" --follow

# Or open CloudWatch dashboard
pulumi stack output cloudwatch_dashboard_url
```

## 📊 Monitoring

### CloudWatch Alarms

Two alarms are created automatically:

1. **Error Alarm** - Triggers when Lambda has >5 errors in 5 minutes
2. **Throttle Alarm** - Triggers when Lambda is throttled >3 times in 5 minutes

View alarms:
```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix "driftguards-lambda"
```

### CloudWatch Metrics

View Lambda metrics in CloudWatch console:
- **Invocations** - Number of function calls
- **Duration** - Execution time
- **Errors** - Failed invocations
- **Throttles** - Rate-limited invocations
- **ConcurrentExecutions** - Concurrent runs

## 🔄 DriftGuards Integration

### Baseline Creation

After deployment, create a baseline for drift detection:

```bash
cd ../..  # Back to project root
python scripts/discover_aws_resources.py
```

### Test Drift Detection

1. **Modify Lambda configuration** in AWS Console:
   - Change memory size: 256 MB → 512 MB
   - Change timeout: 30s → 60s
   - Add environment variable

2. **Run drift detection**:
   ```bash
   python -m app.dashboard.app
   # Click "Run Detection" in dashboard
   ```

3. **Expected drift detected**:
   - Lambda memory size changed
   - Lambda timeout changed
   - New environment variable added

4. **Approve drift** to update baseline

## 🎯 Pulumi Outputs

After deployment, these outputs are available:

| Output | Description |
|--------|-------------|
| `lambda_function_name` | Lambda function name |
| `lambda_function_arn` | Lambda function ARN |
| `lambda_function_url` | Public HTTP endpoint URL |
| `lambda_role_arn` | IAM role ARN |
| `api_gateway_url` | API Gateway invoke URL |
| `log_group_name` | CloudWatch log group name |
| `cloudwatch_dashboard_url` | CloudWatch logs console URL |
| `test_function_url_command` | curl command to test Function URL |
| `test_api_gateway_command` | curl command to test API Gateway |

View all outputs:
```bash
pulumi stack output
```

## 🛠️ Customization

### Modify Lambda Code

Edit `lambda_code/handler.py` to change Lambda behavior:

```python
def lambda_handler(event, context):
    # Your custom logic here
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Custom response'})
    }
```

Redeploy:
```bash
pulumi up
```

### Change Configuration

```bash
# Change environment
pulumi config set environment production

# Change app name
pulumi config set app_name my-custom-lambda

# Change AWS region
pulumi config set aws:region us-east-1
```

### Add Dependencies

If Lambda needs Python packages:

1. Create `lambda_code/requirements.txt`:
   ```
   boto3
   requests
   ```

2. Update `__main__.py` to bundle dependencies:
   ```python
   # Add layer or bundle with Lambda code
   ```

## 🧹 Cleanup

To destroy all resources:

```bash
# Preview what will be deleted
pulumi destroy --preview

# Confirm and destroy
pulumi destroy
```

## 📁 Project Structure

```
pulumi-lambda-deployment/
├── __main__.py              # Pulumi infrastructure code
├── Pulumi.yaml              # Pulumi project config
├── Pulumi.dev.yaml          # Stack-specific config
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore patterns
├── README.md               # This file
└── lambda_code/
    └── handler.py          # Lambda function code
```

## 🔐 Security Considerations

### Current Setup (Development)
- ✅ Function URL has **NO authentication** (for testing)
- ✅ API Gateway has **NO authentication** (for testing)
- ✅ CORS allows all origins

### Production Recommendations
1. **Enable IAM authentication** on Function URL:
   ```python
   authorization_type="AWS_IAM"
   ```

2. **Add API Gateway authorizer**:
   - Lambda authorizer
   - Cognito User Pool
   - API Key

3. **Restrict CORS origins**:
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

4. **Enable encryption**:
   - Encrypt environment variables with KMS
   - Enable CloudWatch Logs encryption

5. **Apply least privilege IAM**:
   - Grant only necessary permissions
   - Use IAM conditions

## 🐛 Troubleshooting

### Issue: "Cannot assume role"

**Solution**: Ensure IAM role trust policy allows Lambda service

### Issue: "Function URL not working"

**Solution**: 
- Check authorization type
- Verify CORS settings
- Check CloudWatch logs for errors

### Issue: "Pulumi state locked"

**Solution**:
```bash
pulumi cancel
```

### Issue: "Import error in Lambda"

**Solution**: 
- Verify Python version (3.11)
- Check lambda_code directory structure
- Review CloudWatch logs

## 📚 Resources

- [Pulumi AWS Lambda Documentation](https://www.pulumi.com/registry/packages/aws/api-docs/lambda/)
- [AWS Lambda Python Runtime](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [Lambda Function URLs](https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html)
- [API Gateway Lambda Integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-integrations.html)

## 💡 Tips

1. **Use Pulumi watch** for rapid development:
   ```bash
   pulumi watch
   ```

2. **View real-time logs**:
   ```bash
   aws logs tail /aws/lambda/driftguards-lambda-function --follow
   ```

3. **Invoke Lambda directly**:
   ```bash
   aws lambda invoke \
     --function-name driftguards-lambda-function \
     --payload '{"test": "data"}' \
     response.json
   ```

4. **Check Lambda metrics**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Invocations \
     --dimensions Name=FunctionName,Value=driftguards-lambda-function \
     --start-time 2025-11-07T00:00:00Z \
     --end-time 2025-11-07T23:59:59Z \
     --period 3600 \
     --statistics Sum
   ```

---

**Built for DriftGuards AI** 🛡️ - Infrastructure Drift Detection & Prevention
