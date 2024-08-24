from constructs import Construct
from aws_cdk import (
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_rds as rds,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_ecs_patterns as ecs_patterns,
    Stack, CfnOutput, Duration
)

class DevKeycloakStack(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        """
        VPC Group
        """

        # Create a VPC
        vpc = ec2.Vpc(
            self, "MyVpc",
            max_azs=2,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                )
            ]
        )

        """
        Security Group
        """

        # Create a Security Group for ECS tasks
        ecs_security_group = ec2.SecurityGroup(
            self, "EcsSecurityGroup",
            vpc=vpc,
            description="Allow traffic for ECS tasks",
            allow_all_outbound=True
        )

        ecs_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(3306),
            description="Allow ECS tasks to connect to RDS"
        )
        ecs_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(8080),
            description="Allow ECS tasks to receive traffic from ALB"
        )
        ecs_security_group.add_ingress_rule(
            peer=ecs_security_group,
            connection=ec2.Port.tcp(7800),
            description="Allow ECS tasks to communicate with other tasks on port 7800"
        )

        # Create a Security Group for ALB
        alb_security_group = ec2.SecurityGroup(
            self, "AlbSecurityGropu",
            vpc=vpc,
            description="Allow HTTP/HTTPS traffic to ALB",
            allow_all_outbound=True
        )

        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow HTTP traffic to ALB"
        )
        alb_security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS traffic to ALB"
        )


        """
        ECS-FARGATE Group
        """


        # Create a cluster
        cluster = ecs.Cluster(
            self, 'ecs-fargate-keycloak-Cluster',
            vpc=vpc
        )

        task_role = iam.Role(
            self, 'ecs-fargate-keycloak-EcsTaskRole',
            assumed_by = iam.ServicePrincipal('ecs-tasks.amazonaws.com').with_conditions({
                "StringEquals":{
                    "aws:SourceAccount":Stack.of(self).account
                },
                "ArnLike":{
                    "aws:SourceArn":"arn:aws:ecs:" + Stack.of(self).region + ":" + Stack.of(self).account + ":*"
                },
            }),
        )

        # コンテナ用のロール
        task_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('AmazonS3FullAccess')
        )

        # クラスタ用のロール
        task_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name('service-role/AmazonECSTaskExecutionRolePolicy')
        )

        # task_role.attach_inline_policy(
        # )

        task_definition = ecs.FargateTaskDefinition(
            self, 'FargateTaskDef',
            task_role=task_role,
        )

        keycloak_port_mapping = ecs.PortMapping(
            container_port=8080,
            protocol=ecs.Protocol.TCP,
        )

        s3_port_mapping = ecs.PortMapping(
            container_port=7800,
        )

        container = ecs.ContainerDefinition(
            self, 'ecs-fargate-keycloak-container',
            task_definition=task_definition,
            image=ecs.ContainerImage.from_registry('878518084785.dkr.ecr.us-east-1.amazonaws.com/keycloak-aws'),
            environment={
                "KC_DB_URL": "jdbc:mysql://keycloak.ap-northeast-1.rds.amazonaws.com/keycloak",
                "KEYCLOAK_ADMIN": "admin",
                "KEYCLOAK_ADMIN_PASSWORD": "admin",
                "KC_DB_VENDOR": "mysql",
                "KC_DB_USERNAME": "dbuser",
                "KC_DB_PASSWORD": "dbpass",
                "KC_DB_DATABASE": "keycloak",
                "KC_ADMIN_HOSTNAME": "auth.example.com",
                "KC_PROXY": "edge",
                "KC_HOSTNAME_STRICT_BACKCHANNEL": "true",
                "KC_HTTP_PORT": "8080",
                "KC_HTTP_ENABLED": "true",
                "JAVA_OPTS_APPEND": "-Djgroups.dns.query=myapplication.tutorial",
                "KC_HOSTNAME_STRICT_HTTPS": "false",
                "KC_DB_URL_PORT": "3306",
                "KC_CACHE_STACK": "kubernetes",
                "KC_HEALTH_ENABLED": "true",
                "KC_CACHE": "ispn",
                "KC_HOSTNAME": "www.example.com"
            }
        )

        container.add_port_mappings(keycloak_port_mapping)
        container.add_port_mappings(s3_port_mapping)

        # Create Fargate Service
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "FargateService",
            cluster=cluster,
            task_definition=task_definition,
            task_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            public_load_balancer=True,
            security_groups=[ecs_security_group, alb_security_group],
            enable_execute_command=True,
            enable_ecs_managed_tags=True,
        )

        # fargate_service.service.connections.security_groups[0].add_ingress_rule(
        #     peer = ec2.Peer.ipv4(vpc.vpc_cidr_blocke),
        #     connections = ec2.Port.tcp(80),
        #     description="Allow http imbound from VPC"
        # )

        # Setup AutoScaling policy
        scaling = fargate_service.service.auto_scale_task_count(
            max_capacity=2
        )

        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=50,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )


        """
        RDS Group
        """

        # Create an RDS (Aurora MySQL) instance
        db_security_group = ec2.SecurityGroup(
            self, "DbSecurityGroup",
            vpc=vpc,
            description="Allow traffic to RDS from ECS tasks",
            allow_all_outbound=True
        )

        rds_instance = rds.DatabaseCluster(
            self, "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_mysql(version=rds.AuroraMysqlEngineVersion.VER_3_03_0),
            default_database_name="keycloak",
            instances=2,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[db_security_group],
            instance_props=rds.InstanceProps(
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MEDIUM
                    )
            )
            # instance_props=rds.InstanceProps(
            #     instance_type=ec2.InstanceType.of(
            #         ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MEDIUM
            #     ),
            #     vpc=vpc,
            #     vpc_subnets=ec2.SubnetSelection(
            #         subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            #     )
            # )
        )

        # Allow traffic from ECS tasks to RDS on port 3306
        db_security_group.add_ingress_rule(
            peer=ecs_security_group,
            connection=ec2.Port.tcp(3306),
            description="Allow ECS tasks to connect to RDS"
        )

        CfnOutput(
            self, "LoadBalancerDNS",
            value=fargate_service.load_balancer.load_balancer_dns_name
        )