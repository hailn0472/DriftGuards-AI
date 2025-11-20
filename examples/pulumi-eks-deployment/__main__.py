"""Minimal AWS EKS cluster - Control plane only"""

import pulumi
import pulumi_aws as aws

# Configuration
config = pulumi.Config()
cluster_name = config.get("cluster_name") or "minimal-eks"
vpc_id = config.get("vpc_id")  # Optional: specify existing VPC ID

# Get VPC and subnets
if vpc_id:
    # Use specified VPC
    subnets = aws.ec2.get_subnets(filters=[{"name": "vpc-id", "values": [vpc_id]}])
    subnet_ids = subnets.ids
else:
    # Try to find any existing VPC with subnets
    try:
        # Try default VPC first
        vpc = aws.ec2.get_vpc(default=True)
        vpc_id = vpc.id
    except:
        # Get first available VPC
        vpcs = aws.ec2.get_vpcs()
        if len(vpcs.ids) > 0:
            vpc_id = vpcs.ids[0]
        else:
            raise Exception("No VPC found. Please create a VPC first or specify vpc_id in config.")
    
    # Get subnets from VPC
    subnets = aws.ec2.get_subnets(filters=[{"name": "vpc-id", "values": [vpc_id]}])
    
    # EKS requires at least 2 subnets in different AZs
    if len(subnets.ids) < 2:
        raise Exception(f"VPC {vpc_id} needs at least 2 subnets in different AZs for EKS")
    
    subnet_ids = subnets.ids[:2]  # Use first 2 subnets

# IAM role for EKS cluster
cluster_role = aws.iam.Role("eks-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {"Service": "eks.amazonaws.com"}
        }]
    }""")

aws.iam.RolePolicyAttachment("eks-policy",
    role=cluster_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy")

# EKS cluster (control plane only)
cluster = aws.eks.Cluster("eks",
    name=cluster_name,
    role_arn=cluster_role.arn,
    vpc_config={"subnet_ids": subnet_ids})

# Exports
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_endpoint", cluster.endpoint)
pulumi.export("kubeconfig", pulumi.Output.concat(
    "aws eks update-kubeconfig --region ", 
    aws.get_region().name, 
    " --name ", 
    cluster.name))