@echo off
rem Registers this checkout as the "ipa" MCP server in Claude Code, for every project (user scope).
rem Needs uv and the claude CLI. To remove it again:  claude mcp remove ipa
pushd "%~dp0.."
where uv >nul 2>nul || (echo uv is not installed: https://docs.astral.sh/uv/getting-started/installation/ & popd & pause & exit /b 1)
where claude >nul 2>nul || (echo the claude CLI is not installed & popd & pause & exit /b 1)
echo Preparing the environment in %CD% ...
uv sync --quiet || (popd & pause & exit /b 1)
claude mcp add --scope user ipa -- uv run --directory "%CD%" ipa-mcp
popd
echo Done. In Claude Code, /mcp shows the server; ask it: "which microscopes does the site list?"
pause
