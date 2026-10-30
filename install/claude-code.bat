@echo off
rem Installs the "ipa" MCP server in Claude Code, for every project. Double-click it.
rem Needs uv and git; it says so if one is missing. Running it again updates the server.
rem   claude-code.bat -Remove   removes it again
rem   claude-code.bat -Checkout   this checkout instead of the GitHub repository (development)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -App claude-code %*
pause
