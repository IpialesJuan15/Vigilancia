# syntax=docker/dockerfile:1
FROM golang:1.24-bookworm AS build
WORKDIR /src
RUN --mount=type=secret,id=ca_bundle \
    if [ -f /run/secrets/ca_bundle ]; then export GIT_SSL_CAINFO=/run/secrets/ca_bundle SSL_CERT_FILE=/run/secrets/ca_bundle; fi; \
    git init . && git remote add origin https://github.com/minio/minio.git && \
    git fetch --depth 1 origin refs/tags/RELEASE.2025-09-07T16-13-09Z && \
    test "$(git rev-parse FETCH_HEAD)" = 01ce918d8279a20e4706b96a64396146894adee4 && \
    git checkout --detach FETCH_HEAD
RUN --mount=type=secret,id=ca_bundle \
    if [ -f /run/secrets/ca_bundle ]; then export SSL_CERT_FILE=/run/secrets/ca_bundle; fi; \
    CGO_ENABLED=0 GOMAXPROCS=2 go build -p 2 -trimpath -o /minio .
FROM debian:bookworm-slim
COPY --from=build /minio /usr/local/bin/minio
COPY --from=build /src/LICENSE /usr/share/licenses/minio/LICENSE
LABEL org.opencontainers.image.source="https://github.com/minio/minio" org.opencontainers.image.licenses="AGPL-3.0-only"
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001
ENTRYPOINT ["minio"]
