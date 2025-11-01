"""
Pulumi program (Python) — E-commerce infra on AWS + Instana agents

This file was updated to be safe to *run in sandboxed/dev environments* where the Pulumi SDK
is not installed. The original program provisions a full AWS-based e-commerce stack and
installs Instana agents. In environments without Pulumi available (ModuleNotFoundError),
this script now falls back to a **dry-run planning mode** that writes a JSON "plan" describing
what resources would be created. This avoids the `ModuleNotFoundError` and gives clear
instructions to run the real Pulumi program in an environment with Pulumi installed.

IMPORTANT FIX (from previous iteration):
- Previously the script called `sys.exit(0)` after writing the dry-run plan. That caused
  a `SystemExit` exception in some sandbox/test harness environments. This version **does not
  call** `sys.exit(0)`. Instead, the real Pulumi resource creation code is guarded behind
  `if PULUMI_AVAILABLE:` so the module can be imported/executed safely in both modes without
  raising `SystemExit`.

How it works:
- Attempts to import Pulumi and provider SDKs.
- On ImportError, constructs an in-memory representation of the intended resources
  and writes `/mnt/data/pulumi_plan.json` and prints guidance.
- When Pulumi is present, it performs the same resource definitions as before.

Notes:
- This script does not attempt to fully emulate AWS — it only records the arguments
  passed when resources would be created, which is useful for debugging in CI/sandboxes.
- To run for real, ensure `pulumi`, `pulumi-aws`, `pulumi-awsx`, `pulumi-eks`, and
  `pulumi-kubernetes` are installed in your Python environment (e.g. pip install pulumi).

"""

import json
import os
import sys
from typing import Any, Dict, List

# Attempt to import Pulumi and provider packages. If unavailable, we switch to
# a local dry-run plan mode to avoid ModuleNotFoundError in sandboxed environments.
PULUMI_AVAILABLE = True
try:
    import pulumi
    from pulumi import Config, Output
    import pulumi_aws as aws
    import pulumi_awsx as awsx
    import pulumi_eks as eks
    import pulumi_kubernetes as k8s
except Exception as e:
    PULUMI_AVAILABLE = False
    _import_error = e

# Common metadata for the plan output
_plan: Dict[str, Any] = {
    "meta": {
        "mode": "pulumi" if PULUMI_AVAILABLE else "dry-run",
        "message": "Pulumi SDK available"
        if PULUMI_AVAILABLE
        else "Pulumi SDK not available; producing dry-run plan",
    },
    "resources": [],
}


# Helper to record intended resources in dry-run mode
def record_resource(kind: str, name: str, args: Dict[str, Any]):
    _plan["resources"].append({"kind": kind, "name": name, "args": args})


# Utility to safely extract simple-serializable values
def simpleify(obj):
    try:
        return json.loads(json.dumps(obj, default=str))
    except Exception:
        return str(obj)


