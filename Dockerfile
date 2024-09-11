FROM quay.io/keycloak/keycloak:latest as builder

WORKDIR /opt/keycloak

# for demonstration purposes only, please make sure to use proper certificates in production instead
RUN keytool -genkeypair -storepass password -storetype PKCS12 -keyalg RSA -keysize 2048 -dname "CN=server" -alias server -ext "SAN:c=DNS:localhost,IP:127.0.0.1" -keystore conf/server.keystore
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:latest
COPY --from=builder /opt/keycloak/ /opt/keycloak/

#add jgroup-aws.jar and depencies
ADD --chown=keycloak:keycloak https://repo1.maven.org/maven2/org/jgroups/aws/jgroups-aws/2.0.1.Final/jgroups-aws-2.0.1.Final.jar /opt/keycloak/providers/jgroups-aws-2.0.1.Final.jar
ADD --chown=keycloak:keycloak https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-core/1.12.410/aws-java-sdk-core-1.12.410.jar  /opt/keycloak/providers/aws-java-sdk-core-1.12.410.jar
ADD --chown=keycloak:keycloak https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-s3/1.12.410/aws-java-sdk-s3-1.12.410.jar   /opt/keycloak/providers/aws-java-sdk-s3-1.12.410.jar
ADD --chown=keycloak:keycloak https://repo1.maven.org/maven2/joda-time/joda-time/2.12.2/joda-time-2.12.2.jar  /opt/keycloak/providers/joda-time-2.12.2.jar

ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]