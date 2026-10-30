@echo off
rem Installs the "ipa" MCP server in Claude Desktop. Double-click it.
rem Needs uv and git; it says so if one is missing. Running it again updates the server.
rem   claude-desktop.bat -Remove   removes it again
rem   claude-desktop.bat -Checkout   this checkout instead of the GitHub repository (development)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -App claude-desktop %*
pause
