@echo off
rem Registers this checkout as the "ipa" MCP server in Claude Desktop.
rem Needs uv (https://docs.astral.sh/uv/). Restart Claude Desktop afterwards.
rem To remove it again:  claude-desktop.bat --remove
set "ARGS="
if /i "%~1"=="--remove" set "ARGS=-Remove"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0claude-desktop.ps1" %ARGS%
pause
