# Installs the "ipa" MCP server in one application, for every project. Run it through the
# .bat next to it (claude-code.bat, claude-desktop.bat, vscode.bat, check.bat).
#
# It checks uv and git, then starts the server once: the first start downloads and builds
# it, which can take longer than an application waits for a server, and shows whether the
# synced library is found. Then it registers the server and says what to restart.
# Running it again updates the server and replaces its entry.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("claude-code", "claude-desktop", "vscode", "check")]
    [string]$App,
    [switch]$Checkout,   # register this checkout (uv run --directory) instead of the GitHub repository
    [switch]$Remove
)

$source = "git+https://github.com/unige-biochem/ipa-mcp"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

function Fail($msg) {
    Write-Host ""
    Write-Host $msg -ForegroundColor Red
    exit 1
}
function Need($exe, $how) {
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) {
        Fail "$exe is not installed. $how`nThen open a new window and run this again."
    }
}

if ($Checkout) {
    $command = "uv"
    $arguments = @("run", "--directory", $repo, "ipa-mcp")
} else {
    $command = "uvx"
    $arguments = @("--from", $source, "ipa-mcp")
}

# ------------------------------------------------------------------ remove ---

if ($Remove) {
    switch ($App) {
        "claude-code" {
            Need claude "Install Claude Code first."
            & claude mcp remove -s user ipa
        }
        "claude-desktop" {
            $config = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
            if (Test-Path $config) {
                $cfg = Get-Content $config -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($cfg.mcpServers) { $cfg.mcpServers.PSObject.Properties.Remove("ipa") }
                [IO.File]::WriteAllText($config, ($cfg | ConvertTo-Json -Depth 10), (New-Object Text.UTF8Encoding $false))
            }
            Write-Host "Removed. Quit Claude Desktop (also from the tray icon) and open it again."
        }
        "vscode" { Write-Host "In VS Code: MCP: List Servers, select ipa, and remove it there." }
        "check" { }
    }
    exit 0
}

# ------------------------------------------------- fetch, start once, check ---

Need uv "Install it: https://docs.astral.sh/uv/getting-started/installation/"
if (-not $Checkout) { Need git "Install it: https://git-scm.com/downloads/win" }
if ($App -eq "claude-code") { Need claude "Install Claude Code first." }
if ($App -eq "vscode") { Need code "Install VS Code with 'Add to PATH' ticked: https://code.visualstudio.com/" }

Write-Host "Fetching the server and starting it once (the first time takes a minute) ..."
$run = @($arguments) + "--status"
if (-not $Checkout) { $run = @("--refresh") + $run }   # rerunning the installer updates it
$out = & $command @run
if ($LASTEXITCODE -ne 0) { Fail "The server did not start. The messages above say why." }
$status = ($out -join "`n") | ConvertFrom-Json
Write-Host ""
Write-Host "ipa-mcp $($status.version) runs."
if ($status.library) {
    Write-Host "Library found: $($status.library) ($($status.pages) pages, $($status.equipment) items)." -ForegroundColor Green
} else {
    Write-Host $status.setup -ForegroundColor Yellow
    Write-Host "The server is installed anyway; the assistant will remind you." -ForegroundColor Yellow
}
Write-Host ""

# ---------------------------------------------------------------- register ---

switch ($App) {
    "check" { }

    "claude-code" {
        & claude mcp remove -s user ipa *> $null   # replaces an earlier entry; none is fine
        $add = @("mcp", "add", "-s", "user", "ipa", "--", $command) + $arguments
        & claude @add
        if ($LASTEXITCODE -ne 0) { Fail "claude mcp add failed (see above)." }
        Write-Host "Registered in Claude Code for every project." -ForegroundColor Green
        Write-Host "Start a new Claude Code session: tools load when a session starts. /mcp lists 'ipa'."
        Write-Host "Ask it: 'which microscopes does the site list?'"
    }

    "claude-desktop" {
        $config = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
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
        $entry = [pscustomobject]@{ command = $command; args = $arguments }
        $cfg.mcpServers | Add-Member -NotePropertyName ipa -NotePropertyValue $entry -Force
        [IO.File]::WriteAllText($config, ($cfg | ConvertTo-Json -Depth 10), (New-Object Text.UTF8Encoding $false))
        Write-Host "Registered in Claude Desktop ($config)." -ForegroundColor Green
        Write-Host "Quit Claude Desktop (also from the tray icon) and open it again."
        Write-Host "Ask it: 'which microscopes does the site list?'"
    }

    "vscode" {
        $entry = [ordered]@{ name = "ipa"; command = $command; args = $arguments } | ConvertTo-Json -Compress
        # Windows PowerShell drops the quotes of a JSON argument: pass it as-is through --%.
        $env:IPA_MCP_JSON = $entry -replace '"', '\"'
        & code --% --add-mcp "%IPA_MCP_JSON%"
        if ($LASTEXITCODE -ne 0) { Fail "code --add-mcp failed (see above)." }
        Write-Host "Registered in VS Code (user profile)." -ForegroundColor Green
        Write-Host "In VS Code: MCP: List Servers shows 'ipa'; use it from Chat in agent mode."
    }
}
