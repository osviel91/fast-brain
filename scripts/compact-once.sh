#!/bin/sh
set -eu

: "${FAST_BRAIN_URL:?Set FAST_BRAIN_URL}"
: "${FAST_BRAIN_API_KEY:?Set FAST_BRAIN_API_KEY}"

AGENT_ID="${FAST_BRAIN_AGENT_ID:-hermes}"
KIND="${FAST_BRAIN_COMPACT_KIND:-summary}"
MAX_CHARS="${FAST_BRAIN_COMPACT_MAX_CHARS:-12000}"
MAX_SESSIONS="${FAST_BRAIN_COMPACT_MAX_SESSIONS:-5}"
MIN_AGE_MINUTES="${FAST_BRAIN_COMPACT_MIN_AGE_MINUTES:-60}"

curl -fsS -X POST \
  -H "Authorization: Bearer $FAST_BRAIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":\"$AGENT_ID\",\"kind\":\"$KIND\",\"max_chars\":$MAX_CHARS,\"max_sessions\":$MAX_SESSIONS,\"min_age_minutes\":$MIN_AGE_MINUTES}" \
  "${FAST_BRAIN_URL%/}/v1/compact"

printf '\n'
