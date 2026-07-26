# CLAUDE.md — Project JARVIS

## What This Is

AI assistant daemon with LLM orchestration, MCP tool dispatch, and multiple
interface layers (TUI, CLI, voice, socket). The LLM reasons about what tools
it needs, discovers them via semantic search, and executes them in parallel
through a Rust orchestrator.

## Ecosystem Overview

```
Project-JARVIS (Python)     — daemon, LLM orchestration, interfaces
  jarvis/dispatch/          — Python adapter wrapping the Rust dispatch binary
  jarvis/core/              — security, confirmation, logging, I/O
  jarvis/tui/               — Textual TUI (decomposed into ~12 modules)
  jarvis/llm/               — provider-agnostic LLM layer (Ollama local + OpenAI-compatible API providers, ProviderPool failover)
  jarvis/voice/             — STT (Vosk) + TTS (Piper)
  jarvis/sessions/          — session persistence
  jarvis/runtime/           — event loop, action handlers
  jarvis/contextor/         — adapter + embeddings for the Rust contextor memory binary
  jarvis/platform/          — OS abstraction (Linux/macOS/Windows: data dirs, IPC hardening + accept-time peer auth, askpass/elevation, sidecar resolution)
  jarvis/server/            — opt-in OpenAI-compatible HTTP endpoint (`openai_compat.py`, off by default)

deps/rust/dispatch          — Rust signal-driven MCP task orchestrator
deps/rust/dmcp              — Rust MCP server manager (package manager for MCP)
deps/rust/contextor         — Rust vector-based long-term memory store
mcp-registry                — JSON registry of installable MCP servers
jarvisos-app                — Desktop GUI (Rust + CXX-Qt + Qt6/QML)
jarvisos                    — AI-native Linux distro (Arch base + custom kernel)
```

### Dispatch: Python wrapper vs Rust engine

Two things share the name "dispatch":

| Layer | Location | Language | Role |
|-------|----------|----------|------|
| Interface | `jarvis/dispatch/` | Python | Wraps the Rust binary, translates Python calls to MCP JSON-RPC, surfaces signals to the event loop |
| Engine | `deps/rust/dispatch` (submodule) | Rust/Tokio | Spawns MCP tool calls in parallel, tracks PIDs, fires INIT/EXIT/REMIND/WAIT/KILL signals |

One-liner: **Python dispatch wraps Rust dispatch.** The Python package
docstring (`jarvis/dispatch/__init__.py`) documents this boundary.

---

## Tool Discovery Flow

The LLM uses a multi-step flow to find and invoke tools:

1. **`search_tools`** — LLM derives a capability from the user's request,
   system does embedding search on the vector index
2. **`get_server_docs`** — LLM picks a server from results, system returns
   full tool list + param schemas
3. **`install_server`** / **`configure_server`** — if the server isn't installed
   or needs configuration
4. **`dispatch`** — LLM dispatches concrete tool calls for parallel execution

Key: the LLM derives *capability*, not keywords. "check my python version" →
`{"action": "search_tools", "capability": "execute shell commands"}`.

---

## Security Architecture

### TLA (Threat Level Access) — 4-tier policy

Behaviour in `smart` mode, per `confirmation_manager.should_confirm`:

| Tier | Behaviour |
|------|-----------|
| SAFE | Runs without prompting |
| ELEVATED | Blocked pending user confirmation |
| DANGEROUS | Blocked pending user confirmation |
| FORBIDDEN | Blocked pending user confirmation |

There is no separate audit log and no unconditional FORBIDDEN block:
`allow_all` bypasses ALL tiers including FORBIDDEN (documented risk).

### Confirmation Modes

`CONFIRMATION_MODE` in config controls the confirmation gate:

| Mode | Behaviour |
|------|-----------|
| `allow_all` | No prompts, everything auto-approved (bypasses all tiers) |
| `smart` | Ask when the TLA classifier rates the call >= ELEVATED: max(host floor for always-dangerous tools, manifest-declared `threat_level` / legacy `confirmation_required`, dangerous-payload scan of params) |
| `ask_all` | Confirm every tool call |

### Confirmation Channels

The `ConfirmationManager` (core) is interface-agnostic. It routes confirmation
requests to the best available channel:

