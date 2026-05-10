@echo off
:: OD's Stardew Mod Manager — Windows launcher
:: Place this file in the same folder as sdv_mod_manager.py

cd /d "%~dp0"

python sdv_mod_manager.py
if %errorlevel% neq 0 (
    echo.
    echo Something went wrong. Make sure Python and PyQt6 are installed.
    echo Run: pip install PyQt6
    pause
)
