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
    Stack, CfnOutput
)

class DevKeycloakStackV2(Stack):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create a VPC
        vpc = ec2.Vpc(self, "MyVpc", max_azs=2)

        # ECS Cluster
        cluster = ecs.Cluster(self, "KeycloakCluster", vpc=vpc)

        # Security Group
        sg = ec2.SecurityGroup(self, "KeycloakSecurityGroup", vpc=vpc)
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80))
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(443))
        sg.add_ingress_rule(sg, ec2.Port.tcp(7800))
        sg.add_ingress_rule(sg, ec2.Port.tcp(3306))

        # RDS Aurora Configuration
        db_secret = secretsmanager.Secret(self, "DBSecret", 
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True, 
                include_space=False, 
                secret_string_template='{"username":"keycloak_user"}',
                generate_string_key="password"
            )
        )

        db_cluster = rds.DatabaseCluster(self, "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_mysql(version=rds.AuroraMysqlEngineVersion.VER_3_04_0),
            credentials=rds.Credentials.from_secret(db_secret),
            instance_props={
                "vpc": vpc,
                "security_groups": [sg],
                "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            },
            instances=2,
            default_database_name="keycloakdb"
        )

        # CloudWatch Logs Group
        log_group = logs.LogGroup(self, "KeycloakLogGroup",
            log_group_name="/ecs/keycloak",
            retention=logs.RetentionDays.ONE_MONTH
        )

        # ECS Task Role
        task_role = iam.Role(self, "KeycloakTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
            ]
        )

        # ECS Task Definition
        task_definition = ecs.FargateTaskDefinition(self, "KeycloakTaskDef",
            task_role=task_role,
            execution_role=iam.Role(self, "KeycloakExecutionRole",
                assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
                managed_policies=[
                    iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonECSTaskExecutionRolePolicy")
                ]
            ),
            memory_limit_mib=4096,
            cpu=1024
        )

        # ECS Container Definition
        container = task_definition.add_container("KeycloakContainer",
            image=ecs.ContainerImage.from_registry("878518084785.dkr.ecr.us-east-1.amazonaws.com/keycloak-aws:latest"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="keycloak", log_group=log_group),
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
        container.add_port_mappings(ecs.PortMapping(container_port=8080), ecs.PortMapping(container_port=7800))

        # ECS Service
        ecs_service = ecs_patterns.ApplicationLoadBalancedFargateService(self, "KeycloakService",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=2,
            public_load_balancer=True
        )

        # Output the DNS where Keycloak can be accessed
        CfnOutput(self, "LoadBalancerDNS", value=ecs_service.load_balancer.load_balancer_dns_name)

