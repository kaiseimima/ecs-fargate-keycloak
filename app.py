#!/usr/bin/env python3

import aws_cdk as cdk

# from dev_keycloak.dev_keycloak_stack import DevKeycloakStack
from dev_keycloak.dev_network_stack import DevNetworkStack
from dev_keycloak.dev_ecs_stack import DevEcsStack


app = cdk.App()
# DevKeycloakStack(app, "DevKeycloakStack")
network_stack = DevNetworkStack(app, "DevNetworkStack")
ecs_stack = DevEcsStack(app, "DevEcsStack", vpc=network_stack.vpc)

app.synth()
