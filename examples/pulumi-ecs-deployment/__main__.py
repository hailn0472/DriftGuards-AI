"""An AWS Python Pulumi program for ECS cluster deployment"""

import pulumi
import pulumi_aws as aws
import pulumi_awsx as awsx
import random
import string
import json

# Configuration
config = pulumi.Config()
environment = config.get("environment") or "dev"
app_name = config.get("app_name") or "driftguards-ecs"

# Generate unique cluster name
random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
cluster_name = f"{app_name}-{environment}-{random_suffix}"

# Create VPC for ECS cluster
vpc = awsx.ec2.Vpc("ecs-vpc",
    cidr_block="10.0.0.0/16",
    number_of_availability_zones=2,
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={
        "Name": f"{cluster_name}-vpc",
        "Environment": environment,
    })

# Create ECS cluster
cluster = aws.ecs.Cluster("ecs-cluster",
    name=cluster_name,
    tags={
        "Name": cluster_name,
        "Environment": environment,
    })

# Enable container insights for monitoring
cluster_capacity_providers = aws.ecs.ClusterCapacityProviders("ecs-capacity-providers",
    cluster_name=cluster.name,
    capacity_providers=["FARGATE", "FARGATE_SPOT"],
    default_capacity_provider_strategies=[
        {
            "capacity_provider": "FARGATE",
            "weight": 1,
            "base": 1,
        },
        {
            "capacity_provider": "FARGATE_SPOT",
            "weight": 4,
        },
    ])

# Create IAM role for ECS task execution
task_execution_role = aws.iam.Role("ecs-task-execution-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            }
        }]
    }),
    tags={
        "Name": f"{cluster_name}-task-execution-role",
        "Environment": environment,
    })

# Attach required policies to task execution role
task_execution_policy_attachment = aws.iam.RolePolicyAttachment("ecs-task-execution-policy",
    role=task_execution_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy")

# Create IAM role for ECS task
task_role = aws.iam.Role("ecs-task-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Effect": "Allow",
            "Principal": {
                "Service": "ecs-tasks.amazonaws.com"
            }
        }]
    }),
    tags={
        "Name": f"{cluster_name}-task-role",
        "Environment": environment,
    })

# Create CloudWatch Log Group
log_group = aws.cloudwatch.LogGroup("ecs-log-group",
    name=f"/ecs/{cluster_name}",
    retention_in_days=7,
    tags={
        "Name": f"{cluster_name}-logs",
        "Environment": environment,
    })

# Create security group for ECS tasks
security_group = aws.ec2.SecurityGroup("ecs-security-group",
    name=f"{cluster_name}-sg",
    description="Security group for ECS tasks",
    vpc_id=vpc.vpc_id,
    ingress=[
        {
            "protocol": "tcp",
            "from_port": 80,
            "to_port": 80,
            "cidr_blocks": ["0.0.0.0/0"],
            "description": "HTTP access",
        },
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
        "Name": f"{cluster_name}-sg",
        "Environment": environment,
    })

# Create ECS task definition for a sample nginx service
task_definition = aws.ecs.TaskDefinition("ecs-task-definition",
    family=f"{cluster_name}-nginx",
    network_mode="awsvpc",
    requires_compatibilities=["FARGATE"],
    cpu="256",
    memory="512",
    execution_role_arn=task_execution_role.arn,
    task_role_arn=task_role.arn,
    container_definitions=json.dumps([{
        "name": "nginx",
        "image": "nginx:latest",
        "essential": True,
        "portMappings": [{
            "containerPort": 80,
            "protocol": "tcp"
        }],
        "logConfiguration": {
            "logDriver": "awslogs",
            "options": {
                "awslogs-group": log_group.name,
                "awslogs-region": aws.get_region().name,
                "awslogs-stream-prefix": "ecs"
            }
        },
        "environment": [
            {
                "name": "ENVIRONMENT",
                "value": environment
            },
            {
                "name": "CLUSTER_NAME",
                "value": cluster_name
            }
        ]
    }]),
    tags={
        "Name": f"{cluster_name}-task-definition",
        "Environment": environment,
    })

