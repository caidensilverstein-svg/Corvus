#!/usr/bin/env bash
# Corvus one-liner bootstrap
# Usage: curl -fsSL https://raw.githubusercontent.com/caidensilverstein-svg/Corvus/main/install.sh | bash
set -euo pipefail

REPO="https://github.com/caidensilverstein-svg/Corvus"
INSTALL_DIR="$HOME/.local/corvus"

echo "==> Corvus installer"

# Require git
if ! command -v git &>/dev/null; then
    echo "Error: git is required but not found." >&2
    exit 1
fi

# Require Python 3.8+
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 is required but not found." >&2
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(sys.version_info >= (3, 8))')
if [ "$PY_VERSION" != "True" ]; then
    echo "Error: Python 3.8 or newer is required." >&2
    exit 1
fi

# Clone or pull
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "==> Updating existing installation at $INSTALL_DIR"
    git -C "$INSTALL_DIR" pull --ff-only
else
    echo "==> Cloning Corvus to $INSTALL_DIR"
    git clone --depth 1 "$REPO" "$INSTALL_DIR"
fi

# Install dependencies
echo "==> Installing Python dependencies"
python3 -m pip install --quiet --user -r "$INSTALL_DIR/requirements.txt"

# Create launcher in PATH
LAUNCHER="$HOME/.local/bin/corvus"
mkdir -p "$(dirname "$LAUNCHER")"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"

echo ""
echo "Corvus installed successfully."
echo "Run: corvus --help"
echo ""

# Suggest PATH addition if needed
if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
    echo "Note: Add \$HOME/.local/bin to your PATH:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
fi
