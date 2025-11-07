"""AWS Lambda deployment using Pulumi."""

import json
import pulumi
import pulumi_aws as aws
from pathlib import Path

# Configuration
config = pulumi.Config()
environment = config.get("environment") or "dev"
app_name = config.get("app_name") or "driftguards-lambda"

# Create IAM role for Lambda
lambda_role = aws.iam.Role("lambda-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            }
        }]
    }),
    tags={
        "Name": f"{app_name}-lambda-role",
        "Environment": environment,
    })

# Attach basic Lambda execution policy
lambda_role_policy_attachment = aws.iam.RolePolicyAttachment("lambda-role-policy",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")

# Attach CloudWatch Logs policy for detailed logging
cloudwatch_policy_attachment = aws.iam.RolePolicyAttachment("lambda-cloudwatch-policy",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/CloudWatchLogsFullAccess")

# Create CloudWatch Log Group for Lambda
log_group = aws.cloudwatch.LogGroup("lambda-log-group",
    name=pulumi.Output.concat("/aws/lambda/", app_name, "-function"),
    retention_in_days=7,
    tags={
        "Name": f"{app_name}-logs",
        "Environment": environment,
    })

# Create Lambda function from local code
lambda_function = aws.lambda_.Function("lambda-function",
    name=f"{app_name}-function",
    runtime="python3.11",
    role=lambda_role.arn,
    handler="handler.lambda_handler",
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("./lambda_code")
    }),
    timeout=30,
    memory_size=256,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "ENVIRONMENT": environment,
            "APP_NAME": app_name,
            "LOG_LEVEL": "INFO",
        }
    ),
    tags={
        "Name": f"{app_name}-function",
        "Environment": environment,
    },
    opts=pulumi.ResourceOptions(depends_on=[log_group]))

# Create Lambda Function URL (HTTP endpoint)
function_url = aws.lambda_.FunctionUrl("lambda-function-url",
    function_name=lambda_function.name,
    authorization_type="NONE",  # Public access - change to AWS_IAM for secured access
    cors=aws.lambda_.FunctionUrlCorsArgs(
        allow_origins=["*"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
        max_age=3600,
    ))

# Create API Gateway REST API (alternative to Function URL)
api = aws.apigateway.RestApi("lambda-api",
    name=f"{app_name}-api",
    description=f"API Gateway for {app_name}",
    tags={
        "Name": f"{app_name}-api",
        "Environment": environment,
    })

# Create API Gateway resource
api_resource = aws.apigateway.Resource("lambda-api-resource",
    rest_api=api.id,
    parent_id=api.root_resource_id,
    path_part="invoke")

# Create API Gateway method
api_method = aws.apigateway.Method("lambda-api-method",
    rest_api=api.id,
    resource_id=api_resource.id,
    http_method="ANY",
    authorization="NONE")

# Create Lambda integration
api_integration = aws.apigateway.Integration("lambda-api-integration",
    rest_api=api.id,
    resource_id=api_resource.id,
    http_method=api_method.http_method,
    integration_http_method="POST",
    type="AWS_PROXY",
    uri=lambda_function.invoke_arn)

# Create API Gateway deployment
api_deployment = aws.apigateway.Deployment("lambda-api-deployment",
    rest_api=api.id,
    opts=pulumi.ResourceOptions(depends_on=[api_integration]))

# Create API Gateway stage
api_stage = aws.apigateway.Stage("lambda-api-stage",
    rest_api=api.id,
    deployment=api_deployment.id,
    stage_name=environment)

# Grant API Gateway permission to invoke Lambda
lambda_permission = aws.lambda_.Permission("lambda-api-permission",
    action="lambda:InvokeFunction",
    function=lambda_function.name,
    principal="apigateway.amazonaws.com",
    source_arn=pulumi.Output.concat(api.execution_arn, "/*/*"))

# Create CloudWatch alarm for Lambda errors
error_alarm = aws.cloudwatch.MetricAlarm("lambda-error-alarm",
    name=f"{app_name}-lambda-errors",
    comparison_operator="GreaterThanThreshold",
    evaluation_periods=1,
    metric_name="Errors",
    namespace="AWS/Lambda",
    period=300,
    statistic="Sum",
    threshold=5,
    alarm_description="Alert when Lambda function has more than 5 errors in 5 minutes",
    dimensions={
        "FunctionName": lambda_function.name,
    },
    tags={
        "Name": f"{app_name}-error-alarm",
        "Environment": environment,
    })

# Create CloudWatch alarm for Lambda throttles
throttle_alarm = aws.cloudwatch.MetricAlarm("lambda-throttle-alarm",
    name=f"{app_name}-lambda-throttles",
    comparison_operator="GreaterThanThreshold",
    evaluation_periods=1,
    metric_name="Throttles",
    namespace="AWS/Lambda",
    period=300,
    statistic="Sum",
    threshold=3,
    alarm_description="Alert when Lambda function is throttled more than 3 times in 5 minutes",
    dimensions={
        "FunctionName": lambda_function.name,
    },
    tags={
        "Name": f"{app_name}-throttle-alarm",
        "Environment": environment,
    })

# Export outputs
pulumi.export('lambda_function_name', lambda_function.name)
pulumi.export('lambda_function_arn', lambda_function.arn)
pulumi.export('lambda_function_url', function_url.function_url)
pulumi.export('lambda_role_arn', lambda_role.arn)
pulumi.export('api_gateway_url', pulumi.Output.concat(
    "https://", api.id, ".execute-api.", aws.get_region().name, ".amazonaws.com/", api_stage.stage_name, "/invoke"
))
pulumi.export('log_group_name', log_group.name)
pulumi.export('cloudwatch_dashboard_url', pulumi.Output.concat(
    "https://console.aws.amazon.com/cloudwatch/home?region=", 
    aws.get_region().name,
    "#logsV2:log-groups/log-group/",
    log_group.name
))

# Export test commands
pulumi.export('test_function_url_command', pulumi.Output.concat(
    'curl "', function_url.function_url, '"'
))
pulumi.export('test_api_gateway_command', pulumi.Output.concat(
    'curl "https://', api.id, '.execute-api.', aws.get_region().name, '.amazonaws.com/', api_stage.stage_name, '/invoke"'
))
