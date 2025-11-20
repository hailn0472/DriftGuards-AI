"""
AWS RDS Instances deployment using Pulumi
Creates RDS database instances with proper security groups and subnet groups
"""

import pulumi
import pulumi_aws as aws
import random
import string

# Generate random suffix for unique naming
def generate_random_suffix(length=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

random_suffix = generate_random_suffix()

# Try to get default VPC, if not found, get any VPC or create one
try:
    default_vpc = aws.ec2.get_vpc(default=True)
    vpc_id = default_vpc.id
except:
    # Try to get any existing VPC
    vpcs = aws.ec2.get_vpcs()
    if vpcs.ids:
        vpc_id = vpcs.ids[0]
        pulumi.log.info(f"Using existing VPC: {vpc_id}")
    else:
        # Create a new VPC if none exists
        new_vpc = aws.ec2.Vpc(
            f"rds-vpc-{random_suffix}",
            cidr_block="10.0.0.0/16",
            enable_dns_hostnames=True,
            enable_dns_support=True,
            tags={
                "Name": f"rds-vpc-{random_suffix}",
                "Environment": "dev",
                "Service": "rds-instances"
            }
        )
        vpc_id = new_vpc.id
        pulumi.log.info("Created new VPC for RDS")

# Get subnets in the VPC
try:
    subnets = aws.ec2.get_subnets(
        filters=[
            aws.ec2.GetSubnetsFilterArgs(
                name="vpc-id",
                values=[vpc_id]
            )
        ]
    )
    subnet_ids = subnets.ids
except:
    # Create subnets if none exist
    availability_zones = aws.get_availability_zones(state="available")
    
    subnet_1 = aws.ec2.Subnet(
        f"rds-subnet-1-{random_suffix}",
        vpc_id=vpc_id,
        cidr_block="10.0.1.0/24",
        availability_zone=availability_zones.names[0],
        tags={
            "Name": f"rds-subnet-1-{random_suffix}",
            "Environment": "dev"
        }
    )
    
    subnet_2 = aws.ec2.Subnet(
        f"rds-subnet-2-{random_suffix}",
        vpc_id=vpc_id,
        cidr_block="10.0.2.0/24",
        availability_zone=availability_zones.names[1] if len(availability_zones.names) > 1 else availability_zones.names[0],
        tags={
            "Name": f"rds-subnet-2-{random_suffix}",
            "Environment": "dev"
        }
    )
    
    subnet_ids = [subnet_1.id, subnet_2.id]
    pulumi.log.info("Created new subnets for RDS")

# Create DB subnet group
db_subnet_group = aws.rds.SubnetGroup(
    f"rds-subnet-group-{random_suffix}",
    subnet_ids=subnet_ids,
    tags={
        "Name": f"rds-subnet-group-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-instances"
    }
)

# Create security group for RDS
rds_security_group = aws.ec2.SecurityGroup(
    f"rds-sg-{random_suffix}",
    description="Security group for RDS instances",
    vpc_id=vpc_id,
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
        "Name": f"rds-sg-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-instances"
    }
)

# Create MySQL RDS instance
mysql_instance = aws.rds.Instance(
    f"mysql-db-{random_suffix}",
    identifier=f"mysql-db-{random_suffix}",
    engine="mysql",
    engine_version="8.0",
    instance_class="db.t3.micro",
    allocated_storage=20,
    storage_type="gp2",
    storage_encrypted=True,
    
    db_name="testdb",
    username="admin",
    password="changeme123!",
    
    vpc_security_group_ids=[rds_security_group.id],
    db_subnet_group_name=db_subnet_group.name,
    
    backup_retention_period=7,
    backup_window="03:00-04:00",
    maintenance_window="sun:04:00-sun:05:00",
    
    skip_final_snapshot=True,
    deletion_protection=False,
    
    tags={
        "Name": f"mysql-db-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-instances",
        "Engine": "mysql"
    }
)

# Create PostgreSQL RDS instance
postgres_instance = aws.rds.Instance(
    f"postgres-db-{random_suffix}",
    identifier=f"postgres-db-{random_suffix}",
    engine="postgres",
    engine_version="15",  # Use major version, AWS will use latest minor version
    instance_class="db.t3.micro",
    allocated_storage=20,
    storage_type="gp2",
    storage_encrypted=True,
    
    db_name="testdb",
    username="postgres",
    password="changeme123!",
    
    vpc_security_group_ids=[rds_security_group.id],
    db_subnet_group_name=db_subnet_group.name,
    
    backup_retention_period=7,
    backup_window="03:00-04:00",
    maintenance_window="sun:04:00-sun:05:00",
    
    skip_final_snapshot=True,
    deletion_protection=False,
    
    tags={
        "Name": f"postgres-db-{random_suffix}",
        "Environment": "dev",
        "Service": "rds-instances",
        "Engine": "postgres"
    }
)

# Export important values
pulumi.export("mysql_endpoint", mysql_instance.endpoint)
pulumi.export("mysql_port", mysql_instance.port)
pulumi.export("mysql_database_name", mysql_instance.db_name)
pulumi.export("mysql_username", mysql_instance.username)

pulumi.export("postgres_endpoint", postgres_instance.endpoint)
pulumi.export("postgres_port", postgres_instance.port)
pulumi.export("postgres_database_name", postgres_instance.db_name)
pulumi.export("postgres_username", postgres_instance.username)

pulumi.export("db_subnet_group_name", db_subnet_group.name)
pulumi.export("security_group_id", rds_security_group.id)
pulumi.export("random_suffix", random_suffix)

# Connection strings (without passwords for security)
pulumi.export("mysql_connection_string", pulumi.Output.concat(
    "mysql://admin@",
    mysql_instance.endpoint,
    "/testdb"
))

pulumi.export("postgres_connection_string", pulumi.Output.concat(
    "postgresql://postgres@",
    postgres_instance.endpoint,
    "/testdb"
))