#!/usr/bin/env bash
set -euo pipefail

validate_config() {
  local invalid=0 name label value
  for name in API_HOOK WEB_HOOK API_URL WEB_URL IMAGE_PREFIX TAG; do
    case "$name" in
      API_HOOK) label="secret RENDER_DEPLOY_HOOK_API" ;;
      WEB_HOOK) label="secret RENDER_DEPLOY_HOOK_WEB" ;;
      API_URL) label="variable API_URL" ;;
      WEB_URL) label="variable DEV_WEB_URL / PROD_WEB_URL" ;;
      *) label="$name" ;;
    esac
    value="${!name:-}"
    if [[ -z "$value" ]]; then
      echo "::error::Missing $label. Configure the selected GitHub Environment; see README deployment setup." >&2
      invalid=1
    elif [[ "$name" == *_HOOK ]]; then
      if [[ ! "$value" =~ ^https://api\.render\.com/deploy/srv-[[:alnum:]-]+\?key=[^[:space:]\&\#]+$ ]]; then
        echo "::error::Invalid $label. Use the complete Render deploy hook URL, including ?key=, without quotes or whitespace." >&2
        invalid=1
      fi
    elif [[ "$name" == *_URL ]]; then
      if [[ ! "$value" =~ ^https://[^[:space:]\?\#]+$ ]]; then
        echo "::error::Invalid $label. Use the service's public HTTPS URL." >&2
        invalid=1
      fi
    elif [[ "$name" == TAG && ! "$value" =~ ^[a-fA-F0-9]{40}$ ]]; then
      echo "::error::TAG must be the full 40-character commit SHA of published images." >&2
      invalid=1
    fi
  done
  return "$invalid"
}

wait_for_url() {
  local url="$1" service="$2" attempt
  for attempt in $(seq 1 40); do
    if curl --fail --silent --show-error --connect-timeout 10 --max-time 20 "$url"; then
      return 0
    fi
    sleep 15
  done
  echo "::error::Render $service health check failed." >&2
  return 1
}

main() {
  validate_config || return 1
  curl --fail --silent --show-error --connect-timeout 10 --max-time 60 \
    --request POST --url-query "imgURL=$IMAGE_PREFIX-backend:$TAG" "$API_HOOK" || return 1
  curl --fail --silent --show-error --connect-timeout 10 --max-time 60 \
    --request POST --url-query "imgURL=$IMAGE_PREFIX-frontend:$TAG" "$WEB_HOOK" || return 1
  sleep 60
  wait_for_url "${API_URL%/}/health" backend || return 1
  wait_for_url "${WEB_URL%/}/" frontend
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main
fi
