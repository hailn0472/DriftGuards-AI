"""Minimal S3 bucket deployment"""
import pulumi
import pulumi_aws as aws

# Create S3 bucket (encryption enabled by default)
bucket = aws.s3.BucketV2("bucket")

# Block public access
aws.s3.BucketPublicAccessBlock("pab",
    bucket=bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True)

pulumi.export("bucket_name", bucket.bucket)
pulumi.export("bucket_arn", bucket.arn)