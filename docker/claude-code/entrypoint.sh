#!/bin/bash
set -e

# Initialize persistent config directory on first run
mkdir -p /home/claude/.claude
if [ ! -f /home/claude/.claude/settings.json ]; then
    echo '{"env":{"DISABLE_AUTOUPDATER":"1"}}' > /home/claude/.claude/settings.json
fi

TTYD_ARGS=(
    "--port" "7681"
    "--writable"
    "--max-clients" "5"
)

# Enable basic auth if credentials are provided
if [ -n "${TTYD_CREDENTIAL}" ]; then
    TTYD_ARGS+=("--credential" "${TTYD_CREDENTIAL}")
fi

exec ttyd "${TTYD_ARGS[@]}" bash
