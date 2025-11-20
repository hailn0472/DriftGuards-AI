"""Minimal DynamoDB table deployment"""
import pulumi
import pulumi_aws as aws

# Simple table with hash key only
table = aws.dynamodb.Table("table",
    billing_mode="PAY_PER_REQUEST",
    hash_key="id",
    attributes=[aws.dynamodb.TableAttributeArgs(name="id", type="S")])

pulumi.export("table_name", table.name)
pulumi.export("table_arn", table.arn)