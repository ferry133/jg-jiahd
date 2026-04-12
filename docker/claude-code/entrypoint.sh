#!/bin/bash
set -e

TTYD_ARGS=(
    "--port" "7681"
    "--writable"
    "--max-clients" "5"
)

# Enable basic auth if credentials are provided
if [ -n "${TTYD_CREDENTIAL}" ]; then
    TTYD_ARGS+=("--credential" "${TTYD_CREDENTIAL}")
fi

exec ttyd "${TTYD_ARGS[@]}" claude
