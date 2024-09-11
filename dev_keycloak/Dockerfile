# FROM registry.access.redhat.com/ubi9 AS ubi-micro-build

# RUN dnf install --installroot /mnt/rootfs python3-pip python3-wheel python3 --releasever 9 --setopt install_weak_deps=false --nodocs -y && \
#     dnf --installroot /mnt/rootfs clean all && \
#     rpm --root /mnt/rootfs -e --nodeps setup

# # JavaとUnzipのインストール、およびApache Mavenのパス設定
# COPY apache-maven-3.9.6-bin.zip /opt/
# RUN dnf install -y unzip java-17-openjdk java-17-openjdk-devel && \
#     cd /opt && \
#     unzip apache-maven-3.9.6-bin.zip
# ENV PATH="/opt/apache-maven-3.9.6/bin:${PATH}"

# # argon2-password-hash-providerの解凍とビルド
# COPY argon2-password-hash-provider-master.zip /opt/
# RUN cd /opt && \
#     unzip argon2-password-hash-provider-master.zip && \
#     cd argon2-password-hash-provider-master && \
#     # ls && \
#     mvn clean package && \
#     ls -la /opt/argon2-password-hash-provider-master/target

# # keycloak-webauthn-conditional-mediationの解凍とビルド
# COPY keycloak-webauthn-conditional-mediation-main.zip /opt/
# RUN cd /opt && \
#     unzip keycloak-webauthn-conditional-mediation-main.zip && \
#     cd keycloak-webauthn-conditional-mediation-main && \
#     mvn clean package && \
#     ls -la /opt/argon2-password-hash-provider-master/target



FROM quay.io/keycloak/keycloak:latest as builder
# healthとmetricsのサポートを有効化
ENV KC_HEALTH_ENABLED=true
ENV KC_METRICS_ENABLED=true

# 既存の Dockerfile の内容は保持し、以下の ENV 命令を適切な場所に追加します

ENV DB_VENDOR=mysql \
    DB_ADDR=db \
    DB_USER=dbuser \
    DB_PASSWORD=dbpass \
    DB_DATABASE=keycloak \
    KEYCLOAK_USER=admin \
    KEYCLOAK_PASSWORD=admin \
    PROXY_ADDRESS_FORWARDING=true \
    JDBC_PARAMS="&enabledTLSProtocols=TLSv1.2"


# database vendorの設定
ENV KC_DB=mysql

# /opt/argon2-password-hash-provider-master/target/の確認
# RUN ls -la /opt/argon2-password-hash-provider-master/target

# # keycloak-webauthn-conditional-mediation.jarとargon2-password-hash-provider-master.jarのコピー
# COPY --from=ubi-micro-build /opt/keycloak-webauthn-conditional-mediation-main/target/keycloak-webauthn-conditional-mediation.jar /opt/keycloak/providers/
# COPY --from=ubi-micro-build /opt/argon2-password-hash-provider-master/target/argon2-password-hash-provider-*.jar /opt/keycloak/providers/

WORKDIR /opt/keycloak

# ビルドの実行
RUN /opt/keycloak/bin/kc.sh build

FROM quay.io/keycloak/keycloak:latest
# # builderステージからのファイルのコピー
# COPY --from=builder /opt/keycloak/ /opt/keycloak/
# COPY --from=ubi-micro-build /mnt/rootfs /

# database vendorの設定
ENV KC_DB=mysql
# ENV KC_DB_URL=<DBURL>
ENV KC_DB_USERNAME=dbuser
ENV KC_DB_PASSWORD=dbpass
# ENV KC_HOSTNAME=localhost
# ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
