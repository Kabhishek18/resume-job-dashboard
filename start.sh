#!/usr/bin/env bash
# Start FastAPI (backend-ai) and Next.js (frontend) for local development.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UVICORN_PID=""

# Override with JOB_RESUME_BACKEND_CONDA_ENV=myenv ./start.sh
CONDA_ENV_NAME="${JOB_RESUME_BACKEND_CONDA_ENV:-job-resume-backend}"

cleanup() {
  if [[ -n "$UVICORN_PID" ]] && kill -0 "$UVICORN_PID" 2>/dev/null; then
    kill "$UVICORN_PID" 2>/dev/null || true
    wait "$UVICORN_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

ensure_conda_backend() {
  if ! command -v conda &>/dev/null; then
    echo "" >&2
    echo "  ERROR: conda not found on PATH." >&2
    echo "" >&2
    echo "  Install Miniconda or Anaconda, then open a new terminal and run ./start.sh again:" >&2
    echo "    https://docs.conda.io/en/latest/miniconda.html" >&2
    echo "" >&2
    exit 1
  fi

  # shellcheck disable=SC1091
  eval "$(conda shell.bash hook)"

  local has_env=0
  if conda run -n "$CONDA_ENV_NAME" true 2>/dev/null; then
    has_env=1
  fi

  if [[ "$has_env" -eq 1 ]]; then
    if ! conda run -n "$CONDA_ENV_NAME" python -c 'import sys; exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      echo "ERROR: conda env \"$CONDA_ENV_NAME\" exists but Python is < 3.10 (python-jobspy needs 3.10+)." >&2
      echo "  Recreate: conda env remove -n \"$CONDA_ENV_NAME\" -y && \"$ROOT/start.sh\"" >&2
      exit 1
    fi
    echo "    Backend conda: $CONDA_ENV_NAME ($(conda run -n "$CONDA_ENV_NAME" python -c 'import sys; print("%d.%d" % sys.version_info[:2])'))" >&2
  else
    echo "    Creating conda env: $CONDA_ENV_NAME (python=3.11) — this may take a minute…" >&2
    conda create -n "$CONDA_ENV_NAME" python=3.11 -y -q
    echo "    Backend conda: $CONDA_ENV_NAME (3.11)" >&2
  fi

  conda activate "$CONDA_ENV_NAME"
}

echo "==> Backend: backend-ai (uvicorn)"
ensure_conda_backend
cd "$ROOT/backend-ai"
echo "    Installing Python dependencies (pip -q)…" >&2
pip install -qr requirements.txt
pip install -q --no-deps -r requirements-jobspy.txt
if ! python -c "import jobspy" 2>/dev/null; then
  echo "ERROR: python-jobspy failed to import after pip install." >&2
  exit 1
fi
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 &
UVICORN_PID=$!
echo "    Uvicorn PID $UVICORN_PID — http://127.0.0.1:8000/docs"

echo "==> Frontend: frontend (next dev)"
cd "$ROOT/frontend"
# Next 16+ dev expects .next/dev/routes-manifest.json. A prior `next build` or a
# crashed dev server can leave .next/dev incomplete → ENOENT routes-manifest and GET / 500.
if [[ -d .next/dev ]] && [[ ! -f .next/dev/routes-manifest.json ]]; then
  echo "    Removing incomplete .next (missing dev routes-manifest)…" >&2
  rm -rf .next
fi
if [[ ! -d node_modules ]]; then
  npm install
fi
if [[ ! -f .env.local ]] && [[ -f .env.example ]]; then
  cp .env.example .env.local
  echo "    Created .env.local from .env.example"
fi
npm run dev
