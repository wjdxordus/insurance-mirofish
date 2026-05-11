#!/usr/bin/env sh
set -eu

ROOT="/app"

# Railway remote OpenCode mode:
# - Use OPENCODE_REMOTE_* values when present.
# - Keep everything overridable via Railway Variables.
if [ -n "${OPENCODE_REMOTE_SERVER_URL:-}" ]; then
  export OPENCODE_SERVER_URL="${OPENCODE_REMOTE_SERVER_URL}"
fi

if [ -n "${OPENCODE_REMOTE_SERVER_USERNAME:-}" ]; then
  export OPENCODE_SERVER_USERNAME="${OPENCODE_REMOTE_SERVER_USERNAME}"
fi

if [ -n "${OPENCODE_REMOTE_SERVER_PASSWORD:-}" ]; then
  export OPENCODE_SERVER_PASSWORD="${OPENCODE_REMOTE_SERVER_PASSWORD}"
fi

if [ -n "${OPENCODE_REMOTE_MODEL_PROVIDER_ID:-}" ]; then
  export OPENCODE_MODEL_PROVIDER_ID="${OPENCODE_REMOTE_MODEL_PROVIDER_ID}"
fi

if [ -n "${OPENCODE_REMOTE_MODEL_ID:-}" ]; then
  export OPENCODE_MODEL_ID="${OPENCODE_REMOTE_MODEL_ID}"
fi

export OPENCODE_PROXY_PORT="${OPENCODE_REMOTE_PROXY_PORT:-${OPENCODE_PROXY_PORT:-4098}}"
export OPENCODE_NGROK_SKIP_BROWSER_WARNING="${OPENCODE_NGROK_SKIP_BROWSER_WARNING:-1}"

# In remote mode, force backend traffic through in-container proxy to avoid
# stale pasted values (e.g. LLM_BASE_URL=...4097) causing runtime 500 errors.
if [ -n "${OPENCODE_REMOTE_SERVER_URL:-}" ]; then
  export LLM_API_KEY="${LLM_API_KEY:-opencode-remote}"
  export LLM_BASE_URL="http://127.0.0.1:${OPENCODE_PROXY_PORT}/v1"
  export LLM_MODEL_NAME="${OPENCODE_REMOTE_MODEL_ID:-${OPENCODE_MODEL_ID:-${LLM_MODEL_NAME:-gpt-5.2}}}"
else
  # Non-remote mode: keep compatibility with explicit LLM_* overrides.
  export LLM_API_KEY="${LLM_API_KEY:-opencode-remote}"
  export LLM_BASE_URL="${LLM_BASE_URL:-http://127.0.0.1:${OPENCODE_PROXY_PORT}/v1}"
  export LLM_MODEL_NAME="${LLM_MODEL_NAME:-${OPENCODE_MODEL_ID:-gpt-5.2}}"
fi

cd "$ROOT"

node scripts/opencode-openai-proxy.mjs &
PROXY_PID=$!

cleanup() {
  kill "$PROXY_PID" >/dev/null 2>&1 || true
}

trap cleanup EXIT INT TERM

cd backend
exec uv run python run.py
