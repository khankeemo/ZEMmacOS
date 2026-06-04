@echo off
title ZEMmacOS License Admin
cd /d "%~dp0"
echo Ensure the ZEM API backend is running before launching the admin UI.
python admin_tools\license_admin_ui.py
pause
