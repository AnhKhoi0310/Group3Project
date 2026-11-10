#!/usr/bin/env bash
# ReviewLens verification script (S1-006 tooling checks + S1-008 secret checks).
#
# Usage (from anywhere inside the repo):
#   scripts/verify.sh               backend + frontend + secret checks
#   scripts/verify.sh --mysql       also start MySQL in Docker and run the DB tests
#   scripts/verify.sh --prove-fail  also prove a test fails when check_revoked is broken
#   scripts/verify.sh --quick       skip the frontend build and the dist leak check
#
# It keeps going after a failure and prints a summary at the end.
# Exit code is 0 only if every check passed.

set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "Run inside the repo."; exit 2; }
cd "$ROOT" || exit 2

RUN_MYSQL=0; PROVE_FAIL=0; QUICK=0
for arg in "$@"; do
  case "$arg" in
    --mysql) RUN_MYSQL=1 ;;
    --prove-fail) PROVE_FAIL=1 ;;
    --quick) QUICK=1 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg"; exit 2 ;;
  esac
done

RESULTS=()
FAILED=0
LOG_DIR="$(mktemp -d)"

record() { # name status
  RESULTS+=("$2|$1")
  [ "$2" = "FAIL" ] && FAILED=1
}

run() { # name, command...
  local name="$1"; shift
  local log="$LOG_DIR/$(echo "$name" | tr ' /:' '___').log"
  printf '>> %s ... ' "$name"
  if "$@" >"$log" 2>&1; then
    echo "ok"; record "$name" PASS
  else
    echo "FAILED (last lines below)"; tail -n 15 "$log" | sed 's/^/     /'
    record "$name" FAIL
  fi
}

skip() { echo ">> $1 ... skipped"; record "$1" SKIP; }

# ---------- Backend environment ----------
echo "=== Backend ==="
cd "$ROOT/backend" || exit 2
if [ ! -x .venv/bin/python ]; then
  echo "Creating backend/.venv ..."
  rm -rf .venv
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 .venv >/dev/null 2>&1 || uv venv .venv >/dev/null 2>&1
  else
    python3 -m venv .venv >/dev/null 2>&1 || python3 -m venv --without-pip .venv
  fi
fi
# shellcheck disable=SC1091
source .venv/bin/activate
echo "Python: $(python --version 2>&1)"

if ! python -c "import fastapi, pytest, ruff" >/dev/null 2>&1 && ! command -v ruff >/dev/null 2>&1; then
  echo "Installing backend dependencies ..."
  if command -v uv >/dev/null 2>&1; then
    uv pip install -q -r requirements-dev.txt
  else
    pip install -q -r requirements-dev.txt
  fi
fi

run "backend: ruff check"         ruff check .
run "backend: ruff format --check" ruff format --check .
run "backend: compileall"         python -m compileall -q app
run "backend: pytest"             pytest -q

# ---------- Optional: MySQL tests ----------
if [ "$RUN_MYSQL" = 1 ]; then
  echo "=== Backend MySQL tests ==="
  cd "$ROOT" || exit 2
  [ -f .env ] || cp .env.example .env
  # shellcheck disable=SC1091
  set -a; source .env; set +a
  if docker compose up -d --wait db >/dev/null 2>&1; then
    docker compose exec -T db mysql -uroot -p"$MYSQL_ROOT_PASSWORD" \
      -e "CREATE DATABASE IF NOT EXISTS reviewlens_test;" >/dev/null 2>&1
    cd "$ROOT/backend" || exit 2
    run "backend: pytest with MySQL (0 skipped expected)" \
      env TEST_DATABASE_URL="mysql+pymysql://root:${MYSQL_ROOT_PASSWORD}@127.0.0.1:${MYSQL_HOST_PORT:-3306}/reviewlens_test" \
      pytest -q -rs
  else
    echo ">> could not start MySQL with docker compose"
    record "backend: pytest with MySQL" FAIL
  fi
  cd "$ROOT/backend" || exit 2
