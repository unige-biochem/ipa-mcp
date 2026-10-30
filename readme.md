# ipa-mcp: the department's imaging site for AI assistants (draft)

Lets an AI assistant answer questions about the UNIGE Biochemistry imaging site,
[biochem-ipa](https://unigech.sharepoint.com/teams/ipa): the microscopes, hoods and
lab VMs, their protocols, and the measurements made on them.

> Is there a water objective on the Nikon scope? Has the laser power of the 3i
> spinning disk dropped since last year? Get me the PSF of the 60x. Is napari
> installed on the VMs? Open the booking page for the spinning disc.

When the answer is on the site, the assistant gives it with the page to check.
When it is not, it says so and gives the way forward: the protocol, and that the
facility can measure it with you.

It is an [MCP](https://modelcontextprotocol.io) server, so it is not tied to one
assistant: any application that can start a local MCP server, with any model it
offers. It reads **your own synced copy** of the site's library, read-only, with no
credentials: what the assistant sees is what your account can already read. What
you then send to a model is your decision, as with any file you open.

## Install

1. **Sync the library once.** Open the site's
   [library](https://unigech.sharepoint.com/teams/ipa/Documents%20partages) and click
   *Sync*. OneDrive creates a folder named *biochem-ipa - Documents*. Large raw files
   stay placeholders until something reads them.
2. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)** and
   [git](https://git-scm.com/downloads) (uv uses it to fetch the server).
3. **Install the server in your application.**

### Windows: double-click

Download the repository (on GitHub: *Code*, *Download ZIP*) and unzip it. In its
`install` folder, double-click the script for your application:

| Script | Installs in | Then |
| --- | --- | --- |
| `claude-code.bat` | Claude Code, for every project | start a new session |
| `claude-desktop.bat` | Claude Desktop | quit it (also from the tray icon) and open it again |
| `vscode.bat` | VS Code, your user profile | *MCP: List Servers* shows `ipa` |
| `check.bat` | nothing: says whether the server starts and finds the library | |

Each script checks that uv and git are there, fetches the server and starts it once
(so the application does not wait for the first download), says whether it found
the library, then registers it. Running it again updates the server; `-Remove` (for
example `claude-code.bat -Remove` in a terminal) takes it out again. The unzipped
folder is not needed afterwards.

### By hand (any system, any application)

The server runs straight from the repository with
`uvx --from git+https://github.com/unige-biochem/ipa-mcp ipa-mcp`. **Run this once
first**, with `--status` at the end: the first run downloads and builds it, which can
take longer than an application waits for a server to start, and it shows whether the
library was found. Then register it:

- VS Code: [![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_ipa--mcp-0098FF?logo=visualstudiocode)](https://vscode.dev/redirect/mcp/install?name=ipa&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22git%2Bhttps%3A%2F%2Fgithub.com%2Funige-biochem%2Fipa-mcp%22%2C%22ipa-mcp%22%5D%7D)
- Claude Code, for every project, then start a new session:
  `claude mcp add -s user ipa -- uvx --from git+https://github.com/unige-biochem/ipa-mcp ipa-mcp`
- Claude Desktop: *Settings, Developer, Edit config*, under `mcpServers`:
  `"ipa": {"command": "uvx", "args": ["--from", "git+https://github.com/unige-biochem/ipa-mcp", "ipa-mcp"]}`,
  then quit and reopen it.
- Anything else: command `uvx`, arguments
  `--from git+https://github.com/unige-biochem/ipa-mcp ipa-mcp`.

The server finds the synced folder by itself (OneDrive's registry on Windows, the
usual places on macOS). If it does not, set `IPA_LIBRARY` to the folder, or tell the
assistant where it is. The first time it matters, the assistant asks who you are and
which lab you are in, and remembers it in `~/.ipa-mcp/config.json`.

**It is not on PyPI, and will not be:** it only makes sense for the department's
site, so it is installed from git. `uvx ipa-mcp` alone does not work. To stay on
one version, add it to the URL (`git+https://github.com/unige-biochem/ipa-mcp@v0.1.0`).

### If the tools do not show up

- **Restart.** Applications load their servers when a session starts: a new Claude
  Code session, Claude Desktop quit and reopened, or *MCP: List Servers*, `ipa`,
  *Start* in VS Code.
- **See what it says.** In Claude Code, `/mcp` lists the servers and their state, and
  `claude mcp get ipa` shows where `ipa` is registered.
- **First start too slow.** Run `uvx --from git+https://github.com/unige-biochem/ipa-mcp ipa-mcp --status`
  once (or `check.bat`), then restart.
- **"MCP server ipa already exists".** It is already registered: nothing to do. To
  replace it, `claude mcp remove ipa` first, or run `claude-code.bat` again.
- **Works in one folder only (Claude Code).** `claude mcp add` without `-s user`
  registers it for the current folder only, and that entry wins there. In that
  folder, `claude mcp remove -s local ipa`, then add it with `-s user`.
- **Library not found.** `--status` gives the setup steps; or set `IPA_LIBRARY`.
- **Newer version.** `uvx` keeps what it built: run the `--status` command above with
  `--refresh` after `uvx` (or the `.bat` again), then restart.

### Testing from a checkout

Clone the repository and run the same scripts with `-Checkout` (for example
`install\claude-code.bat -Checkout`): they register the checkout, with
`uv run --directory <checkout> ipa-mcp`, instead of the GitHub repository. For the
Claude Desktop bundle, see [DEVELOPMENT.md](DEVELOPMENT.md).

## What it knows

| | From |
| --- | --- |
| Every page of the site: hardware, software, start-up, quirks, protocols, VMs | `site/*.md` |
| The equipment registry: objectives, light paths, laser lines, rooms | `site/registry.json` |
| Laser power at the sample over time | `data/laser-power/laser-power.csv` |
| PSFs per objective and light path, with the PSF images | `data/psf/psf.csv`, `data/psf/<session>/` |
| Courses, presentations, viewers | `builds/*/*/build.yaml` |

The copy is as fresh as OneDrive's last sync. The site is the reference, and the
assistant cites its pages. The library's `private/` folder is never read.

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md).

---

Created by: Nicolas Chiaruttini. GitHub (code, issues, releases):
https://github.com/unige-biochem/ipa-mcp. The facility's project record stays on GitLab:
https://gitlab.unige.ch/unige-biochem/common/ipa-mcp

Data folder (Windows): `I:\common\ipa-mcp`. macOS (Finder, Go, Connect to Server):
`smb://isis.unige.ch/nasac/s/biochem/biochem-ipa/ipa_biochemistry/common/ipa-mcp`.

Confidentiality level for this project: **open**: code, scientific question and sample
images may be shown to AI tools.