1. **TUI modal** — `ConfirmModal` in Textual (Y/N inline)
2. **Desktop notification** — `notify-send` with Allow/Deny actions
3. **Socket** — JSON over output socket for external clients
4. **CLI prompt** — stdin `[y/N]` fallback

Pending confirmations are tracked in a persistent, queryable list
(`ConfirmationManager.list_pending()`), reviewable anytime via `jarvis
confirmations` (CLI) or `list_confirmations`/`approve_confirmation`/
`deny_confirmation`/`approve_all_confirmations` (GUI socket) rather than
expiring on a clock. `CONFIRMATION_TIMEOUT` defaults to `0` (disabled);
set it > 0 to restore auto-deny for unattended/headless setups.

### Socket Security

`socket_security.py` hardens the three IPC endpoints under `JARVIS_DATA_DIR`
(platform data dir, e.g. `~/.jarvis/`): `input.sock`, `output.sock`, and
`jarvis.sock` (GUI) — overridable via `JARVIS_INPUT_SOCKET` /
`JARVIS_OUTPUT_SOCKET` / `JARVIS_GUI_SOCKET`:
- `harden_socket_path()` — platform-delegated (0600 on Linux/macOS, localhost TCP on Windows)
- `verify_socket_ownership()` — checks UID before connecting
- `warn_if_allow_all()` — logs warning when confirmation is disabled

### Output-Provenance Boundary (Prompt Injection)

