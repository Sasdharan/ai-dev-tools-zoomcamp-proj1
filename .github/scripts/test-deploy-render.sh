#!/usr/bin/env bash
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/deploy-render.sh"

API_HOOK="https://api.render.com/deploy/srv-api?key=test-api"
WEB_HOOK="https://api.render.com/deploy/srv-web?key=test-web"
API_URL="https://api.example.com/"
WEB_URL="https://web.example.com/"
IMAGE_PREFIX="ghcr.io/example/project"
TAG="0123456789abcdef0123456789abcdef01234567"
calls=()
curl() { calls+=("$*"); echo "mock-curl"; }
sleep() { :; }

assert_no_deploy() {
  local output
  output="$(main 2>&1)" && {
    echo "Expected configuration validation to fail" >&2
    exit 1
  }
  [[ "$output" == *"::error::"* ]]
  [[ "$output" != *"mock-curl"* ]]
  [[ "$output" != *"test-api"* && "$output" != *"test-web"* ]]
  [[ ${#calls[@]} == 0 ]]
}

for name in API_HOOK WEB_HOOK API_URL WEB_URL IMAGE_PREFIX TAG; do
  saved="${!name}"
  printf -v "$name" '%s' ""
  assert_no_deploy
  printf -v "$name" '%s' "$saved"
done

saved="$API_HOOK"
for API_HOOK in \
  "not-a-url" \
  "https://api.render.com/deploy/srv-api" \
  "https://api.render.com/deploy/srv-api?key=" \
  "https://api.render.com/deploy/srv-api?key=test-api " \
  "https://wrong.example.com/deploy/srv-api?key=test-api"; do
  assert_no_deploy
done
API_HOOK="$saved"

saved="$TAG"
TAG="invalid-tag"
assert_no_deploy
TAG="$saved"

main
[[ ${#calls[@]} == 4 ]]
[[ "${calls[0]}" == *"--request POST --url-query imgURL=$IMAGE_PREFIX-backend:$TAG $API_HOOK" ]]
[[ "${calls[1]}" == *"--request POST --url-query imgURL=$IMAGE_PREFIX-frontend:$TAG $WEB_HOOK" ]]
[[ "${calls[2]}" == *"https://api.example.com/health" ]]
[[ "${calls[3]}" == *"https://web.example.com/" ]]

calls=()
curl() { calls+=("$*"); return 22; }
if main >/dev/null 2>&1; then
  echo "Expected failed deploy request to fail the script" >&2
  exit 1
fi
[[ ${#calls[@]} == 1 ]]

if wait_for_url "$API_URL" backend >/dev/null 2>&1; then
  echo "Expected exhausted health checks to fail" >&2
  exit 1
fi

echo "Render deployment regression checks passed."
