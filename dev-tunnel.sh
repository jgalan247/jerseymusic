#!/usr/bin/env bash
set -euo pipefail

# -------- settings --------
PORT="${PORT:-8000}"               # your app's local port
ENV_FILE="${ENV_FILE:-.env.local}" # where to write the URL
NGROK_BIN="${NGROK_BIN:-ngrok}"    # path to ngrok binary
# --------------------------

# Kill old ngrok (optional + safe-ish)
if pgrep -x "ngrok" >/dev/null; then
  echo "Killing existing ngrok..."
  pkill -x ngrok || true
  sleep 1
fi

# Start ngrok in background
echo "Starting ngrok on port ${PORT}..."
${NGROK_BIN} http ${PORT} --log=stdout >/tmp/ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for the API to come up
echo -n "Waiting for ngrok..."
until curl -fsS http://127.0.0.1:4040/api/tunnels >/dev/null 2>&1; do
  echo -n "."
  sleep 0.5
done
echo ""

# Grab the public URL (https)
PUBLIC_URL="$(curl -fsS http://127.0.0.1:4040/api/tunnels \
  | python -c "import sys, json; d=json.load(sys.stdin); print([t['public_url'] for t in d['tunnels'] if t['public_url'].startswith('https://')][0])")"

echo "ngrok public URL: ${PUBLIC_URL}"

# Write to your env file for the app to read (or for your clipboard)
grep -q '^PUBLIC_TUNNEL_URL=' "${ENV_FILE}" 2>/dev/null && \
  sed -i '' "s|^PUBLIC_TUNNEL_URL=.*$|PUBLIC_TUNNEL_URL=${PUBLIC_URL}|g" "${ENV_FILE}" \
  || echo "PUBLIC_TUNNEL_URL=${PUBLIC_URL}" >> "${ENV_FILE}"

# Copy to clipboard (macOS)
command -v pbcopy >/dev/null && echo -n "${PUBLIC_URL}" | pbcopy && echo "Copied to clipboard ✅"

# ---- OPTIONAL: auto-update a webhook in a service that HAS an API ----
# Example placeholder; replace with a real API (e.g., Stripe/GitHub/etc.)
if [[ -n "${AUTO_UPDATE_ENDPOINT:-}" && -n "${API_TOKEN:-}" ]]; then
  echo "Updating remote webhook at ${AUTO_UPDATE_ENDPOINT}..."
  curl -fsS -X POST "${AUTO_UPDATE_ENDPOINT}" \
    -H "Authorization: Bearer ${API_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{\"webhook_url\": \"${PUBLIC_URL}/payments/sumup/webhook\"}" \
    && echo "Webhook updated ✅" || echo "⚠️ Webhook update failed"
fi

# Keep script attached so you can Ctrl+C to stop both your app and ngrok
echo "Tunnel running (PID: ${NGROK_PID}). Press Ctrl+C to stop."
wait ${NGROK_PID}
