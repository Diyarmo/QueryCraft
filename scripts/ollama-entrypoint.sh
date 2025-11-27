#!/usr/bin/env sh
set -e

MODEL_NAME="${OLLAMA_MODEL:-sqlcoder:7b-q4_K_M}"
LOCAL_OLLAMA_HOST="${OLLAMA_LOCAL_HOST:-http://127.0.0.1:11434}"

ollama serve &
SERVER_PID=$!

until OLLAMA_HOST="$LOCAL_OLLAMA_HOST" ollama list >/dev/null 2>&1; do
  sleep 1
done

echo "Ensuring ${MODEL_NAME} is available..."
OLLAMA_HOST="$LOCAL_OLLAMA_HOST" ollama run "$MODEL_NAME" || true

wait "$SERVER_PID"
