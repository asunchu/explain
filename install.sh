#!/usr/bin/env bash
# Install Explain from a checkout, or bootstrap a complete GitHub snapshot.
set -euo pipefail

REPOSITORY="asunchu/explain"
REF="${EXPLAIN_REF:-main}"
DRY_RUN=0
NO_SYSTEM_DEPS=0
CORE_ONLY=0
FORWARD_ARGS=()
SOURCE_ROOT=""
TEMP_ROOT=""
PYTHON_BIN=""
MISSING=()

say() { printf '%s\n' "$*"; }
fail() { printf 'Explain installer: %s\n' "$*" >&2; exit 1; }

cleanup() {
  if [[ -n "$TEMP_ROOT" && -d "$TEMP_ROOT" ]]; then
    rm -rf -- "$TEMP_ROOT"
  fi
}
trap cleanup EXIT

for argument in "$@"; do
  case "$argument" in
    --dry-run) DRY_RUN=1; FORWARD_ARGS+=("$argument") ;;
    --no-system-deps) NO_SYSTEM_DEPS=1 ;;
    --core-only) CORE_ONLY=1; FORWARD_ARGS+=("$argument") ;;
    *) FORWARD_ARGS+=("$argument") ;;
  esac
done

# BASH_SOURCE is empty when the bootstrap is piped into bash.
script_path="${BASH_SOURCE[0]:-}"
if [[ -n "$script_path" && -f "$script_path" ]]; then
  script_directory="$(cd -- "$(dirname -- "$script_path")" && pwd -P)"
  if [[ -f "$script_directory/skills/explain/SKILL.md" && -d "$script_directory/scripts" ]]; then
    SOURCE_ROOT="$script_directory"
  fi
fi

find_python() {
  local candidate
  PYTHON_BIN=""
  for candidate in python3.11 python3.12 python3.13 python3 \
    /opt/homebrew/opt/python@3.11/bin/python3.11 \
    /usr/local/opt/python@3.11/bin/python3.11; do
    if command -v "$candidate" >/dev/null 2>&1 && \
      "$candidate" -c 'import sys, venv, ensurepip; sys.exit(0 if (3, 11) <= sys.version_info[:2] <= (3, 13) else 1)' >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v "$candidate")"
      return 0
    fi
  done
  return 1
}

node_supported() {
  local version major minor
  command -v node >/dev/null 2>&1 || return 1
  command -v npm >/dev/null 2>&1 || return 1
  version="$(node --version 2>/dev/null)" || return 1
  if [[ "$version" =~ ^v([0-9]+)\.([0-9]+)\. ]]; then
    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    [[ "$major" -gt 22 || ( "$major" -eq 22 && "$minor" -ge 20 ) ]]
  else
    return 1
  fi
}

check_prerequisites() {
  MISSING=()
  if [[ "$CORE_ONLY" -eq 0 ]]; then
    node_supported || MISSING+=("Node.js >= 22.20 with npm")
  fi
  find_python || MISSING+=("Python 3.11-3.13 (3.11 preferred)")
  if [[ "$CORE_ONLY" -eq 0 ]]; then
    command -v ffmpeg >/dev/null 2>&1 || MISSING+=("ffmpeg")
    command -v ffprobe >/dev/null 2>&1 || MISSING+=("ffprobe")
  fi
}

describe_missing() {
  local dependency
  for dependency in "${MISSING[@]}"; do
    say "  - $dependency"
  done
}

install_system_dependencies() {
  local operating_system linux_id key value
  operating_system="$(uname -s)"
  case "$operating_system" in
    Darwin)
      command -v brew >/dev/null 2>&1 || \
        fail "Homebrew is required to install missing macOS dependencies. Install Homebrew from https://brew.sh, then rerun this command."
      local packages=()
      if [[ "$CORE_ONLY" -eq 0 ]]; then node_supported || packages+=(node@22); fi
      find_python || packages+=(python@3.11)
      if [[ "$CORE_ONLY" -eq 0 ]] && { ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; }; then
        packages+=(ffmpeg)
      fi
      say "Installing missing dependencies with Homebrew: ${packages[*]}"
      brew install "${packages[@]}" || fail "Homebrew could not install the required dependencies."
      # Versioned Homebrew packages can be installed without being linked.
      local node_prefix
      node_prefix="$(brew --prefix node@22 2>/dev/null || true)"
      if [[ -n "$node_prefix" && -x "$node_prefix/bin/node" ]]; then
        export PATH="$node_prefix/bin:$PATH"
      fi
      ;;
    Linux)
      linux_id=""
      if [[ -r /etc/os-release ]]; then
        while IFS='=' read -r key value; do
          if [[ "$key" == ID ]]; then
            linux_id="${value#\"}"
            linux_id="${linux_id%\"}"
          fi
        done < /etc/os-release
      fi
      [[ "$linux_id" == ubuntu || "$linux_id" == debian ]] || \
        fail "Automatic Linux setup requires Ubuntu or Debian with apt-get. Install the listed dependencies, then rerun with --no-system-deps."
      command -v apt-get >/dev/null 2>&1 || fail "apt-get is required to install missing Linux dependencies."
      local apt_command=() packages=()
      if [[ "$EUID" -ne 0 ]]; then
        command -v sudo >/dev/null 2>&1 || fail "sudo is required for apt-get. Install the listed dependencies as an administrator."
        sudo -n true 2>/dev/null || \
          fail "apt-get needs administrator access. Run sudo -v in your terminal, then rerun this command. The installer does not request or read passwords."
        apt_command=(sudo -n)
      fi
      if [[ "$CORE_ONLY" -eq 0 ]]; then node_supported || packages+=(nodejs npm); fi
      find_python || packages+=(python3.11 python3.11-venv)
      if [[ "$CORE_ONLY" -eq 0 ]] && { ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; }; then
        packages+=(ffmpeg)
      fi
      say "Installing missing dependencies with apt-get: ${packages[*]}"
      ${apt_command[@]+"${apt_command[@]}"} apt-get update || fail "apt-get could not update its package index."
      ${apt_command[@]+"${apt_command[@]}"} apt-get install -y "${packages[@]}" || \
        fail "apt-get could not install the required packages. Your configured repositories must provide Node.js >= 22.20 and Python 3.11-3.13. Install supported versions, then rerun."
      ;;
    *)
      fail "Automatic dependency setup is supported on macOS, Ubuntu, and Debian. Install the listed dependencies, then rerun with --no-system-deps."
      ;;
  esac
}

