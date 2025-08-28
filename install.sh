#!/usr/bin/env bash
# shellcheck disable=SC2317
set -Eeuo pipefail

################################################################################
# Piper/TTS Dev Setup Helper
# - Linux + macOS (Apple Silicon/Intel)
# - Creates venv, installs PyAudio deps, PyTorch (CPU/NVIDIA/AMD), pulls Piper model
#
# Flags:
#   --no-model            Skip Piper model download
#   --python PYBIN        Python executable (default: python3)
#   --venv PATH           Virtualenv path (default: ./venv)
#   --yes                 Assume "yes" to package installs and prompts
#   --quiet               Reduce log noise
#   --help                Show usage
#
# Env overrides:
#   WITH_MODEL=true|false
#   PYTHON_BIN=/path/to/python
#   VENV_PATH=./venv
#   PIPER_MODEL_NAME=en_US-libritts_r-medium
#   PIPER_ONNX_URL=...
#   PIPER_JSON_URL=...
#   PIPER_ONNX_SHA256=...            # optional checksum
#   PIPER_JSON_SHA256=...            # optional checksum
################################################################################

# -----------------------------
# Config (tweakable defaults)
# -----------------------------
DEFAULT_PIPER_MODEL_NAME="${PIPER_MODEL_NAME:-en_US-libritts_r-medium}"

PIPER_ONNX_URL_DEFAULT="https://github.com/rhasspy/piper/releases/download/v0.0.2-voices/${DEFAULT_PIPER_MODEL_NAME}.onnx"
PIPER_JSON_URL_DEFAULT="https://github.com/rhasspy/piper/releases/download/v0.0.2-voices/${DEFAULT_PIPER_MODEL_NAME}.onnx.json"
PIPER_ONNX_URL="${PIPER_ONNX_URL:-$PIPER_ONNX_URL_DEFAULT}"
PIPER_JSON_URL="${PIPER_JSON_URL:-$PIPER_JSON_URL_DEFAULT}"

WITH_MODEL="${WITH_MODEL:-true}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PATH="${VENV_PATH:-venv}"
ASSUME_YES="false"
QUIET="false"

# -----------------------------
# Pretty logging
# -----------------------------
is_tty() { [[ -t 1 ]] && [[ -t 2 ]]; }
color()  { is_tty || { echo -n ""; return; }; printf "\033[%sm" "$1"; }
resetc() { is_tty && printf "\033[0m"; }

log()  { [[ "$QUIET" == "true" ]] && return; printf "%s[+]%s %s\n" "$(color '1;32')" "$(resetc)" "$*"; }
warn() { printf "%s[!]%s %s\n" "$(color '1;33')" "$(resetc)" "$*"; }
err()  { printf "%s[✗]%s %s\n" "$(color '1;31')" "$(resetc)" "$*" >&2; }
die()  { err "$*"; exit 1; }

# -----------------------------
# Traps
# -----------------------------
cleanup() { :; }  # placeholder for future
trap cleanup EXIT
trap 'err "Unexpected error on line $LINENO"; exit 1' ERR

# -----------------------------
# Helpers
# -----------------------------
have_cmd() { command -v "$1" >/dev/null 2>&1; }

confirm() {
  local msg="${1:-Proceed?}"
  if [[ "$ASSUME_YES" == "true" ]]; then return 0; fi
  read -r -p "$msg [y/N] " ans || true
  [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]]
}

detect_os() {
  case "${OSTYPE:-}" in
    linux-gnu*|linux*) echo "linux" ;;
    darwin*)           echo "macos" ;;
    *)                 echo "unknown" ;;
  esac
}

detect_pkg_mgr() {
  if have_cmd apt; then echo "apt"
  elif have_cmd dnf; then echo "dnf"
  elif have_cmd yum; then echo "yum"
  elif have_cmd pacman; then echo "pacman"
  else echo "none"; fi
}

ensure_dir_structure() {
  mkdir -p "models/piper"
}

# BSD vs GNU sed in-place handling
sed_inplace() {
  # Usage: sed_inplace 's/foo/bar/' file
  if sed --version >/dev/null 2>&1; then
    sed -i -E "$1" "$2"
  else
    # macOS/BSD sed requires backup suffix (can be empty with '')
    sed -i '' -E "$1" "$2"
  fi
}

