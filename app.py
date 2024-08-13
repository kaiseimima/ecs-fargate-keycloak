#!/usr/bin/env python3

import aws_cdk as cdk

from dev_keycloak.dev_keycloak_stack import DevKeycloakStack


app = cdk.App()
DevKeycloakStack(app, "DevKeycloakStack")

app.synth()
