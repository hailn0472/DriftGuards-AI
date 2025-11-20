"""Minimal ECS cluster deployment - Cluster only"""
import pulumi
import pulumi_aws as aws

# Configuration
config = pulumi.Config()
cluster_name = config.get("cluster_name") or "minimal-ecs"

# Create ECS cluster
cluster = aws.ecs.Cluster("cluster",
    name=cluster_name,
    settings=[aws.ecs.ClusterSettingArgs(
        name="containerInsights",
        value="enabled"
    )])

# Exports
pulumi.export("cluster_name", cluster.name)
pulumi.export("cluster_arn", cluster.arn)