fi

# ---------- Optional: prove a test can fail ----------
if [ "$PROVE_FAIL" = 1 ]; then
  echo "=== Negative check ==="
  TARGET="app/adapters/identity.py"
  cp "$TARGET" "$LOG_DIR/identity.py.bak"
  trap 'cp "$LOG_DIR/identity.py.bak" "$ROOT/backend/$TARGET" 2>/dev/null' EXIT
  sed -i 's/check_revoked=True/check_revoked=False/' "$TARGET"
  if pytest -q tests/test_identity_adapter.py >"$LOG_DIR/neg.log" 2>&1; then
    echo ">> negative check ... FAILED (tests still passed with the bug)"
    record "negative: test fails when check_revoked broken" FAIL
  else
    echo ">> negative check ... ok (test failed as expected)"
    record "negative: test fails when check_revoked broken" PASS
  fi
  cp "$LOG_DIR/identity.py.bak" "$TARGET"
  run "negative: restored file passes again" pytest -q tests/test_identity_adapter.py
fi

deactivate 2>/dev/null || true

# ---------- Frontend ----------
echo "=== Frontend ==="
cd "$ROOT/frontend" || exit 2
echo "Node: $(node --version 2>&1)"
[ -d node_modules ] || run "frontend: npm ci" npm ci
run "frontend: lint"         npm run lint
run "frontend: format:check" npm run format:check
if [ "$QUICK" = 1 ]; then skip "frontend: build"; else run "frontend: build" npm run build; fi
run "frontend: tests"        npm test

# ---------- Secret / environment checks (S1-008) ----------
echo "=== Secrets and config ==="
cd "$ROOT" || exit 2

tracked_secrets() {
  local hits
  hits="$(git ls-files | grep -Ei '(^|/)\.env($|\.)|(^|/)secrets/|firebase-admin|service-account' | grep -v '\.env\.example$')"
  [ -z "$hits" ] || { echo "$hits"; return 1; }
}
run "secrets: no env/secret files tracked" tracked_secrets

history_secrets() {
  local hits
  hits="$(git log --all --oneline -- '*.env' 'backend/secrets/*' '*firebase-adminsdk*' '*service-account*.json' | head)"
  [ -z "$hits" ] || { echo "$hits"; return 1; }
}
run "secrets: none in git history" history_secrets

missing_config_is_clear() {
  cd "$ROOT/backend" || return 1
  # shellcheck disable=SC1091
  source .venv/bin/activate
  local out
  out="$(DATABASE_URL= FIREBASE_PROJECT_ID= FIREBASE_CREDENTIALS_PATH= REVIEW_PROVIDER_API_KEY= \
         python -m app.config 2>&1)"
  local code=$?
  [ $code -ne 0 ] || { echo "app.config succeeded with blank config"; return 1; }
  for name in DATABASE_URL FIREBASE_PROJECT_ID FIREBASE_CREDENTIALS_PATH REVIEW_PROVIDER_API_KEY; do
    echo "$out" | grep -q "$name" || { echo "message does not name $name"; return 1; }
  done
}
run "secrets: missing backend config names variables" missing_config_is_clear

if [ "$QUICK" = 1 ] || [ ! -d "$ROOT/frontend/dist" ]; then
  skip "secrets: no secrets in frontend bundle"
else
  bundle_clean() {
    ! grep -rEi 'REVIEW_PROVIDER|firebase-admin|private_key|DATABASE_URL' "$ROOT/frontend/dist"
  }
  run "secrets: no secrets in frontend bundle" bundle_clean
fi

# ---------- Summary ----------
echo
echo "================ SUMMARY ================"
for r in "${RESULTS[@]}"; do
  printf '%-5s %s\n' "${r%%|*}" "${r#*|}"
done
echo "========================================="
if [ "$FAILED" = 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED"; fi
echo "Logs: $LOG_DIR"
exit "$FAILED"