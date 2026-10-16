#!/usr/bin/env bash
# aFold21 Colab session helper. Safe to source from interactive shell startup.
set -u

AF21_SESSION="${AF21_SESSION:-alphafold21}"
AF21_AUTH="${AF21_AUTH:-oauth2}"
AF21_GPU="${AF21_GPU:-T4}"
AF21_COLAB_TOKEN="${AF21_COLAB_TOKEN:-$HOME/.config/colab-cli/token.json}"

af21_colab_status() {
  colab --auth="$AF21_AUTH" status -s "$AF21_SESSION" 2>&1
}

af21_colab_session_exists() {
  local output rc
  output="$(af21_colab_status)"; rc=$?
  printf '%s\n' "$output"
  [[ $rc -eq 0 && ! "$output" =~ [Ss]ession[[:space:]]+.*not[[:space:]]+found ]]
}

af21_colab_usage() {
  echo
  echo "========== Colab compute usage =========="
  colab --auth="$AF21_AUTH" usage 2>&1 || true
  echo "[af21] FREE TIER: Google does not publish a fixed compute quota, so percentage remaining is unavailable."
  echo "[af21] A 0.00 compute-unit balance is not a free-tier quota percentage; free access is governed by dynamic limits and availability."
  echo "[af21] This CLI cannot calculate a reliable 90%-used warning for free-tier usage."
}

af21_colab_create_session() {
  local output rc
  echo
  echo "[af21] Creating/reconnecting session '$AF21_SESSION' with GPU $AF21_GPU..."
  output="$(colab --auth="$AF21_AUTH" new -s "$AF21_SESSION" --gpu "$AF21_GPU" 2>&1)"; rc=$?
  printf '%s\n' "$output"
  if [[ $rc -eq 0 ]] && { [[ "$output" =~ [Rr][Ee][Aa][Dd][Yy] ]] || af21_colab_session_exists >/dev/null 2>&1; }; then
    echo "[af21] Session '$AF21_SESSION' is ready."
    af21_colab_usage
    return 0
  fi
  echo "[af21] Could not create the session. Check account access, quota, and GPU availability."
  return 1
}

af21_colab_switch_account() {
  local backup="" saved="" output rc
  mkdir -p "$(dirname "$AF21_COLAB_TOKEN")" || return 1
  echo "[af21] Backing up the current token before starting a fresh OAuth flow."
  if [[ -f "$AF21_COLAB_TOKEN" ]]; then
    backup="${AF21_COLAB_TOKEN}.backup.$(date +%Y%m%d-%H%M%S)"
    cp -p "$AF21_COLAB_TOKEN" "$backup" || { echo "[af21] Could not back up token."; return 1; }
    saved="${AF21_COLAB_TOKEN}.switching.$$"
    mv "$AF21_COLAB_TOKEN" "$saved" || return 1
    echo "[af21] Previous token backup: $backup"
  fi

  echo "[af21] Starting the supported OAuth flow via 'colab status'."
  echo "[af21] Open the displayed Google URL, choose the intended account, approve, then paste the authorization code."
  # CLI 0.7.4 has no `colab login` command. With the token temporarily absent,
  # any authenticated command starts colab_cli.auth._run_remote_flow().
  output="$(colab --auth="$AF21_AUTH" status -s "$AF21_SESSION" 2>&1)"; rc=$?
  printf '%s\n' "$output"
  if [[ -s "$AF21_COLAB_TOKEN" ]]; then
    [[ -z "$saved" ]] || rm -f "$saved"
    echo "[af21] OAuth token created."
    return 0
  fi

  if [[ -n "$saved" && -f "$saved" && ! -e "$AF21_COLAB_TOKEN" ]]; then
    mv "$saved" "$AF21_COLAB_TOKEN"
    echo "[af21] Restored previous token because new authentication was not completed."
  elif [[ -n "$saved" && -f "$saved" ]]; then
    echo "[af21] Previous token remains at: $saved"
  fi
  echo "[af21] OAuth was not confirmed (CLI exit: $rc)."
  return 1
}

af21_colab_menu() {
  if [[ ! -t 0 || ! -t 1 ]]; then
    echo "[af21] Non-interactive terminal; skipping session menu."
    return 0
  fi
  echo
  echo "========================================"
  echo "       aFold21 - Colab Connection"
  echo "========================================"
  echo "Session: $AF21_SESSION | GPU for new session: $AF21_GPU"
  echo
  echo "1. Check session and usage"
  echo "2. Sign in / switch Google account, then create session"
  echo "3. Create session with current account"
  echo "4. Check compute usage"
  echo "5. Return without connecting"
  local choice
  while true; do
    read -r -p "Choose [1-5]: " choice </dev/tty || return 0
    case "$choice" in
      1)
        if af21_colab_session_exists; then af21_colab_usage
        else echo "[af21] Session is missing or unavailable."; fi
        ;;
      2)
        if af21_colab_switch_account; then af21_colab_create_session || true
        else echo "[af21] Account switch was not confirmed; check authentication output."; fi
        ;;
      3) af21_colab_create_session || true ;;
      4) af21_colab_usage ;;
      5|"") return 0 ;;
      *) echo "Choose 1, 2, 3, 4, or 5." ;;
    esac
  done
}

# Public entry point used by the activation hook.
af21_colab_on_activate() {
  # Never read from stdin or prompt in batch/non-interactive shells.
  [[ $- == *i* && -t 0 && -t 1 ]] || return 0
  if ! command -v colab >/dev/null 2>&1; then
    echo "[af21] Colab CLI not found; skipping activation check."
    return 0
  fi
  local output rc
  output="$(af21_colab_status)"; rc=$?
  if [[ $rc -eq 0 && ! "$output" =~ [Ss]ession[[:space:]]+.*not[[:space:]]+found ]]; then
    echo
    echo "[af21] Existing session '$AF21_SESSION' found:"
    printf '%s\n' "$output"
    af21_colab_usage
  else
    echo
    echo "[af21] Session '$AF21_SESSION' is missing or unavailable."
    af21_colab_menu
  fi
}
