#!/usr/bin/env bash
set -euo pipefail

BASE="${FINAM_REST_BASE:-https://api.finam.ru}"
TOKEN="${FINAM_TOKEN:-}"

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: FINAM_TOKEN is not set"
  exit 2
fi

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

request() {
  local path="$1"
  local name="$2"
  local url="${BASE}${path}"
  local hdr="${tmpdir}/${name}.hdr"
  local body="${tmpdir}/${name}.body"

  echo "==> GET ${url}"

  # -L: follow redirects (чтобы увидеть куда реально уводит)
  # -sS: silent but show errors
  # -D: dump headers
  curl -sS -L \
    -D "$hdr" \
    -o "$body" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Accept: application/json" \
    "$url" || {
      echo "ERROR: curl failed for ${url}"
      exit 10
    }

  local code
  code="$(awk 'NR==1{print $2}' "$hdr" | tail -n 1)"
  local ctype
  ctype="$(grep -i '^content-type:' "$hdr" | tail -n 1 | tr -d '\r' | cut -d' ' -f2- || true)"
  local loc
  loc="$(grep -i '^location:' "$hdr" | tail -n 1 | tr -d '\r' | cut -d' ' -f2- || true)"

  echo "HTTP: ${code}  Content-Type: ${ctype:-<none>}"
  [[ -n "$loc" ]] && echo "Location: ${loc}"

  # первые 80 байт тела — чтобы сразу увидеть HTML/JSON
  echo -n "Body head: "
  head -c 80 "$body" | tr '\n' ' ' ; echo

  # hard-fail условия
  if [[ "$code" != "200" ]]; then
    echo "FAIL: HTTP code != 200 for ${path}"
    exit 20
  fi

  # если пришёл HTML — это не REST API, а портал/прокси/редирект
  if head -c 20 "$body" | grep -qiE '<!doctype|<html'; then
    echo "FAIL: HTML received (wrong endpoint or auth redirect) for ${path}"
    exit 21
  fi

  # JSON обычно application/json; иногда может быть application/json; charset=utf-8
  if ! echo "$ctype" | grep -qi 'application/json'; then
    echo "FAIL: Content-Type is not application/json for ${path}"
    exit 22
  fi

  echo "OK: ${path}"
  echo
}

echo "BASE=${BASE}"
echo "Token head=$(echo "$TOKEN" | cut -c1-3)... len=${#TOKEN}"
echo

# 1) базовый эндпоинт (у тебя он отвечает {"assets":[]})
request "/v1/assets" "assets"

# 2) котировка (может дать 403/404 если нет прав на market data — тогда тест покажет это)
# Если не хочешь, чтобы это было hard-fail при отсутствии md permissions — закомментируй.
request "/v1/instruments/SBER@MISX/quote" "quote"

# 3) бары
request "/v1/instruments/SBER@MISX/bars?timeframe=D1&count=1" "bars"

echo "ALL OK"