# Safer downloader with retries + resume
_fetch() {
  local url="$1" out="$2"
  if have_cmd curl; then
    curl -fsSL --retry 5 --retry-delay 2 --continue-at - -o "$out" "$url"
  elif have_cmd wget; then
    wget -c -O "$out" "$url"
  else
    return 1
  fi
}

sha256_ok() {
  local file="$1" want="$2"
  [[ -z "$want" ]] && return 0
  local got
  if have_cmd sha256sum; then
    got="$(sha256sum "$file" | awk '{print $1}')"
  elif have_cmd shasum; then
    got="$(shasum -a 256 "$file" | awk '{print $1}')"
  else
    warn "No sha256 tool found; skipping checksum"
    return 0
  fi
  [[ "$got" == "$want" ]]
}

create_venv() {
  if [[ ! -d "$VENV_PATH" ]]; then
    log "Creating Python venv at $VENV_PATH"
    # Ensure venv module exists (especially on Debian/Ubuntu)
    if [[ "$(detect_pkg_mgr)" == "apt" ]] && ! "$PYTHON_BIN" -m venv --help >/dev/null 2>&1; then
      warn "python3-venv not present; installing…"
      sudo apt update -y
      sudo apt install -y python3-venv
    fi
    "$PYTHON_BIN" -m venv "$VENV_PATH"
  else
    log "Using existing venv at $VENV_PATH"
  fi

  # shellcheck disable=SC1090
  source "$VENV_PATH/bin/activate"
  python -m pip install --upgrade pip wheel >/dev/null
}

install_portaudio_deps_unix() {
  local os="$1" mgr
  [[ "$os" == "linux" || "$os" == "macos" ]] || return 0

  if [[ "$os" == "linux" ]]; then
    mgr="$(detect_pkg_mgr)"
    case "$mgr" in
      apt)
        log "Installing PortAudio build deps via apt"
        sudo apt update -y
        sudo apt install -y build-essential portaudio19-dev python3-dev
        ;;
      dnf)
        log "Installing PortAudio build deps via dnf"
        sudo dnf install -y portaudio-devel gcc python3-devel
        ;;
      yum)
        log "Installing PortAudio build deps via yum"
        sudo yum install -y portaudio-devel gcc python3-devel
        ;;
      pacman)
        log "Installing PortAudio build deps via pacman"
        sudo pacman -Sy --noconfirm base-devel portaudio python
        ;;
      *)
        warn "Unknown package manager — skipping system deps. If PyAudio fails, install PortAudio headers manually."
        ;;
    esac
  else
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
  python -m pip install --upgrade pip wheel >/dev/null
  python -m pip install pyaudio
}

gpu_vendor() {
  local os; os="$(detect_os)"

  # Quick wins first
  if have_cmd nvidia-smi; then echo "nvidia" && return; fi
  if [[ "$os" == "macos" ]]; then echo "integrated" && return; fi

  if [[ "$os" == "linux" ]] && have_cmd lspci; then
    local out; out="$(lspci -nn | grep -Ei 'vga|3d|display' || true)"
    if echo "$out" | grep -qi nvidia; then echo "nvidia" && return; fi
    if echo "$out" | grep -qi 'amd|ati'; then echo "amd" && return; fi
    echo "integrated" && return
  fi
  echo "integrated"
}

install_torch_by_vendor() {
  local vendor; vendor="$(gpu_vendor)"
  log "Detected GPU: $vendor"

  case "$vendor" in
    amd)
      log "Installing PyTorch for AMD ROCm (rocm6.4 nightly)"
      python -m pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/rocm6.4/
      ;;
    nvidia)
      log "Installing PyTorch for NVIDIA (pip will pick a compatible CUDA wheel if available)"
      python -m pip install torch torchvision torchaudio
      ;;
    integrated|*)
      log "Installing CPU-only PyTorch"
      python -m pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cpu
      ;;
  esac
}

pip_requirements() {
  if [[ -f requirements.txt ]]; then
    log "Installing Python dependencies from requirements.txt"
    python -m pip install -r requirements.txt
  else
    warn "requirements.txt not found — skipping"
  fi
}

ollama_pull() {
  if have_cmd ollama; then
    log "Pulling Ollama model codegemma:7b-instruct-q5_K_M"
    if ! ollama pull codegemma:7b-instruct-q5_K_M; then
      warn "ollama pull failed (is the daemon running?)"
    fi
  else
    warn "ollama not found — skipping ollama pull"
  fi
}