# If Pulumi not available — build a declarative plan and write it to disk
if not PULUMI_AVAILABLE:
    # Build the same high-level plan as the original program would create
    aws_region = os.environ.get("AWS_REGION", "us-east-1")

    record_resource("ProviderConfig", "aws:region", {"region": aws_region})

    # VPC
    record_resource(
        "awsx.ec2.Vpc", "ecom-vpc", {"cidr_block": "10.0.0.0/16", "number_of_availability_zones": 2}
    )

    # EKS
    record_resource(
        "eks.Cluster",
        "frontend-eks",
        {"instance_type": "t3.medium", "desired_capacity": 2, "min_size": 1, "max_size": 3},
    )

    # ECS cluster
    record_resource("aws.ecs.Cluster", "order-ecs-cluster", {})

    # ECS task + instana sidecar
    record_resource(
        "aws.iam.Role",
        "ecsTaskExecutionRole",
        {"assume_role_policy": "sts:AssumeRole for ecs-tasks.amazonaws.com"},
    )
    record_resource("aws.cloudwatch.LogGroup", "ecs-log-group", {"retention_in_days": 14})
    record_resource(
        "aws.ecs.TaskDefinition",
        "order-task",
        {
            "family": "order-task-family",
            "cpu": "512",
            "memory": "1024",
            "network_mode": "awsvpc",
            "requires_compatibilities": ["FARGATE"],
            "containers": [
                {
                    "name": "order-service",
                    "image": "amazon/amazon-ecs-sample",
                    "portMappings": [{"containerPort": 8080}],
                },
                {
                    "name": "instana-agent",
                    "image": "instana/agent:latest",
                    "env": ["INSTANA_AGENT_KEY", "INSTANA_ENDPOINT"],
                },
            ],
        },
    )

    # Aurora
    record_resource(
        "aws.rds.SubnetGroup",
        "aurora-subnet-group",
        {"subnet_ids": ["private-subnet-1", "private-subnet-2"]},
    )
    record_resource(
        "aws.rds.Cluster",
        "aurora-cluster",
        {"engine": "aurora-mysql", "engine_mode": "provisioned"},
    )
    record_resource(
        "aws.rds.ClusterInstance", "aurora-instance-1", {"instance_class": "db.r5.large"}
    )

    # DynamoDB
    record_resource(
        "aws.dynamodb.Table",
        "session-table",
        {"attributes": [{"name": "sessionId", "type": "S"}], "billing_mode": "PAY_PER_REQUEST"},
    )

    # S3
    record_resource("aws.s3.Bucket", "assets-bucket", {"acl": "private"})

    # SQS
    record_resource("aws.sqs.Queue", "order-queue", {"visibility_timeout_seconds": 30})

    # MSK
    record_resource("aws.ec2.SecurityGroup", "msk-sg", {"description": "MSK SG"})
    record_resource(
        "aws.msk.Cluster", "msk-cluster", {"kafka_version": "2.8.1", "number_of_broker_nodes": 3}
    )

    # Instana on EKS — DaemonSet
    record_resource("k8s.core.v1.Namespace", "instana", {})
    record_resource(
        "k8s.apps.v1.DaemonSet",
        "instana-agent",
        {"image": "instana/agent:latest", "mounts": ["/proc", "/sys"]},
    )

    # ROSA placeholder
    record_resource(
        "note",
        "rosa-placeholder",
        {
            "instructions": "Use rosa CLI to provision ROSA cluster and apply daemonset with kubeconfig"
        },
    )

    # Write plan to file
    out_path = "/mnt/data/pulumi_plan.json"
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(_plan, f, indent=2)
        print("\n=== Pulumi SDK NOT FOUND — dry-run plan written to:\n  {}\n".format(out_path))
        print("Import error was: {}\n".format(simpleify(_import_error)))
        print(
            "Open the JSON file to inspect the intended resources. To run for real, install Pulumi and providers:"
        )
        print("  pip install pulumi pulumi-aws pulumi-awsx pulumi-eks pulumi-kubernetes")
        print(
            "\nNote: This script will *not* attempt to create cloud resources because Pulumi is unavailable in the current environment."
        )
    except Exception as write_err:
        print("Failed to write plan file: {}".format(write_err))
        print("Original import error: {}".format(simpleify(_import_error)))

