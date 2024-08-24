from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecs as ecs,
    CfnOutput, Duration, Stack
)

class DevNetworkStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            'MyVpc',
            # cidr='10.1.0.0/16',
            ip_addresses=ec2.IpAddresses.cidr('10.1.0.0/16'),
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name='publicForEcsFargate1',
                    subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name='publicForEcsFargate2',
                    subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name='privateForRds1',
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ),
                ec2.SubnetConfiguration(
                    name='privateForRds2',
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                ),
            ]
        )

        # Create Cluster
        cluster = ecs.Cluster(
            self, 
            'ecs-cluster',
            vpc=self.vpc
        )

        # Create ALB
        self.lb = elbv2.ApplicationLoadBalancer(
            self, 
            "LB",
            vpc=self.vpc,
            internet_facing=True
        )

        listener = self.lb.add_listener(
            "PublicListner",
            port=80,
            open=True
        )

        # Attach ALB to ECS Service
        listener.add_targets(
            "ECS",
            port=80,
            targets=[service],
        )
        