download_piper_model() {
  [[ "$WITH_MODEL" != "true" ]] && { log "Skipping Piper model download (WITH_MODEL=false)"; return; }

  local dest="models/piper"
  local onnx="$dest/${DEFAULT_PIPER_MODEL_NAME}.onnx"
  local json="$dest/${DEFAULT_PIPER_MODEL_NAME}.onnx.json"

  ensure_dir_structure
  if ! have_cmd curl && ! have_cmd wget; then
    warn "Neither curl nor wget found; skipping model download."
    return
  fi

  log "Downloading Piper model to $dest"
  if [[ ! -s "$onnx" ]]; then
    _fetch "$PIPER_ONNX_URL" "$onnx" || die "Failed to download ONNX model"
  else
    log "ONNX already present — $onnx"
  fi
  if [[ ! -s "$json" ]]; then
    _fetch "$PIPER_JSON_URL" "$json" || die "Failed to download JSON config"
  else
    log "JSON already present — $json"
  fi

  if ! sha256_ok "$onnx" "${PIPER_ONNX_SHA256:-}"; then
    rm -f "$onnx"; die "ONNX checksum mismatch"
  fi
  if ! sha256_ok "$json" "${PIPER_JSON_SHA256:-}"; then
    rm -f "$json"; die "JSON checksum mismatch"
  fi
}

make_env_from_example() {
  if [[ ! -f ".env.example" ]]; then
    warn ".env.example not found — generating a minimal .env"
    cat > .env <<EOF
# Generated by setup script
PIPER_MODEL_1=
PIPER_MODEL_2=
OLLAMA_MODEL=codegemma:7b-instruct-q5_K_M
EOF
  elif [[ ! -f ".env" ]]; then
    log "Creating .env from .env.example"
    cp .env.example .env
  else
    log ".env already exists — will update model entries"
  fi

  # Pick up to two .onnx basenames
  mapfile -t models < <(find models/piper -maxdepth 1 -type f -name "*.onnx" -printf "%f\n" 2>/dev/null || true)
  local m1="${models[0]:-}"
  local m2="${models[1]:-}"

  # Ensure keys exist
  grep -q '^PIPER_MODEL_1=' .env || echo "PIPER_MODEL_1=" >> .env
  grep -q '^PIPER_MODEL_2=' .env || echo "PIPER_MODEL_2=" >> .env
  grep -q '^OLLAMA_MODEL='  .env || echo "OLLAMA_MODEL="  >> .env

  sed_inplace "s|^PIPER_MODEL_1=.*|PIPER_MODEL_1=${m1}|" .env
  sed_inplace "s|^PIPER_MODEL_2=.*|PIPER_MODEL_2=${m2}|" .env
  sed_inplace "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=codegemma:7b-instruct-q5_K_M|" .env

  log "Set PIPER_MODEL_1='${m1:-}' PIPER_MODEL_2='${m2:-}' in .env"
}

usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  --no-model            Skip Piper model download
  --python PYBIN        Python executable to use (default: python3)
  --venv PATH           Virtualenv path (default: ./venv)
  --yes                 Non-interactive; assume "yes" to installs
  --quiet               Reduce log output
  --help                Show this help

Env overrides:
  WITH_MODEL=true|false
  PIPER_MODEL_NAME=…
  PIPER_ONNX_URL=…
  PIPER_JSON_URL=…
  PIPER_ONNX_SHA256=…   # optional
  PIPER_JSON_SHA256=…   # optional
EOF
}

parse_flags() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --no-model) WITH_MODEL="false"; shift ;;
      --python)   PYTHON_BIN="$2"; shift 2 ;;
      --venv)     VENV_PATH="$2"; shift 2 ;;
      --yes)      ASSUME_YES="true"; shift ;;
      --quiet)    QUIET="true"; shift ;;
      --help|-h)  usage; exit 0 ;;
      *)          usage; die "Unknown option: $1" ;;
    esac
  done
}

main() {
  parse_flags "$@"
  local os; os="$(detect_os)"
  [[ "$os" == "unknown" ]] && warn "Unrecognized OS; proceeding with best-effort."

  log "OS detected: $os"
  ensure_dir_structure
  create_venv

  if confirm "Install system PortAudio build deps?"; then
    install_portaudio_deps_unix "$os"
  else
    warn "Skipping system dependency installation"
  fi

  install_pyaudio
  install_torch_by_vendor
  pip_requirements
  ollama_pull
  download_piper_model
  make_env_from_example
  log "All done ✅  (venv: $VENV_PATH)"
}

main "$@"
