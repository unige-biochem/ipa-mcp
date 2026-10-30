@echo off
rem Installs the "ipa" MCP server in VS Code (user profile). Double-click it.
rem Needs uv and git; it says so if one is missing. Running it again updates the server.
rem   remove it in VS Code: MCP: List Servers
rem   vscode.bat -Checkout   this checkout instead of the GitHub repository (development)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -App vscode %*
pause
