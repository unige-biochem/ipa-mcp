# Registers this checkout as the "ipa" MCP server in Claude Desktop's config:
#   %APPDATA%\Claude\claude_desktop_config.json  ->  mcpServers.ipa
# Run through install\claude-desktop.bat. Restart Claude Desktop afterwards.
param([switch]$Remove)

$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$config = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
}

if (Test-Path $config) {
    $json = Get-Content $config -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($json)) { $json = "{}" }
    $cfg = $json | ConvertFrom-Json
} else {
    New-Item -ItemType Directory -Force (Split-Path $config) | Out-Null
    $cfg = [pscustomobject]@{}
}
if (-not ($cfg.PSObject.Properties.Name -contains "mcpServers")) {
    $cfg | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{})
}

if ($Remove) {
    $cfg.mcpServers.PSObject.Properties.Remove("ipa")
    Write-Host "Removed the 'ipa' server from $config"
} else {
    Write-Host "Preparing the environment in $repo ..."
    & uv sync --directory $repo --quiet
    if ($LASTEXITCODE -ne 0) { Write-Host "uv sync failed"; exit 1 }
    $entry = [pscustomobject]@{
        command = "uv"
        args    = @("run", "--directory", $repo, "ipa-mcp")
    }
    $cfg.mcpServers | Add-Member -NotePropertyName ipa -NotePropertyValue $entry -Force
    Write-Host "Registered the 'ipa' server in $config"
    Write-Host "  command: uv run --directory `"$repo`" ipa-mcp"
}

$out = $cfg | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($config, $out, (New-Object System.Text.UTF8Encoding $false))
Write-Host "Restart Claude Desktop, then ask it: 'which microscopes does the site list?'"