dispatch wraps every tool output in a per-task 128-bit CSPRNG-nonce-keyed tag
(`[hash=<H>] <<H>>...</<H>>`); the daemon verifies EXIT bodies via
`jarvis/dispatch/boundary.py:verify_boundary()` and treats missing or
mismatched wrappers as untrusted (Threat #2 mitigation, #165).

### Sudo Management

`jarvis sudo enable/disable` (`jarvis/core/sudo_manager.py`, #158) manages a
password-required, visudo-validated `/etc/sudoers.d/jarvis` drop-in (atomic
install) — Linux only; macOS/Windows report "not granted" rather than managing
sudoers.

Shell servers are installed from the MCP registry, not bundled here. A
user-scope shell server that escalates a privileged command via `sudo -A` has
its askpass helper resolved **per OS** through the platform layer
(`BasePlatform.find_askpass()` / `askpass_helpers()`), so the GUI password
prompt stays the boundary on every platform:

| OS | Askpass resolution |
|----|--------------------|
| Linux | probes five candidates in priority order — `/usr/bin/ksshaskpass`, `/usr/lib/ssh/ksshaskpass`, `ssh-askpass`, `lxqt-openssh-askpass`, `x11-ssh-askpass`; `elevate()` raises with the full candidate list if none is installed |
| macOS | no CLI askpass ships with the OS, so `find_askpass()` installs an `osascript`-backed shim at `/usr/local/libexec/jarvis-osascript-askpass` that presents the same interface (native "with administrator privileges" dialog) |
| Windows | no askpass — elevation is a UAC consent prompt, so `askpass_helpers()` is empty |

---

## Packaging

### Install Extras

| Extra | What it adds |
|-------|-------------|
| `project-jarvis` | Core daemon (text I/O, LLM, dispatch) |
| `project-jarvis[tui]` | Textual TUI (`jarvis tui`) |
| `project-jarvis[voice-input]` | Vosk STT only |
| `project-jarvis[voice-output]` | Piper TTS only |
| `project-jarvis[voice]` | Vosk STT + Piper TTS |
| `project-jarvis[voice-aec]` | Voice + acoustic echo cancellation (native-compiled, barge-in fix) |
| `project-jarvis[dev]` | pytest, black, isort, flake8, mypy, pre-commit |
| `project-jarvis[docs]` | Documentation tools (sphinx) |
| `project-jarvis[all]` | tui + voice-aec + dev + docs |

### Rust Dependencies

Submodules under `deps/rust/` — dispatch, dmcp, contextor. Build with
`cargo build --release` in each directory. Binaries must be on PATH.

## LLM Providers

Shipped (#78): `ProviderPool` (`jarvis/llm/provider_pool.py`) is built from
`providers.json` at startup (`ComponentFactory._build_provider_pool()`), walks
providers in priority order, and fails over with per-error cooldowns
(429 → 60 s, 402 → 1 h, 401/403 → permanent, 5xx/timeout → 30 s) plus
automatic restore when a cooldown expires.

---

## Build & Test

```bash
pip install -e ".[all]"     # Install with all extras
make check                  # Format + lint + typecheck + tests
```

## Conventions

- **Python**: Black formatting, type hints on public functions
- **Rust**: `cargo fmt` + `cargo clippy` clean before pushing
- **Commit messages**: imperative mood
- **No comments** explaining what code does; only non-obvious WHY
- **No backwards-compat shims**: delete unused code outright
- Prefer editing existing files over creating new ones

---

## Key Files

| Path | Purpose |
|------|---------|
| `jarvis/main.py` | Daemon entry point |
| `jarvis/cli.py` | CLI entry point |
| `jarvis/config.py` | Global configuration |
| `jarvis/tui/app.py` | Textual app shell |
| `jarvis/tui/lifecycle.py` | App startup/shutdown, callback registration |
| `jarvis/tui/confirm_modal.py` | Tool confirmation modal |
| `jarvis/tui/config_modal.py` | Tabbed config/provider settings modal (F2 / /settings) |
| `jarvis/tui/provider_modal.py` | Provider add/edit modal |
| `jarvis/core/confirmation_manager.py` | Multi-channel confirmation gate |
| `jarvis/core/socket_security.py` | Socket hardening |
| `jarvis/core/sudo_manager.py` | `jarvis sudo` — sudoers drop-in management (#158) |
| `jarvis/dispatch/boundary.py` | Output-provenance boundary verification (#165) |
| `jarvis/core/command_parser.py` | LLM response parser + action registry |
| `jarvis/core/voice_state.py` | `VoiceState` — formal voice/response session state machine |
| `jarvis/voice/chime.py` | Wake-word earcon: path validation + best-effort playback |
| `jarvis/voice/audio.py` | Audio device detection + `passes_noise_gate` RMS filter |
| `jarvis/voice/aec/webrtc_aec.py` | `WebRtcAEC` — acoustic echo cancellation (barge-in fix, #143) |
| `jarvis/runtime/io.py` | Input/GUI/output sockets — confirmation queries, session CRUD, settings + provider CRUD, client labeling/`list_clients`/`shutdown_request` |
| `jarvis/runtime/lifecycle.py` | Signal handlers, startup service wiring, `shutdown_request`'s safe save-then-exit sequence |
| `jarvis/dispatch/goal_manager.py` | `GoalManager` — goal tree + on-disk archive (`archive_all()` for shutdown) |
| `jarvis/core/providers.py` | Provider pool CRUD (`providers.json`), shared by CLI, TUI, and the GUI socket |
| `jarvis/dispatch/adapter.py` | Python wrapper for Rust dispatch binary |
| `jarvis/dispatch/discovery.py` | Embedding search via dmcp vector index |
| `jarvis/dispatch/dmcp_registry.py` | dmcp CLI wrappers (install, tools, config) |
| `jarvis/dispatch/event_merger.py` | Merges voice/CLI/socket/dispatch events |
| `jarvis/runtime/root_actions.py` | ROOT-mode LLM response action handlers |
| `jarvis/runtime/root_context.py` | Context assembly for ROOT-mode prompts |
| `jarvis/runtime/llm_bridge.py` | `ask_llm()` — the sole locked/mode-atomic LLM call site |
| `jarvis/runtime/events.py` | Event routing + per-event task tracking (concurrent goals) |

---

## Changelog — corrected claims

*2026-07-22:* extras renamed to `project-jarvis` and completed (voice-input/voice-output/docs); tier table rewritten to match `should_confirm` (ELEVATED confirms, no audit log, no unconditional FORBIDDEN — `allow_all` bypasses all tiers); `smart` mode described as the TLA classifier (max of host floor, manifest level, payload scan); LLM layer documented as provider-agnostic with the shipped failover pool (#78 moved out of Planned Work); socket security corrected to the three `JARVIS_DATA_DIR` endpoints; added Output-Provenance Boundary (#165), Sudo Management (#158), `jarvis/contextor/`, `jarvis/platform/`, and `shellmcp/`.
