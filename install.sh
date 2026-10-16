#!/usr/bin/env bash
set -euo pipefail

# Use the same environment name as the documented `conda activate af21` workflow.
ENV_NAME="${AF21_ENV_NAME:-af21}"
PYTHON_VERSION="${AF21_PYTHON_VERSION:-3.12}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$HOME/.local/share/alphafold21"
BIN_DIR="$HOME/.local/bin"

if ! command -v conda >/dev/null 2>&1; then
  echo "ERROR: Conda was not found in PATH." >&2
  echo "Initialize/activate your existing Miniforge, Miniconda, or Anaconda shell, then rerun ./install.sh." >&2
  exit 1
fi

if ! conda env list | awk 'NF && $1 !~ /^#/ {print $1}' | grep -Fxq "$ENV_NAME"; then
  echo "Creating Conda environment '$ENV_NAME' (Python $PYTHON_VERSION)..."
  conda create -y -n "$ENV_NAME" "python=$PYTHON_VERSION" pip
else
  echo "Conda environment '$ENV_NAME' already exists; reusing it."
fi

ENV_PREFIX="$(conda run -n "$ENV_NAME" python -c 'import sys; print(sys.prefix)')"
echo "Installing/updating Google Colab CLI in '$ENV_NAME'..."
conda run -n "$ENV_NAME" python -m pip install --upgrade google-colab-cli

mkdir -p "$APP_DIR" "$BIN_DIR"
install -m 0644 "$SCRIPT_DIR/af21.py" "$APP_DIR/af21.py"
install -m 0644 "$SCRIPT_DIR/af21_batch.py" "$APP_DIR/af21_batch.py"
install -m 0644 "$SCRIPT_DIR/af21_colab_session_manager.sh" "$APP_DIR/af21_colab_session_manager.sh"

# Install a Conda activation hook. It only reports/checks on interactive TTYs.
ACTIVATE_DIR="$ENV_PREFIX/etc/conda/activate.d"
mkdir -p "$ACTIVATE_DIR"
install -m 0644 "$SCRIPT_DIR/af21-conda-activate.sh" "$ACTIVATE_DIR/af21-colab-menu.sh"

cat > "$BIN_DIR/af21" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail
export PATH="$ENV_PREFIX/bin:$BIN_DIR:\$PATH"
exec "$ENV_PREFIX/bin/python" "$APP_DIR/af21.py" "\$@"
LAUNCHER

cat > "$BIN_DIR/af21-all" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail
export PATH="$ENV_PREFIX/bin:$BIN_DIR:\$PATH"
exec "$ENV_PREFIX/bin/python" "$APP_DIR/af21_batch.py" "\$@"
LAUNCHER

cat > "$BIN_DIR/af21-stop" <<LAUNCHER
#!/usr/bin/env bash
exec "$BIN_DIR/af21" stop "\$@"
LAUNCHER
cat > "$BIN_DIR/af21-status" <<LAUNCHER
#!/usr/bin/env bash
exec "$BIN_DIR/af21" status "\$@"
LAUNCHER
chmod +x "$BIN_DIR/af21" "$BIN_DIR/af21-all" "$BIN_DIR/af21-stop" "$BIN_DIR/af21-status"

if [[ ":${PATH}:" != *":$BIN_DIR:"* ]]; then
  echo "NOTE: Add this line to ~/.bashrc if ~/.local/bin is not already in PATH:"
  echo '  export PATH="$HOME/.local/bin:$PATH"'
fi

echo
echo "Installation complete."
echo "  Single prediction: af21"
echo "  Batch predictions: af21-all sequences.csv --output-root ./batch_results"
echo "  Runtime status:    af21 status  (or af21-status)"
echo "  Shutdown runtime:  af21 stop    (or af21-stop)"
echo "  Colab manager:     enabled on interactive 'conda activate $ENV_NAME'"
echo "  Details:           $APP_DIR/af21_colab_session_manager.sh"
echo
echo "First use: run 'af21' and follow the Google Colab CLI sign-in instructions."
echo "Quota note: free-tier quota percentage/90% threshold is not available from the CLI."
