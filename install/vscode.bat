@echo off
rem Registers this checkout as the "ipa" MCP server in VS Code (user profile, Copilot agent mode).
rem Needs uv and the code CLI. Remove it again from VS Code: MCP: List Servers.
pushd "%~dp0.."
where uv >nul 2>nul || (echo uv is not installed: https://docs.astral.sh/uv/getting-started/installation/ & popd & pause & exit /b 1)
where code >nul 2>nul || (echo the code CLI is not on the PATH & popd & pause & exit /b 1)
echo Preparing the environment in %CD% ...
uv sync --quiet || (popd & pause & exit /b 1)
set "REPO=%CD:\=\\%"
call code --add-mcp "{\"name\":\"ipa\",\"command\":\"uv\",\"args\":[\"run\",\"--directory\",\"%REPO%\",\"ipa-mcp\"]}"
popd
echo Done. In VS Code, MCP: List Servers shows "ipa".
pause
