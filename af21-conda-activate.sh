#!/usr/bin/env bash
# Conda activation hook. The helper is installed beside this hook.
_AF21_HELPER="${HOME}/.local/share/alphafold21/af21_colab_session_manager.sh"
if [[ -r "$_AF21_HELPER" ]]; then
  # shellcheck source=/dev/null
  source "$_AF21_HELPER"
  af21_colab_on_activate
fi
unset _AF21_HELPER