# Create Application Load Balancer
alb = aws.lb.LoadBalancer("ecs-alb",
    name=f"{cluster_name}-alb"[:32],  # ALB names have 32 char limit
    load_balancer_type="application",
    security_groups=[security_group.id],
    subnets=vpc.public_subnet_ids,
    enable_deletion_protection=False,
    tags={
        "Name": f"{cluster_name}-alb",
        "Environment": environment,
    })

# Create target group for ALB
target_group = aws.lb.TargetGroup("ecs-target-group",
    name=f"{cluster_name}-tg"[:32],  # Target group names have 32 char limit
    port=80,
    protocol="HTTP",
    vpc_id=vpc.vpc_id,
    target_type="ip",
    health_check={
        "enabled": True,
        "healthy_threshold": 2,
        "interval": 30,
        "matcher": "200",
        "path": "/",
        "port": "traffic-port",
        "protocol": "HTTP",
        "timeout": 5,
        "unhealthy_threshold": 2,
    },
    tags={
        "Name": f"{cluster_name}-target-group",
        "Environment": environment,
    })

# Create ALB listener
listener = aws.lb.Listener("ecs-listener",
    load_balancer_arn=alb.arn,
    port="80",
    protocol="HTTP",
    default_actions=[{
        "type": "forward",
        "target_group_arn": target_group.arn,
    }])

# Create ECS service
service = aws.ecs.Service("ecs-service",
    name=f"{cluster_name}-nginx-service",
    cluster=cluster.id,
    task_definition=task_definition.arn,
    desired_count=2,
    launch_type="FARGATE",
    network_configuration={
        "subnets": vpc.private_subnet_ids,
        "security_groups": [security_group.id],
        "assign_public_ip": True,
    },
    load_balancers=[{
        "target_group_arn": target_group.arn,
        "container_name": "nginx",
        "container_port": 80,
    }],
    depends_on=[listener],
    tags={
        "Name": f"{cluster_name}-service",
        "Environment": environment,
    })

# Create CloudWatch alarms for monitoring
cpu_alarm = aws.cloudwatch.MetricAlarm("ecs-cpu-alarm",
    name=f"{cluster_name}-high-cpu",
    comparison_operator="GreaterThanThreshold",
    evaluation_periods=2,
    metric_name="CPUUtilization",
    namespace="AWS/ECS",
    period=300,
    statistic="Average",
    threshold=80,
    alarm_description="Alert when ECS service CPU exceeds 80%",
    dimensions={
        "ServiceName": service.name,
        "ClusterName": cluster.name,
    },
    tags={
        "Name": f"{cluster_name}-cpu-alarm",
        "Environment": environment,
    })

memory_alarm = aws.cloudwatch.MetricAlarm("ecs-memory-alarm",
    name=f"{cluster_name}-high-memory",
    comparison_operator="GreaterThanThreshold",
    evaluation_periods=2,
    metric_name="MemoryUtilization",
    namespace="AWS/ECS",
    period=300,
    statistic="Average",
    threshold=80,
    alarm_description="Alert when ECS service memory exceeds 80%",
    dimensions={
        "ServiceName": service.name,
        "ClusterName": cluster.name,
    },
    tags={
        "Name": f"{cluster_name}-memory-alarm",
        "Environment": environment,
    })

# Export cluster information
pulumi.export('cluster_name', cluster.name)
pulumi.export('cluster_arn', cluster.arn)
pulumi.export('service_name', service.name)
pulumi.export('service_arn', service.arn)
pulumi.export('task_definition_arn', task_definition.arn)
pulumi.export('load_balancer_dns', alb.dns_name)
pulumi.export('load_balancer_url', pulumi.Output.concat('http://', alb.dns_name))
pulumi.export('vpc_id', vpc.vpc_id)
pulumi.export('private_subnet_ids', vpc.private_subnet_ids)
pulumi.export('public_subnet_ids', vpc.public_subnet_ids)
pulumi.export('log_group_name', log_group.name)

# Export useful commands
pulumi.export('service_status_command', pulumi.Output.concat(
    'aws ecs describe-services --cluster ', cluster.name, ' --services ', service.name
))
pulumi.export('task_logs_command', pulumi.Output.concat(
    'aws logs tail ', log_group.name, ' --follow'
))
pulumi.export('scale_service_command', pulumi.Output.concat(
    'aws ecs update-service --cluster ', cluster.name, ' --service ', service.name, ' --desired-count 3'
))