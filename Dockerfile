FROM python:3.13-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

ARG TARGETARCH
RUN case "${TARGETARCH}" in \
      amd64) UV_ARCH="x86_64" ;; \
      arm64) UV_ARCH="aarch64" ;; \
      *) echo "Unsupported architecture: ${TARGETARCH}" && exit 1 ;; \
    esac \
    && curl -L "https://github.com/astral-sh/uv/releases/download/0.6.14/uv-${UV_ARCH}-unknown-linux-gnu.tar.gz" -o uv.tar.gz \
    && tar -xzf uv.tar.gz \
    && mv "uv-${UV_ARCH}-unknown-linux-gnu/uv" /usr/local/bin/uv \
    && chmod 0755 /usr/local/bin/uv \
    && rm -rf uv.tar.gz "uv-${UV_ARCH}-unknown-linux-gnu"

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never \
    UV_PYTHON=/usr/local/bin/python3.13 \
    UV_PROJECT_ENVIRONMENT=/usr/app

# Install dependencies first (without the project itself) for better layer caching
RUN --mount=type=cache,target=/root/.cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Copy project source and install the project as a non-editable wheel
COPY . /usr/app/src
WORKDIR /usr/app/src
RUN --mount=type=cache,target=/root/.cache \
    uv sync --frozen --no-editable --no-dev

# Regenerate the Twisted plugin cache so twistd finds the txsftp plugin
RUN /usr/app/bin/python -c "from txsftp import setup; setup.regeneratePluginCache()"


FROM python:3.13-slim

LABEL Version="2.0.0"

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Generate SSH host keys for the SFTP server.
# Mount a named volume over /etc/txsftp to persist keys across image rebuilds.
RUN mkdir -p /etc/txsftp \
    && ssh-keygen -t rsa -b 4096 -f /etc/txsftp/id_rsa -N "" \
    && chmod 600 /etc/txsftp/id_rsa \
    && chmod 644 /etc/txsftp/id_rsa.pub

RUN useradd -r -d /usr/app -s /bin/false txsftp \
    && mkdir -p /usr/app /data/sftp \
    && chown txsftp:txsftp /usr/app /data/sftp \
    && chown txsftp:txsftp /etc/txsftp /etc/txsftp/id_rsa /etc/txsftp/id_rsa.pub \
    && touch /etc/txsftp.json && chown txsftp:txsftp /etc/txsftp.json

COPY --from=builder /usr/app /usr/app

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Runtime configuration — override via docker-compose environment or -e flags.
# DB_PASSWORD has no default and must be supplied at runtime.
ENV SFTP_PORT=8888
ENV SERVER_CLASS=txsftp.handler.GPGFileTransferServer
ENV ACCESS_LOG=/dev/null
ENV ERROR_LOG=
ENV DB_HOST=db
ENV DB_PORT=5432
ENV DB_NAME=txsftp
ENV DB_USER=txsftp
ENV PATH="/usr/app/bin:/usr/local/bin:/usr/bin:/bin"

USER txsftp

EXPOSE 8888

ENTRYPOINT ["/entrypoint.sh"]
