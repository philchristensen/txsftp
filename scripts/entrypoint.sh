#!/bin/sh
set -e

# Write /etc/txsftp.json from environment variables at container startup.
# All values have defaults set via ENV in the Dockerfile.

cat > /etc/txsftp.json <<EOF
{
  "sftp-port": ${SFTP_PORT},
  "server-class": "${SERVER_CLASS}",
  "access-log": "${ACCESS_LOG}",
  "error-log": "${ERROR_LOG}",
  "db-url": "psycopg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}",
  "ssh-public-key": "${SSH_KEY_DIR:-/etc/txsftp}/id_rsa.pub",
  "ssh-private-key": "${SSH_KEY_DIR:-/etc/txsftp}/id_rsa",
  "suppress-deprecation-warnings": false
}
EOF

if [ "$1" = '' ]; then
    exec twistd --nodaemon --logfile=- --pidfile=/tmp/twistd.pid txsftp
else
    exec "$@"
fi
