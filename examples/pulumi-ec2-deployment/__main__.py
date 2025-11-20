"""Minimal EC2 instance"""
import pulumi
import pulumi_aws as aws

# Configuration
config = pulumi.Config()
vpc_id = config.get("vpc_id")  # Optional: specify existing VPC ID

# Get VPC and subnet
if vpc_id:
    # Use specified VPC
    subnets = aws.ec2.get_subnets(filters=[{"name": "vpc-id", "values": [vpc_id]}])
    subnet_id = subnets.ids[0]
else:
    # Try to find any existing VPC
    try:
        vpc = aws.ec2.get_vpc(default=True)
        vpc_id = vpc.id
    except:
        vpcs = aws.ec2.get_vpcs()
        if len(vpcs.ids) > 0:
            vpc_id = vpcs.ids[0]
        else:
            raise Exception("No VPC found. Please create a VPC first or specify vpc_id in config.")
    
    subnets = aws.ec2.get_subnets(filters=[{"name": "vpc-id", "values": [vpc_id]}])
    subnet_id = subnets.ids[0]

# Security group for SSH
sg = aws.ec2.SecurityGroup("sg",
    vpc_id=vpc_id,
    ingress=[aws.ec2.SecurityGroupIngressArgs(
        protocol="tcp", from_port=22, to_port=22, cidr_blocks=["0.0.0.0/0"])],
    egress=[aws.ec2.SecurityGroupEgressArgs(
        protocol="-1", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"])])

# Get latest Amazon Linux 2 AMI
ami = aws.ec2.get_ami(most_recent=True, owners=["amazon"],
    filters=[aws.ec2.GetAmiFilterArgs(name="name", values=["amzn2-ami-hvm-*-x86_64-gp2"])])

# EC2 instance
instance = aws.ec2.Instance("instance",
    instance_type="t2.micro",
    ami=ami.id,
    subnet_id=subnet_id,
    vpc_security_group_ids=[sg.id],
    associate_public_ip_address=True)

pulumi.export("instance_id", instance.id)
pulumi.export("public_ip", instance.public_ip)