# Discover common unlinked Homebrew Node installations without running brew.
if ! node_supported; then
  for node_directory in /opt/homebrew/opt/node@22/bin /usr/local/opt/node@22/bin; do
    if [[ -x "$node_directory/node" && -x "$node_directory/npm" ]]; then
      export PATH="$node_directory:$PATH"
      node_supported && break
    fi
  done
fi

check_prerequisites
if [[ "${#MISSING[@]}" -gt 0 ]]; then
  say "Missing or unsupported prerequisites:"
  describe_missing
  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ "$NO_SYSTEM_DEPS" -eq 1 ]]; then
      fail "--no-system-deps prevents automatic prerequisite installation."
    fi
    say "Dry run: would install missing prerequisites with the existing system package manager."
    if [[ -z "$SOURCE_ROOT" ]]; then
      say "Dry run: would download the complete $REPOSITORY snapshot at $REF."
    fi
    say "Dry run: would run scripts/install.py with the supplied arguments after prerequisites are available."
    exit 0
  fi
  [[ "$NO_SYSTEM_DEPS" -eq 0 ]] || fail "--no-system-deps prevents automatic prerequisite installation."
  install_system_dependencies
  check_prerequisites
  if [[ "${#MISSING[@]}" -gt 0 ]]; then
    say "The package manager did not provide supported prerequisites:"
    describe_missing
    fail "Install supported versions, then rerun. Node.js must be >= 22.20; Python must be 3.11-3.13."
  fi
fi

if [[ -z "$SOURCE_ROOT" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    say "Dry run: would resolve $REPOSITORY at $REF to a commit, then download its complete GitHub snapshot."
    say "Dry run: would run scripts/install.py with the supplied arguments. No files were created."
    exit 0
  fi
  command -v curl >/dev/null 2>&1 || fail "curl is required to download the source snapshot."
  command -v tar >/dev/null 2>&1 || fail "tar is required to extract the source snapshot."
  encoded_ref="$("$PYTHON_BIN" -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$REF")"
  resolved_ref="$REF"
  if [[ ! "$REF" =~ ^[0-9a-fA-F]{40}$ ]]; then
    if commit_metadata="$(curl --fail --silent --show-error --location --retry 2 --connect-timeout 15 \
      "https://api.github.com/repos/$REPOSITORY/commits/$encoded_ref" 2>/dev/null)"; then
      commit_sha="$(printf '%s' "$commit_metadata" | "$PYTHON_BIN" -c 'import json, re, sys; value = json.load(sys.stdin).get("sha", ""); print(value if re.fullmatch(r"[0-9a-f]{40}", value) else "")' 2>/dev/null)" || commit_sha=""
      if [[ -n "$commit_sha" ]]; then
        resolved_ref="$commit_sha"
      fi
    fi
  fi
  export EXPLAIN_SOURCE_REF="$resolved_ref"
  encoded_ref="$("$PYTHON_BIN" -c 'import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1], safe=""))' "$resolved_ref")"
  TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/explain-install.XXXXXX")"
  SOURCE_ROOT="$TEMP_ROOT/source"
  mkdir -- "$SOURCE_ROOT"
  say "Downloading $REPOSITORY at $resolved_ref."
  curl --fail --silent --show-error --location --retry 2 --connect-timeout 15 \
    "https://codeload.github.com/$REPOSITORY/tar.gz/$encoded_ref" \
    --output "$TEMP_ROOT/source.tar.gz" || fail "Could not download the complete source snapshot. Check EXPLAIN_REF and your network connection."
  tar -xzf "$TEMP_ROOT/source.tar.gz" --strip-components=1 -C "$SOURCE_ROOT" || \
    fail "Could not extract the source snapshot."
fi

[[ -f "$SOURCE_ROOT/scripts/install.py" ]] || fail "The selected source does not contain scripts/install.py. Select a release or commit with the installer."
"$PYTHON_BIN" "$SOURCE_ROOT/scripts/install.py" ${FORWARD_ARGS[@]+"${FORWARD_ARGS[@]}"}
