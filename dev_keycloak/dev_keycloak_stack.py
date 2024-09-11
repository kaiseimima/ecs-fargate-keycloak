from constructs import Construct
from aws_cdk import (
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_rds as rds,
    aws_logs as logs,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    aws_ecs_patterns as ecs_patterns,
    App, Stack, CfnOutput, Duration
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
            ip_addresses=ec2.IpAddresses.cidr('10.1.0.0/16'),
            max_azs=2
        )

        cluster = ecs.Cluster(
            self, 
            "KeycloakCluster", 
            vpc=vpc
            )

        """
        Security Group
        """

        # セキュリティグループ
        sg = ec2.SecurityGroup(self, "KeycloakSecurityGroup", vpc=vpc)
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80))  # ALBへのアクセス
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443))  # ALBのHTTPSアクセス
        sg.add_ingress_rule(sg, ec2.Port.tcp(7800))  # コンテナ間通信（S3_PING用）
        sg.add_ingress_rule(sg, ec2.Port.tcp(3306))  # RDS MySQLアクセス

        # RDS（Aurora）設定
        db_secret = secretsmanager.Secret(self, "DBSecret",  # データベース接続情報をSecrets Managerに保存
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                include_space=False,
                secret_string_template='{"username":"keycloak_user"}',
                generate_string_key="password"
            )
        )

        rds_subnet_group = rds.SubnetGroup(self, "RDSSubnetGroup",
            vpc=vpc,
            description="Private subnets for RDS",
            subnet_group_name="rds-subnet-group",
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        )

        db_instance = rds.DatabaseCluster(self, "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_mysql(version=rds.AuroraMysqlEngineVersion.VER_3_04_0),
            credentials=rds.Credentials.from_secret(db_secret),
            instance_props={
                "vpc": vpc,
                "security_groups": [sg],
                "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            },
            instances=2,  # 高可用性のために2つのRDSインスタンスを作成
            default_database_name="keycloakdb"
        )

        """
        ECS-FARGATE Group
        """

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

        # ECSタスクの実行ロールを作成
        execution_role = iam.Role(
            self, "ExecutionRole",
            assumed_by = iam.ServicePrincipal("ecs-tasks.amazonaws.com")
        )
        # ECRからコンテナイメージをプルするための権限を追加
        execution_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
        )

        task_definition = ecs.FargateTaskDefinition(
            self, 'FargateTaskDef',
            task_role=task_role,
            execution_role=execution_role
        )

        keycloak_port_mapping = ecs.PortMapping(
            container_port=8080,
        )

        s3_port_mapping = ecs.PortMapping(
            container_port=7800,
        )

        container = ecs.ContainerDefinition(
            self, 'ecs-fargate-keycloak-container',
            task_definition=task_definition,
            image=ecs.ContainerImage.from_registry('878518084785.dkr.ecr.us-east-1.amazonaws.com/keycloak-aws:latest'),
            environment={
                "KC_DB_URL": "jdbc:mysql://keycloak.ap-northeast-1.rds.amazonaws.com/keycloak",
                "KEYCLOAK_ADMIN": "admin",
                "KEYCLOAK_ADMIN_PASSWORD": "admin",
                "KC_DB_VENDOR": "mysql",
                "KC_DB_USERNAME": "dbuser",
                "KC_DB_PASSWORD": "dbpass",
                "KC_DB_DATABASE": "keycloak",
                "KC_ADMIN_HOSTNAME": "auth.mima.com",
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
                "KC_HOSTNAME": "www.mima.com"
            }
        )

        container.add_port_mappings(keycloak_port_mapping)
        container.add_port_mappings(s3_port_mapping)

        # Create Fargate Service
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "KeycloakFargateService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=2,  # 高可用性とローリングアップデートのための設定
            public_load_balancer=True
        )
        

        # fargate_service.service.connections.security_groups[0].add_ingress_rule(
        #     peer = ec2.Peer.ipv4(vpc.vpc_cidr_blocke),
        #     connections = ec2.Port.tcp(80),
        #     description="Allow http imbound from VPC"
        # )

        # ローリングアップデート用のオートスケーリングポリシー
        scalable_target = fargate_service.service.auto_scale_task_count(
            min_capacity=2,
            max_capacity=10,
        )
        scalable_target.scale_on_cpu_utilization("CpuScaling", target_utilization_percent=50)
        scalable_target.scale_on_memory_utilization("MemoryScaling", target_utilization_percent=50)


        """
        RDS Group
        """

        # Create an RDS (Aurora MySQL) instance
        # db_security_group = ec2.SecurityGroup(
        #     self, "DbSecurityGroup",
        #     vpc=vpc,
        #     description="Allow traffic to RDS from ECS tasks",
        #     allow_all_outbound=True
        # )

        # rds_instance = rds.DatabaseCluster(
        #     self, "AuroraCluster",
        #     engine=rds.DatabaseClusterEngine.aurora_mysql(version=rds.AuroraMysqlEngineVersion.VER_3_03_0),
        #     default_database_name="keycloak",
        #     instances=2,
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(
        #         subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        #     ),
        #     security_groups=[db_security_group],
        #     instance_props=rds.InstanceProps(
        #         instance_type=ec2.InstanceType.of(
        #             ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MEDIUM
        #             )
        #     )
        # instance_props=rds.InstanceProps(
        #     instance_type=ec2.InstanceType.of(
        #         ec2.InstanceClass.BURSTABLE3, ec2.InstanceSize.MEDIUM
        #     ),
        #     vpc=vpc,
        #     vpc_subnets=ec2.SubnetSelection(
        #         subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        #     )
        # )
        # )

        # Allow traffic from ECS tasks to RDS on port 3306
        # db_security_group.add_ingress_rule(
        #     peer=ecs_security_group,
        #     connection=ec2.Port.tcp(3306),
        #     description="Allow ECS tasks to connect to RDS"
        # )

        # CfnOutput(
        #     self, "LoadBalancerDNS",
        #     value=fargate_service.load_balancer.load_balancer_dns_name
        # )