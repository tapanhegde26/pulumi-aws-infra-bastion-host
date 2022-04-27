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

config = pulumi.Config()
data = config.require_object("data")

virtualprivatecloud = aws.ec2.Vpc(data.get("vpc_name"), cidr_block=data.get("vpc_cidr"))

igw = aws.ec2.InternetGateway(data.get("igw_name"),
    vpc_id=virtualprivatecloud.id,
    tags={
        "Name": data.get("igw_name"),
    })

privatesubnet = aws.ec2.Subnet(data.get("prv_subnet_name"),
    vpc_id=virtualprivatecloud.id,
    cidr_block=data.get("prv_cidr"),
    map_public_ip_on_launch=False,
    tags={
        "Name": data.get("prv_subnet_name"),
    })

publicsubnet = aws.ec2.Subnet(data.get("pub_subnet_name"),
    vpc_id=virtualprivatecloud.id,
    cidr_block=data.get("pub_cidr"),
    map_public_ip_on_launch=True,
    tags={
        "Name": data.get("pub_subnet_name"),
    })

eip = aws.ec2.Eip(data.get("eip_name"),
    vpc=True)

natgateway = aws.ec2.NatGateway(data.get("natgw_name"),
    allocation_id=eip.allocation_id,
    subnet_id=publicsubnet.id,
    tags={
        "Name": data.get("natgw_name"),
    },
    opts=pulumi.ResourceOptions(depends_on=[igw]))

pubroutetable = aws.ec2.RouteTable(data.get("pubrttable_name"),
    vpc_id=virtualprivatecloud.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        )
    ],
    tags={
        "Name": data.get("pubrttable_name"),
    })

prvroutetable = aws.ec2.RouteTable(data.get("prvrttable_name"),
    vpc_id=virtualprivatecloud.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=natgateway.id,
        )
    ],
    tags={
        "Name": data.get("prvrttable_name"),
    })

pub_route_association = aws.ec2.RouteTableAssociation(
        data.get("pubrtasst_name"),
        route_table_id=pubroutetable.id,
        subnet_id=publicsubnet.id
)

prv_route_association = aws.ec2.RouteTableAssociation(
        data.get("prvrtasst_name"),
        route_table_id=prvroutetable.id,
        subnet_id=privatesubnet.id
)

sg = aws.ec2.SecurityGroup(
        data.get("sec_grp_name"),
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

keypair = aws.ec2.KeyPair("keypair", public_key=data.get("public_key"))

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
        data.get("ec2_bastion_name"),
        instance_type=data.get("ec2_bastion_type"),
        vpc_security_group_ids=[sg.id],
        ami=ami.id,
        key_name=keypair.key_name,
        user_data=user_data,
        subnet_id=publicsubnet.id,
        associate_public_ip_address=True,
)


private_ec2_instance = aws.ec2.Instance(
        data.get("ec2_private_name"),
        instance_type=data.get("ec2_private_type"),
        vpc_security_group_ids=[sg.id],
        ami=ami.id,
        key_name=keypair.key_name,
        subnet_id=privatesubnet.id,
)

# export("ec2-public-ip", ec2_instance.public_ip)

