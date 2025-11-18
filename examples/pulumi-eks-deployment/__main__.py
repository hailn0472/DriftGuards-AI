"""An AWS Python Pulumi program for EKS cluster deployment"""

import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
import random
import string

# Configuration
config = pulumi.Config()
environment = config.get("environment") or "dev"
app_name = config.get("app_name") or "driftguards-eks"

# Generate unique cluster name
random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
cluster_name = f"{app_name}-{environment}-{random_suffix}"

# Create VPC for EKS cluster
vpc = awsx.ec2.Vpc("eks-vpc",
    cidr_block="10.0.0.0/16",
    number_of_availability_zones=2,
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={
        "Name": f"{cluster_name}-vpc",
        "Environment": environment,
    })

# Create IAM role for EKS cluster
cluster_role = aws.iam.Role("eks-cluster-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "eks.amazonaws.com"
            }
        }]
    }""",
    tags={
        "Name": f"{cluster_name}-cluster-role",
        "Environment": environment,
    })

# Attach required policies to cluster role
cluster_policy_attachment = aws.iam.RolePolicyAttachment("eks-cluster-policy",
    role=cluster_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy")

# Create IAM role for EKS node group
node_role = aws.iam.Role("eks-node-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "ec2.amazonaws.com"
            }
        }]
    }""",
    tags={
        "Name": f"{cluster_name}-node-role",
        "Environment": environment,
    })

# Attach required policies to node role
node_policy_attachments = [
    aws.iam.RolePolicyAttachment("eks-worker-node-policy",
        role=node_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"),
    aws.iam.RolePolicyAttachment("eks-cni-policy",
        role=node_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"),
    aws.iam.RolePolicyAttachment("eks-container-registry-policy",
        role=node_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"),
]

# Create EKS cluster
cluster = aws.eks.Cluster("eks-cluster",
    name=cluster_name,
    role_arn=cluster_role.arn,
    vpc_config={
        "subnet_ids": pulumi.Output.all(vpc.public_subnet_ids, vpc.private_subnet_ids).apply(
            lambda subnets: subnets[0] + subnets[1]
        ),
        "endpoint_private_access": True,
        "endpoint_public_access": True,
        "public_access_cidrs": ["0.0.0.0/0"],
    },
    version="1.28",
    tags={
        "Name": cluster_name,
        "Environment": environment,
    },
    opts=pulumi.ResourceOptions(depends_on=[cluster_policy_attachment]))

# Create EKS node group
node_group = aws.eks.NodeGroup("eks-node-group",
    cluster_name=cluster.name,
    node_group_name=f"{cluster_name}-nodes",
    node_role_arn=node_role.arn,
    subnet_ids=vpc.private_subnet_ids,
    instance_types=["t3.medium"],
    capacity_type="ON_DEMAND",
    scaling_config={
        "desired_size": 2,
        "max_size": 4,
        "min_size": 1,
    },
    update_config={
        "max_unavailable": 1,
    },
    tags={
        "Name": f"{cluster_name}-node-group",
        "Environment": environment,
    },
    opts=pulumi.ResourceOptions(depends_on=node_policy_attachments))

# Create security group for additional access
cluster_security_group = aws.ec2.SecurityGroup("eks-cluster-sg",
    name=f"{cluster_name}-additional-sg",
    description="Additional security group for EKS cluster",
    vpc_id=vpc.vpc_id,
    ingress=[
        {
            "protocol": "tcp",
            "from_port": 443,
            "to_port": 443,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "HTTPS access",
        },
    ],
    egress=[
        {
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "All outbound traffic",
        },
    ],
    tags={
        "Name": f"{cluster_name}-additional-sg",
        "Environment": environment,
    })

# Export cluster information
pulumi.export('cluster_name', cluster.name)
pulumi.export('cluster_arn', cluster.arn)
pulumi.export('cluster_endpoint', cluster.endpoint)
pulumi.export('cluster_version', cluster.version)
pulumi.export('cluster_security_group_ids', cluster.vpc_config.security_group_ids)
pulumi.export('node_group_arn', node_group.arn)
pulumi.export('vpc_id', vpc.vpc_id)
pulumi.export('private_subnet_ids', vpc.private_subnet_ids)
pulumi.export('public_subnet_ids', vpc.public_subnet_ids)

# Export kubectl config command
pulumi.export('kubeconfig_command', pulumi.Output.concat(
    'aws eks update-kubeconfig --region ', aws.get_region().name, ' --name ', cluster.name
))

# Export cluster status check command
pulumi.export('cluster_status_command', pulumi.Output.concat(
    'kubectl get nodes --kubeconfig ~/.kube/config'
))