#!/usr/bin/env bash
set -euo pipefail

# -----------------------------
# Config (you can tweak defaults)
# -----------------------------
DEFAULT_PIPER_MODEL_NAME="en_US-libritts_r-medium"
# Direct file URLs for convenience (from piper-samples)
PIPER_ONNX_URL_DEFAULT="https://github.com/rhasspy/piper/releases/download/v0.0.2-voices/${DEFAULT_PIPER_MODEL_NAME}.onnx"
PIPER_JSON_URL_DEFAULT="https://github.com/rhasspy/piper/releases/download/v0.0.2-voices/${DEFAULT_PIPER_MODEL_NAME}.onnx.json"
# Allow override via env
PIPER_ONNX_URL="${PIPER_ONNX_URL:-$PIPER_ONNX_URL_DEFAULT}"
PIPER_JSON_URL="${PIPER_JSON_URL:-$PIPER_JSON_URL_DEFAULT}"

WITH_MODEL="${WITH_MODEL:-true}"     # set to "false" to skip piper model download
PYTHON_BIN="${PYTHON_BIN:-python3}"  # or "python" if you prefer

# -----------------------------
# Helpers
# -----------------------------
log() { echo -e "\033[1;32m[+] $*\033[0m"; }
warn() { echo -e "\033[1;33m[!] $*\033[0m"; }
err() { echo -e "\033[1;31m[✗] $*\033[0m" >&2; }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

detect_os() {
  if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "linux"
  elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macos"
  else
    echo "unknown"
  fi
}

detect_pkg_mgr() {
  # Linux: prefer apt, then dnf, then yum, then pacman
  if have_cmd apt; then echo "apt"
  elif have_cmd dnf; then echo "dnf"
  elif have_cmd yum; then echo "yum"
  elif have_cmd pacman; then echo "pacman"
  else echo "none"; fi
}

ensure_dir_structure() {
  mkdir -p models/piper
}

create_venv() {
  if [[ ! -d "venv" ]]; then
    log "Creating Python venv"
    "$PYTHON_BIN" -m venv venv
  else
    log "venv exists — skipping"
  fi
  # shellcheck disable=SC1091
  source venv/bin/activate
  python -m pip install --upgrade pip
}

install_portaudio_deps_unix() {
  local os="$1"
  if [[ "$os" == "linux" ]]; then
    local mgr
    mgr="$(detect_pkg_mgr)"
    case "$mgr" in
      apt)
        log "Installing PyAudio build deps via apt"
        sudo apt update -y
        sudo apt install -y build-essential portaudio19-dev python3-dev
        ;;
      dnf)
        log "Installing PyAudio build deps via dnf"
        sudo dnf install -y portaudio-devel gcc python3-devel
        ;;
      yum)
        log "Installing PyAudio build deps via yum"
        sudo yum install -y portaudio-devel gcc python3-devel
        ;;
      pacman)
        log "Installing PyAudio build deps via pacman"
        sudo pacman -Sy --noconfirm portaudio python
        ;;
      *)
        warn "Unknown package manager — skipping system deps. If PyAudio fails, install PortAudio headers manually."
        ;;
    esac
  elif [[ "$os" == "macos" ]]; then
    if have_cmd brew; then
      log "Installing PortAudio via Homebrew"
      brew install portaudio
      # Make headers visible to pip if needed
      export CFLAGS="${CFLAGS:-} -I$(brew --prefix)/include"
      export LDFLAGS="${LDFLAGS:-} -L$(brew --prefix)/lib"
    else
      warn "Homebrew not found. Install Homebrew or PortAudio manually if PyAudio fails."
    fi
  fi
}

install_pyaudio() {
  log "Installing PyAudio (pip)"
  pip install --upgrade pip wheel
  pip install pyaudio
}

gpu_vendor() {
  # Returns: "nvidia" | "amd" | "integrated"
  local os; os="$(detect_os)"
  if [[ "$os" == "linux" ]]; then
    if have_cmd lspci; then
      local out; out="$(lspci -nn | grep -Ei 'vga|3d|display' || true)"
      if echo "$out" | grep -qi nvidia; then echo "nvidia" && return
      fi
      if echo "$out" | grep -qi 'amd|ati'; then echo "amd" && return
      fi
      # Intel iGPU or unknown → integrated
      echo "integrated" && return
    else
      warn "lspci not found; assuming integrated"
      echo "integrated" && return
    fi
  elif [[ "$os" == "macos" ]]; then
    # macOS (Apple Silicon or Intel iGPU) → treat as integrated for this project
    echo "integrated" && return
  fi
  echo "integrated"
}

