"""
AWS RDS Clusters deployment using Pulumi
Creates Aurora MySQL and PostgreSQL clusters with proper security and networking
"""

import pulumi
import pulumi_aws as aws
import random
import string

# Generate random suffix for unique naming
def generate_random_suffix(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

random_suffix = generate_random_suffix()

# Get default VPC
default_vpc = aws.ec2.get_vpc(default=True)

# Get default subnets
default_subnets = aws.ec2.get_subnets(
    filters=[
        aws.ec2.GetSubnetsFilterArgs(
            name="vpc-id",
            values=[default_vpc.id]
        )
    ]
)

# Create DB subnet group for clusters
cluster_subnet_group = aws.rds.SubnetGroup(
    f"aurora-subnet-group-{random_suffix}",
    subnet_ids=default_subnets.ids,
    tags={
        "Name": f"aurora-subnet-group-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-clusters"
    }
)

# Create security group for Aurora clusters
aurora_security_group = aws.ec2.SecurityGroup(
    f"aurora-sg-{random_suffix}",
    description="Security group for Aurora clusters",
    vpc_id=default_vpc.id,
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            description="MySQL/Aurora",
            from_port=3306,
            to_port=3306,
            protocol="tcp",
            cidr_blocks=["10.0.0.0/8"]
        ),
        aws.ec2.SecurityGroupIngressArgs(
            description="PostgreSQL",
            from_port=5432,
            to_port=5432,
            protocol="tcp",
            cidr_blocks=["10.0.0.0/8"]
        )
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            from_port=0,
            to_port=0,
            protocol="-1",
            cidr_blocks=["0.0.0.0/0"]
        )
    ],
    tags={
        "Name": f"aurora-sg-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-clusters"
    }
)

# Create Aurora MySQL cluster
aurora_mysql_cluster = aws.rds.Cluster(
    f"aurora-mysql-{random_suffix}",
    cluster_identifier=f"aurora-mysql-{random_suffix}",
    engine="aurora-mysql",
    engine_version="8.0.mysql_aurora.3.05.2",
    engine_mode="provisioned",
    
    database_name="testdb",
    master_username="admin",
    master_password="changeme123!",
    
    vpc_security_group_ids=[aurora_security_group.id],
    db_subnet_group_name=cluster_subnet_group.name,
    
    backup_retention_period=7,
    preferred_backup_window="03:00-04:00",
    preferred_maintenance_window="sun:04:00-sun:05:00",
    
    storage_encrypted=True,
    skip_final_snapshot=True,
    deletion_protection=False,
    
    tags={
        "Name": f"aurora-mysql-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-clusters",
        "Engine": "aurora-mysql"
    }
)

# Create Aurora MySQL cluster instances
aurora_mysql_instance_1 = aws.rds.ClusterInstance(
    f"aurora-mysql-instance-1-{random_suffix}",
    identifier=f"aurora-mysql-instance-1-{random_suffix}",
    cluster_identifier=aurora_mysql_cluster.id,
    instance_class="db.t3.small",
    engine=aurora_mysql_cluster.engine,
    engine_version=aurora_mysql_cluster.engine_version,
    
    tags={
        "Name": f"aurora-mysql-instance-1-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-clusters"
    }
)

# Create Aurora PostgreSQL cluster
aurora_postgres_cluster = aws.rds.Cluster(
    f"aurora-postgres-{random_suffix}",
    cluster_identifier=f"aurora-postgres-{random_suffix}",
    engine="aurora-postgresql",
    engine_version="15.4",
    engine_mode="provisioned",
    
    database_name="testdb",
    master_username="postgres",
    master_password="changeme123!",
    
    vpc_security_group_ids=[aurora_security_group.id],
    db_subnet_group_name=cluster_subnet_group.name,
    
    backup_retention_period=7,
    preferred_backup_window="03:00-04:00",
    preferred_maintenance_window="sun:04:00-sun:05:00",
    
    storage_encrypted=True,
    skip_final_snapshot=True,
    deletion_protection=False,
    
    tags={
        "Name": f"aurora-postgres-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-clusters",
        "Engine": "aurora-postgresql"
    }
)

# Create Aurora PostgreSQL cluster instances
aurora_postgres_instance_1 = aws.rds.ClusterInstance(
    f"aurora-postgres-instance-1-{random_suffix}",
    identifier=f"aurora-postgres-instance-1-{random_suffix}",
    cluster_identifier=aurora_postgres_cluster.id,
    instance_class="db.t3.small",
    engine=aurora_postgres_cluster.engine,
    engine_version=aurora_postgres_cluster.engine_version,
    
    tags={
        "Name": f"aurora-postgres-instance-1-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-clusters"
    }
)

# Export important values
pulumi.export("aurora_mysql_cluster_endpoint", aurora_mysql_cluster.endpoint)
pulumi.export("aurora_mysql_cluster_reader_endpoint", aurora_mysql_cluster.reader_endpoint)
pulumi.export("aurora_mysql_cluster_port", aurora_mysql_cluster.port)
pulumi.export("aurora_mysql_database_name", aurora_mysql_cluster.database_name)
pulumi.export("aurora_mysql_master_username", aurora_mysql_cluster.master_username)

pulumi.export("aurora_postgres_cluster_endpoint", aurora_postgres_cluster.endpoint)
pulumi.export("aurora_postgres_cluster_reader_endpoint", aurora_postgres_cluster.reader_endpoint)
pulumi.export("aurora_postgres_cluster_port", aurora_postgres_cluster.port)
pulumi.export("aurora_postgres_database_name", aurora_postgres_cluster.database_name)
pulumi.export("aurora_postgres_master_username", aurora_postgres_cluster.master_username)

pulumi.export("cluster_subnet_group_name", cluster_subnet_group.name)
pulumi.export("aurora_security_group_id", aurora_security_group.id)
pulumi.export("random_suffix", random_suffix)

# Connection strings (without passwords for security)
pulumi.export("aurora_mysql_connection_string", pulumi.Output.concat(
    "mysql://admin@",
    aurora_mysql_cluster.endpoint,
    "/testdb"
))

pulumi.export("aurora_postgres_connection_string", pulumi.Output.concat(
    "postgresql://postgres@",
    aurora_postgres_cluster.endpoint,
    "/testdb"
))

# Cluster information
pulumi.export("aurora_mysql_cluster_id", aurora_mysql_cluster.id)
pulumi.export("aurora_postgres_cluster_id", aurora_postgres_cluster.id)
pulumi.export("aurora_mysql_instance_id", aurora_mysql_instance_1.id)
pulumi.export("aurora_postgres_instance_id", aurora_postgres_instance_1.id)