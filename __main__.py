"""An AWS Python Pulumi program"""

# import pulumi
# from pulumi_aws import s3
#
# # Create an AWS resource (S3 Bucket)
# bucket = s3.Bucket('my-bucket')
#
# # Export the name of the bucket
# pulumi.export('bucket_name', bucket.id)

import pulumi
import pulumi_aws as aws
from pulumi import export

virtualprivatecloud = aws.ec2.Vpc("ec2-vpc", cidr_block="10.0.0.0/16")

igw = aws.ec2.InternetGateway("igw",
    vpc_id=virtualprivatecloud.id,
    tags={
        "Name": "igw",
    })

privatesubnet = aws.ec2.Subnet("private-subnet",
    vpc_id=virtualprivatecloud.id,
    cidr_block="10.0.1.0/24",
    map_public_ip_on_launch=False,
    tags={
        "Name": "private-subnet",
    })

publicsubnet = aws.ec2.Subnet("public-subnet",
    vpc_id=virtualprivatecloud.id,
    cidr_block="10.0.0.0/24",
    map_public_ip_on_launch=True,
    tags={
        "Name": "public-subnet",
    })

eip = aws.ec2.Eip("lb",
    vpc=True)

natgateway = aws.ec2.NatGateway("ngw",
    allocation_id=eip.allocation_id,
    subnet_id=publicsubnet.id,
    tags={
        "Name": "gw NAT",
    },
    opts=pulumi.ResourceOptions(depends_on=[igw]))

pubroutetable = aws.ec2.RouteTable("pubroutetable",
    vpc_id=virtualprivatecloud.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        )
    ],
    tags={
        "Name": "pub-routetable",
    })

prvroutetable = aws.ec2.RouteTable("prvroutetable",
    vpc_id=virtualprivatecloud.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=natgateway.id,
        )
    ],
    tags={
        "Name": "prv-routetable",
    })

pub_route_association = aws.ec2.RouteTableAssociation(
        "ec2-pub-rta",
        route_table_id=pubroutetable.id,
        subnet_id=publicsubnet.id
)

prv_route_association = aws.ec2.RouteTableAssociation(
        "ec2-prv-rta",
        route_table_id=prvroutetable.id,
        subnet_id=privatesubnet.id
)

sg = aws.ec2.SecurityGroup(
        "ec2-http-sg",
        description="Allow HTTP traffic to EC2 instance",
        ingress=[{
                "protocol": "tcp",
                "from_port": 80,
                "to_port": 80,
                "cidr_blocks": ["0.0.0.0/0"],
            },
        {
            "protocol": "tcp",
            "from_port": 443,
            "to_port": 443,
            "cidr_blocks": ["0.0.0.0/0"],
        },
        {
            "protocol": "tcp",
            "from_port": 22,
            "to_port": 22,
            "cidr_blocks": ["0.0.0.0/0"],
        }
        ],
    egress=[
        {
            "protocol": "-1",
            "from_port": 0,
            "to_port": 0,
            "cidr_blocks": ["0.0.0.0/0"],

        }
    ],
    vpc_id=virtualprivatecloud.id
)

keypair = aws.ec2.KeyPair("keypair", public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC9u37J5tfzmeA8INBCcFSPKnUN8GIjYFdPOOCn8AjUC5iTJX/7TWd3pZ42Z++RCIlvBvKkH7LL1pYvi0HdtsbRNtCC60sbkgXRvuXWVAX7laFwERjSrFKpPYr9KxPmKt566lD5mQXrz25Lm0Fz9tGT2F3f8NDa5XY3M525o7ws4WVpg4nGkqnUnNrxBhKSLHI+LoMzsV9WxqFFlsz2EEt8mOekFGR2JUBHrfrPVm1DRtaVl5w6GEgmvXf4i+rN+Q+7y1I7g/7uJTAiR3To1CjFothpk56PINMWQafO31Mi1+ISDUZK4jBi0VrwWcxUE16eXP2WFAugqRElbuFqjoFDYollpx6Q2GpRyM+gIYMNPsNqM/7pGVvXOe/pzJqqFo68W5ASJF3EhwFk10t6cAnZfkL/+a8BR+8QzusMjqoAxip8YtOVglWl1D1ArePComLsxmEmvfnGMgisLqZ62UpwR/bel69uph4TxDCthyxllG0i4RST0MrWv0kAT04yJJE= c5281159@C02Z34YFLVDQ")
ami = aws.ec2.get_ami(
        most_recent="true",
        owners=["099720109477"],
)


user_data = """
#!/bin/bash
echo "Hello, world!" > index.html
nohup python -m SimpleHTTPServer 80 &
"""

bastion_ec2_instance = aws.ec2.Instance(
        "ec2-bastion",
        instance_type="t2.micro",
        vpc_security_group_ids=[sg.id],
        ami=ami.id,
        key_name=keypair.key_name,
        user_data=user_data,
        subnet_id=publicsubnet.id,
        associate_public_ip_address=True,
)


private_ec2_instance = aws.ec2.Instance(
        "ec2-private",
        instance_type="t2.micro",
        vpc_security_group_ids=[sg.id],
        ami=ami.id,
        key_name=keypair.key_name,
        subnet_id=privatesubnet.id,
)

# export("ec2-public-ip", ec2_instance.public_ip)

