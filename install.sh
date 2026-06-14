#!/usr/bin/env bash
# AIPG Validator Node — one-command installer.
#   curl -fsSL <repo>/validator-node/install.sh | bash
# or, from a checkout:  ./install.sh
set -euo pipefail

cd "$(dirname "$0")"
echo "▶ Setting up the AIPG validator node..."

command -v python3 >/dev/null || { echo "❌ python3 not found. Install Python 3.10+ and retry."; exit 1; }

python3 -m venv .venv
./.venv/bin/pip -q install --upgrade pip
./.venv/bin/pip -q install -r requirements.txt
echo "✅ Dependencies installed."

if [ ! -f .env ]; then
  ./.venv/bin/python -m validator.cli init
else
  echo "ℹ️  .env already exists — skipping setup. Edit it or run: ./.venv/bin/python -m validator.cli init"
fi

echo
echo "Next steps:"
echo "  ./.venv/bin/python -m validator.cli check    # verify it works"
echo "  ./.venv/bin/python -m validator.cli run      # start validating"
echo "  (or install the systemd service — see OPERATORS.md)"
