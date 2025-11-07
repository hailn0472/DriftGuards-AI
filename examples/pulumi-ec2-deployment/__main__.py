"""An AWS Python Pulumi program"""

import pulumi
import pulumi_aws as aws
import pulumi_tls as tls

# Create a VPC
vpc = aws.ec2.Vpc("my-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={
        "Name": "my-vpc",
    })

# Create an Internet Gateway
igw = aws.ec2.InternetGateway("my-igw",
    vpc_id=vpc.id,
    tags={
        "Name": "my-igw",
    })

# Get available availability zones
available_azs = aws.get_availability_zones(state="available")

# Create a public subnet
public_subnet = aws.ec2.Subnet("my-public-subnet",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone=available_azs.names[0],
    map_public_ip_on_launch=True,
    tags={
        "Name": "my-public-subnet",
    })

# Create a route table
route_table = aws.ec2.RouteTable("my-route-table",
    vpc_id=vpc.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        )
    ],
    tags={
        "Name": "my-route-table",
    })

# Associate the route table with the public subnet
route_table_association = aws.ec2.RouteTableAssociation("my-route-table-association",
    subnet_id=public_subnet.id,
    route_table_id=route_table.id)

# Create a security group allowing SSH and HTTP
security_group = aws.ec2.SecurityGroup("my-security-group",
    vpc_id=vpc.id,
    description="Allow SSH and HTTP",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=22,
            to_port=22,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow SSH",
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow HTTP",
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
            description="Allow all outbound",
        ),
    ],
    tags={
        "Name": "my-security-group",
    })

# Create a new TLS private key
private_key = tls.PrivateKey("my-private-key",
    algorithm="RSA",
    rsa_bits=4096)

# Create an AWS key pair using the public key
key_pair = aws.ec2.KeyPair("my-key-pair",
    public_key=private_key.public_key_openssh)

# Get the latest Amazon Linux 2 AMI
ami = aws.ec2.get_ami(
    most_recent=True,
    owners=["amazon"],
    filters=[
        aws.ec2.GetAmiFilterArgs(
            name="name",
            values=["amzn2-ami-hvm-*-x86_64-gp2"],
        ),
    ])

# Create an EC2 instance
instance = aws.ec2.Instance("my-instance",
    instance_type="t2.micro",
    ami=ami.id,
    subnet_id=public_subnet.id,
    vpc_security_group_ids=[security_group.id],
    associate_public_ip_address=True,
    key_name=key_pair.key_name,
    tags={
        "Name": "my-ec2-instance",
    })

# Export the instance's public IP and ID
pulumi.export('instance_id', instance.id)
pulumi.export('instance_public_ip', instance.public_ip)
pulumi.export('instance_public_dns', instance.public_dns)
pulumi.export('vpc_id', vpc.id)
pulumi.export('private_key_pem', pulumi.Output.secret(private_key.private_key_pem))
pulumi.export('ssh_command', pulumi.Output.concat('ssh -i ~/.ssh/my-ec2-key.pem ec2-user@', instance.public_ip))
