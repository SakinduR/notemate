#!/bin/sh
set -e

MODEL="${OLLAMA_MODEL:-llama3.2:3b}"

ollama serve &
SERVER_PID=$!

echo "Waiting for Ollama server to be ready..."
until ollama list >/dev/null 2>&1; do
  sleep 1
done

if ollama list | grep -q "^${MODEL}"; then
  echo "Model ${MODEL} already present."
else
  echo "Pulling model ${MODEL}..."
  ollama pull "${MODEL}"
fi

wait "$SERVER_PID"
