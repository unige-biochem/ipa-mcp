@echo off
rem Does the server find the synced library on this machine? Prints what it sees.
pushd "%~dp0.."
where uv >nul 2>nul || (echo uv is not installed: https://docs.astral.sh/uv/getting-started/installation/ & popd & pause & exit /b 1)
uv run ipa-mcp --status
popd
pause
