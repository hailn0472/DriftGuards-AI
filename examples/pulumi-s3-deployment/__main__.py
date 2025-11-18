"""An AWS Python Pulumi program for S3 bucket deployment"""
import pulumi
import pulumi_aws as aws

# Generate a unique bucket name to avoid conflicts
import random
import string
random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
bucket_name = f"driftguards-pulumi-{pulumi.get_stack()}-{random_suffix}"

# Create an S3 bucket
bucket = aws.s3.BucketV2(
    "my-s3-bucket",
    bucket=bucket_name,
    tags={
        "Name": "my-s3-bucket",
        "Environment": pulumi.get_stack(),
    }
)

# Configure bucket versioning
bucket_versioning = aws.s3.BucketVersioningV2(
    "bucket-versioning",
    bucket=bucket.id,
    versioning_configuration={
        "status": "Enabled",
    }
)

# Note: Server-side encryption is enabled by default on new S3 buckets
# No explicit configuration needed for basic AES256 encryption

# Block public access for security
bucket_public_access_block = aws.s3.BucketPublicAccessBlock(
    "bucket-pab",
    bucket=bucket.id,
    block_public_acls=True,
    block_public_policy=True,
    ignore_public_acls=True,
    restrict_public_buckets=True
)

# Export bucket information
pulumi.export('bucket_id', bucket.id)
pulumi.export('bucket_name', bucket.bucket)
pulumi.export('bucket_arn', bucket.arn)
pulumi.export('bucket_domain_name', bucket.bucket_domain_name)
pulumi.export('bucket_regional_domain_name', bucket.bucket_regional_domain_name)