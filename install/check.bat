@echo off
rem Does the server start, and does it find the synced library? Registers nothing.
rem Needs uv and git; it says so if one is missing. Running it again updates the server.
rem   check.bat -Checkout   this checkout instead of the GitHub repository (development)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -App check %*
pause