# If Pulumi is available, run the real Pulumi program.
if PULUMI_AVAILABLE:
    config = Config()
    aws_region = config.get("aws:region") or "us-east-1"
    instana_agent_key = config.require_secret("instana:agentKey")
    instana_endpoint = config.get("instana:endpoint") or "https://saas-us-east-1.instana.io"

    # 1) VPC
    vpc = awsx.ec2.Vpc("ecom-vpc", cidr_block="10.0.0.0/16", number_of_availability_zones=2)

    # 2) EKS for frontend
    eks_cluster = eks.Cluster(
        "frontend-eks",
        vpc_id=vpc.vpc_id,
        subnet_ids=vpc.public_subnet_ids + vpc.private_subnet_ids,
        instance_type="t3.medium",
        desired_capacity=2,
        min_size=1,
        max_size=3,
    )

    k8s_provider = k8s.Provider("eks-k8s", kubeconfig=eks_cluster.kubeconfig)

    # 3) ECS for order processing (Fargate)
    ecs_cluster = aws.ecs.Cluster("order-ecs-cluster")

    # Example IAM role for task execution
    execution_role = aws.iam.Role(
        "ecsTaskExecutionRole",
        assume_role_policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                        "Effect": "Allow",
                        "Sid": "",
                    }
                ],
            }
        ),
    )

    aws.iam.RolePolicyAttachment(
        "ecsExecPolicyAttach",
        role=execution_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
    )

    # CloudWatch log group for ECS tasks
    ecs_log_group = aws.cloudwatch.LogGroup("ecs-log-group", retention_in_days=14)

    # Task definition with an example instana sidecar container (image and envs may vary)
    task_def = aws.ecs.TaskDefinition(
        "order-task",
        family="order-task-family",
        cpu="512",
        memory="1024",
        network_mode="awsvpc",
        requires_compatibilities=["FARGATE"],
        execution_role_arn=execution_role.arn,
        container_definitions=pulumi.Output.all(instana_agent_key).apply(
            lambda args: json.dumps(
                [
                    {
                        "name": "order-service",
                        "image": "amazon/amazon-ecs-sample",
                        "essential": True,
                        "portMappings": [{"containerPort": 8080, "protocol": "tcp"}],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": ecs_log_group.name,
                                "awslogs-region": aws_region,
                                "awslogs-stream-prefix": "order",
                            },
                        },
                    },
                    {
                        "name": "instana-agent",
                        "image": "instana/agent:latest",
                        "essential": False,
                        "environment": [
                            {"name": "INSTANA_AGENT_KEY", "value": args[0]},
                            {"name": "INSTANA_ENDPOINT", "value": instana_endpoint},
                        ],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": ecs_log_group.name,
                                "awslogs-region": aws_region,
                                "awslogs-stream-prefix": "instana",
                            },
                        },
                    },
                ]
            )
        ),
    )

    # 4) Aurora (MySQL) for relational data
    subnet_group = aws.rds.SubnetGroup("aurora-subnet-group", subnet_ids=vpc.private_subnet_ids)

    aurora_cluster = aws.rds.Cluster(
        "aurora-cluster",
        engine="aurora-mysql",
        engine_mode="provisioned",
        master_username="admin",
        master_password=config.require_secret("db:password"),
        db_subnet_group_name=subnet_group.id,
    )

    # at least one instance
    aurora_instance = aws.rds.ClusterInstance(
        "aurora-instance-1", cluster_identifier=aurora_cluster.id, instance_class="db.r5.large"
    )

    # 5) DynamoDB for session storage
    db_table = aws.dynamodb.Table(
        "session-table",
        attributes=[{"name": "sessionId", "type": "S"}],
        hash_key="sessionId",
        billing_mode="PAY_PER_REQUEST",
    )

    # 6) S3 bucket for static assets
    assets_bucket = aws.s3.Bucket("assets-bucket", acl="private")

    # 7) SQS for order queue
    order_queue = aws.sqs.Queue("order-queue", visibility_timeout_seconds=30)

    # 8) MSK (Kafka) for real-time streaming
    msk_subnets = vpc.private_subnet_ids
    msk_security_group = aws.ec2.SecurityGroup("msk-sg", vpc_id=vpc.vpc_id, description="MSK SG")

    msk_cluster = aws.msk.Cluster(
        "msk-cluster",
        cluster_name="ecom-msk",
        kafka_version="2.8.1",
        number_of_broker_nodes=3,
        broker_node_group_info={
            "instance_type": "kafka.m5.large",
            "client_subnets": msk_subnets,
            "security_groups": [msk_security_group.id],
        },
    )

    # 9) CloudWatch log group for Instana (and any custom logs)
    instana_log_group = aws.cloudwatch.LogGroup("instana-log-group", retention_in_days=14)

    # 10) Instana agent on EKS — DaemonSet manifest (example)
    instana_namespace = k8s.core.v1.Namespace(
        "instana", metadata={"name": "instana"}, opts=pulumi.ResourceOptions(provider=k8s_provider)
    )

    instana_daemonset_manifest = {
        "apiVersion": "apps/v1",
        "kind": "DaemonSet",
        "metadata": {"name": "instana-agent", "namespace": "instana"},
        "spec": {
            "selector": {"matchLabels": {"name": "instana-agent"}},
            "template": {
                "metadata": {"labels": {"name": "instana-agent"}},
                "spec": {
                    "containers": [
                        {
                            "name": "instana-agent",
                            "image": "instana/agent:latest",
                            "env": [
                                {
                                    "name": "INSTANA_AGENT_KEY",
                                    "valueFrom": {
                                        "secretKeyRef": {
                                            "name": "instana-agent-secret",
                                            "key": "agentKey",
                                        }
                                    },
                                },
                                {"name": "INSTANA_ENDPOINT", "value": instana_endpoint},
                            ],
                            "volumeMounts": [
                                {"name": "proc", "mountPath": "/host/proc", "readOnly": True},
                                {"name": "sys", "mountPath": "/host/sys", "readOnly": True},
                            ],
                        }
                    ],
                    "volumes": [
                        {"name": "proc", "hostPath": {"path": "/proc"}},
                        {"name": "sys", "hostPath": {"path": "/sys"}},
                    ],
                },
            },
        },
    }

    # Secret for Instana agent key in Kubernetes
    instana_secret = k8s.core.v1.Secret(
        "instana-agent-secret",
        metadata={"namespace": instana_namespace.metadata["name"]},
        string_data={
            "agentKey": instana_agent_key.apply(lambda k: k if isinstance(k, str) else str(k))
        },
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    instana_daemonset = k8s.apps.v1.DaemonSet(
        "instana-agent-ds",
        metadata={"namespace": instana_namespace.metadata["name"]},
        spec=instana_daemonset_manifest["spec"],
        opts=pulumi.ResourceOptions(provider=k8s_provider),
    )

    # 11) Placeholder: ROSA (OpenShift) — instructions & manifest snapshot
    pulumi.export(
        "notes",
        """
    ROSA placeholder: create an OpenShift cluster (ROSA) using the rosa CLI / RH API. After you have a kubeconfig for ROSA, create a k8s.Provider with that kubeconfig and apply the same Instana DaemonSet/Secret.
    E.g.:
    rosa create cluster --cluster-name ecom-openshift --sts
    export KUBECONFIG=~/.kube/rosa-ecom-config
    pulumi config set rosa:kubeconfig --secret "$(cat ~/.kube/rosa-ecom-config)"

    Then in Pulumi: create a k8s.Provider using that kubeconfig and apply the Instana resources into the 'openshift-monitoring' or custom namespace.
    """,
    )

    # Exports
    pulumi.export("vpc_id", vpc.vpc_id)
    pulumi.export("eks_cluster_name", eks_cluster.core.cluster.name)
    pulumi.export("ecs_cluster_name", ecs_cluster.name)
    pulumi.export("aurora_cluster_endpoint", aurora_cluster.endpoint)
    pulumi.export("s3_bucket", assets_bucket.id)
    pulumi.export("order_queue_url", order_queue.id)
    pulumi.export("msk_cluster_arn", msk_cluster.arn)

else:
    # Pulumi is not present — friendly runtime message for users/tests.
    print(
        "\nPulumi SDK is not available in this environment. The dry-run plan was written to /mnt/data/pulumi_plan.json (if writing succeeded)."
    )
    print(
        "This module will not attempt to create cloud resources. To run for real, install Pulumi and the required providers:"
    )
    print("  pip install pulumi pulumi-aws pulumi-awsx pulumi-eks pulumi-kubernetes")

# End of script
