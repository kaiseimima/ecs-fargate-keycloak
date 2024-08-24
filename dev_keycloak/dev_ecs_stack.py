from constructs import Construct
from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecs as ecs,
    CfnOutput, Duration, Stack
)

class DevEcsStack(Stack):

    def __init__(self, scope: Construct, id: str, vpc: ec2.Vpc, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        cluster = ecs.Cluster(
            self, 
            'ecs-cluster',
            vpc=vpc
        )

        