"""Minimal Lambda function deployment"""
import pulumi
import pulumi_aws as aws

# IAM role for Lambda
role = aws.iam.Role("role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"}
        }]
    }""")

aws.iam.RolePolicyAttachment("policy",
    role=role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")

# Lambda function
function = aws.lambda_.Function("function",
    runtime="python3.11",
    role=role.arn,
    handler="index.handler",
    code=pulumi.AssetArchive({
        "index.py": pulumi.StringAsset("def handler(event, context): return {'statusCode': 200, 'body': 'Hello'}")
    }))

pulumi.export("function_name", function.name)
pulumi.export("function_arn", function.arn)
