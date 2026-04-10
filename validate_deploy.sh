#!/usr/bin/env bash
# validate_deploy.sh
# Uso: ./validate_deploy.sh https://tu-backend.railway.app
# Valida que el backend deployado responda correctamente.

set -e

BACKEND_URL="${1:-http://localhost:8000}"
PASS=0
FAIL=0

check() {
  local label="$1"
  local url="$2"
  local expected="$3"

  response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$url" 2>/dev/null)

  if [ "$response" = "$expected" ]; then
    echo "  ✅ $label → HTTP $response"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $label → HTTP $response (esperado: $expected)"
    FAIL=$((FAIL + 1))
  fi
}

check_json() {
  local label="$1"
  local url="$2"
  local key="$3"

  response=$(curl -s --max-time 15 "$url" 2>/dev/null)
  if echo "$response" | grep -q "\"$key\""; then
    echo "  ✅ $label → contiene '$key'"
    PASS=$((PASS + 1))
  else
    echo "  ❌ $label → no contiene '$key' — respuesta: ${response:0:100}"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "🔍 Validando backend: $BACKEND_URL"
echo "─────────────────────────────────"

check       "Health básico"        "$BACKEND_URL/api/health"              "200"
check       "Health completo"      "$BACKEND_URL/api/health/full"         "200"
check       "Matches live"         "$BACKEND_URL/api/matches/live"        "200"
check       "Matches today"        "$BACKEND_URL/api/matches/today"       "200"
check       "Matches results"      "$BACKEND_URL/api/matches/results"     "200"
check       "Matches argentina"    "$BACKEND_URL/api/matches/argentina"   "200"
check       "Sports summary"       "$BACKEND_URL/api/sports/"             "200"
check       "Players abroad"       "$BACKEND_URL/api/players/abroad"      "200"
check_json  "Health tiene status"  "$BACKEND_URL/api/health"              "status"
check_json  "Scheduler activo"     "$BACKEND_URL/api/health/full"         "scheduler"

echo "─────────────────────────────────"
echo "  ✅ Pasaron: $PASS"
echo "  ❌ Fallaron: $FAIL"
echo ""

if [ "$FAIL" -gt 0 ]; then
  echo "⚠️  Deploy incompleto — revisar logs del servicio"
  exit 1
else
  echo "🚀 Deploy validado correctamente"
  exit 0
fi
