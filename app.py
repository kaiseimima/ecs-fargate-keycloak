#!/usr/bin/env python3

import aws_cdk as cdk

# from dev_keycloak.dev_keycloak_stack import DevKeycloakStack
from dev_keycloak.dev_network_stack import DevNetworkStack


app = cdk.App()
# DevKeycloakStack(app, "DevKeycloakStack")
DevNetworkStack(app, "DevNetworkStack")

app.synth()
