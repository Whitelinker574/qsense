#!/usr/bin/env bash
# QSense 一键安装脚本
# 用法:
#   人工交互:  bash setup.sh
#   Agent 静默: QSENSE_API_KEY=sk-xxx bash setup.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"

echo "[qsense] Installing QSense..."

# ── 1. 确保 uv 存在 ──
if ! command -v uv &>/dev/null; then
    if command -v brew &>/dev/null; then
        echo "[qsense] Installing uv via Homebrew..."
        brew install uv
    else
        echo "[qsense] ERROR: uv is required but not installed."
        echo "  Install uv first: https://docs.astral.sh/uv/getting-started/installation/"
        echo "  macOS:   brew install uv"
        echo "  Linux:   curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "  Windows: powershell -c 'irm https://astral.sh/uv/install.ps1 | iex'"
        exit 1
    fi
fi

# ── 2. 创建虚拟环境 ──
if [ ! -d "$VENV_DIR" ]; then
    echo "[qsense] Creating virtual environment..."
    uv venv --python 3.12 "$VENV_DIR"
fi

# ── 3. 激活并安装 ──
source "$VENV_DIR/bin/activate"
echo "[qsense] Installing dependencies..."
uv pip install -e "$REPO_DIR" --quiet

# ── 4. 配置 ──
CONFIG_DIR="$HOME/.qsense"
CONFIG_FILE="$CONFIG_DIR/.env"

if [ -f "$CONFIG_FILE" ]; then
    echo "[qsense] Config already exists: $CONFIG_FILE"
else
    if [ -n "${QSENSE_API_KEY:-}" ]; then
        mkdir -p "$CONFIG_DIR" && chmod 700 "$CONFIG_DIR"
        cat > "$CONFIG_FILE" <<EOF
QSENSE_API_KEY=${QSENSE_API_KEY}
QSENSE_BASE_URL=${QSENSE_BASE_URL:-https://api.openai.com/v1}
QSENSE_MODEL=${QSENSE_MODEL:-google/gemini-3-flash-preview}
EOF
        chmod 600 "$CONFIG_FILE"
        echo "[qsense] Config written from environment variables: $CONFIG_FILE"
    else
        echo "[qsense] No config found. Run 'qsense init' to set up,"
        echo "         or set QSENSE_API_KEY env var and re-run this script."
    fi
fi

# ── 5. 验证 ──
echo ""
echo "[qsense] Installation complete!"
echo ""
echo "  Activate:  source $VENV_DIR/bin/activate"
echo "  Verify:    qsense --help"
echo "  Models:    qsense models"
echo ""

if command -v qsense &>/dev/null; then
    qsense --help | head -3
fi
