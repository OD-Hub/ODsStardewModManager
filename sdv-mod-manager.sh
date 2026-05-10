#!/usr/bin/env bash
# SDV Mod Manager launcher
# Place sdv_mod_manager.py in the same directory as this script.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="python3"

# Check for PyQt6
if ! "$PYTHON" -c "import PyQt6" 2>/dev/null; then
    echo "PyQt6 not found. Installing..."
    pip3 install PyQt6 --break-system-packages
fi

exec "$PYTHON" "$SCRIPT_DIR/sdv_mod_manager.py" "$@"