install_torch_by_vendor() {
  local vendor; vendor="$(gpu_vendor)"
  log "Detected GPU: $vendor"

  case "$vendor" in
    amd)
      # ROCm nightly 6.4 as requested in your mock; change if you want stable
      log "Installing PyTorch for AMD ROCm (rocm6.4 nightly)"
      pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/rocm6.4/
      ;;
    nvidia)
      # Let pip resolve a suitable CUDA wheel automatically
      log "Installing PyTorch for NVIDIA"
      pip install torch torchvision torchaudio
      ;;
    integrated|*)
      log "Installing CPU-only PyTorch"
      pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cpu
      ;;
  esac
}

pip_requirements() {
  if [[ -f requirements.txt ]]; then
    log "Installing Python dependencies from requirements.txt"
    pip install -r requirements.txt
  else
    warn "requirements.txt not found — skipping"
  fi
}

ollama_pull() {
  if have_cmd ollama; then
    log "Pulling Ollama model codegemma:7b-instruct-q5_K_M"
    ollama pull codegemma:7b-instruct-q5_K_M || warn "ollama pull failed (is ollama running?)"
  else
    warn "ollama not found — skipping ollama pull"
  fi
}

download_piper_model() {
  if [[ "$WITH_MODEL" != "true" ]]; then
    log "Skipping Piper model download (WITH_MODEL=false)"
    return
  fi

  local dest="models/piper"
  local onnx_path="$dest/${DEFAULT_PIPER_MODEL_NAME}.onnx"
  local json_path="$dest/${DEFAULT_PIPER_MODEL_NAME}.onnx.json"

  log "Downloading Piper model to $dest"
  if ! have_cmd curl && ! have_cmd wget; then
    warn "Neither curl nor wget found; skipping model download."
    return
  fi

  if [[ ! -f "$onnx_path" ]]; then
    if have_cmd curl; then curl -L "$PIPER_ONNX_URL" -o "$onnx_path"
    else wget -O "$onnx_path" "$PIPER_ONNX_URL"
    fi
  else
    log "ONNX already present — $onnx_path"
  fi

  if [[ ! -f "$json_path" ]]; then
    if have_cmd curl; then curl -L "$PIPER_JSON_URL" -o "$json_path"
    else wget -O "$json_path" "$PIPER_JSON_URL"
    fi
  else
    log "JSON already present — $json_path"
  fi
}

make_env_from_example() {
  if [[ ! -f ".env.example" ]]; then
    warn ".env.example not found — will generate a minimal .env"
    cat > .env <<EOF
# Generated by install.sh
PIPER_MODEL_1=
PIPER_MODEL_2=
OLLAMA_MODEL=codegemma:7b-instruct-q5_K_M
EOF
    return
  fi

  if [[ -f ".env" ]]; then
    log ".env already exists — updating model entries"
    # fallthrough to update below
  else
    log "Creating .env from .env.example"
    cp .env.example .env
  fi

  # Pick up to two models available in models/piper (by basename without path)
  mapfile -t models < <(find models/piper -maxdepth 1 -type f -name "*.onnx" -printf "%f\n" 2>/dev/null || true)
  local m1="${models[0]:-}"
  local m2="${models[1]:-}"

  # Ensure lines exist and are updated
  grep -q '^PIPER_MODEL_1=' .env || echo "PIPER_MODEL_1=" >> .env
  grep -q '^PIPER_MODEL_2=' .env || echo "PIPER_MODEL_2=" >> .env
  grep -q '^OLLAMA_MODEL='  .env || echo "OLLAMA_MODEL="  >> .env

  sed -i.bak -E "s|^PIPER_MODEL_1=.*|PIPER_MODEL_1=${m1}|g" .env
  sed -i.bak -E "s|^PIPER_MODEL_2=.*|PIPER_MODEL_2=${m2}|g" .env
  sed -i.bak -E "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=codegemma:7b-instruct-q5_K_M|g" .env
  rm -f .env.bak

  log "Set PIPER_MODEL_1='${m1}' PIPER_MODEL_2='${m2}' in .env"
}

usage() {
  cat <<EOF
Usage: $0 [--no-model] [--python PYBIN]

Options:
  --no-model        Skip Piper model download
  --python PYBIN    Python binary to use (default: python3)
Env overrides:
  WITH_MODEL=true|false
  PIPER_ONNX_URL=
  PIPER_JSON_URL=
EOF
}

main() {
  local os; os="$(detect_os)"
  if [[ "${1:-}" == "--help" ]]; then usage; exit 0; fi

  # Parse simple flags
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-model) WITH_MODEL="false"; shift ;;
      --python) PYTHON_BIN="$2"; shift 2 ;;
      *) usage; exit 1 ;;
    esac
  done

  log "OS detected: $os"
  ensure_dir_structure
  create_venv
  install_portaudio_deps_unix "$os"
  install_pyaudio
  install_torch_by_vendor
  pip_requirements
  ollama_pull
  download_piper_model
  make_env_from_example
  log "All done ✅"
}

main "$@"

