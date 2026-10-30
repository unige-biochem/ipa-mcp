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
2. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/).**
3. **Register the server** as a local (stdio) MCP server in your application. It runs
   straight from the repository, with
   `uvx --from git+https://github.com/unige-biochem/ipa-mcp ipa-mcp`:
   - VS Code: [![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_ipa--mcp-0098FF?logo=visualstudiocode)](https://vscode.dev/redirect/mcp/install?name=ipa&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22--from%22%2C%22git%2Bhttps%3A%2F%2Fgithub.com%2Funige-biochem%2Fipa-mcp%22%2C%22ipa-mcp%22%5D%7D)
   - Claude Code: `claude mcp add ipa -- uvx --from git+https://github.com/unige-biochem/ipa-mcp ipa-mcp`
   - Claude Desktop: the `.mcpb` bundle attached to a
     [release](https://github.com/unige-biochem/ipa-mcp/releases), or *Settings, Developer,
     Edit config* with the same command.
   - Anything else: command `uvx`, arguments
     `--from git+https://github.com/unige-biochem/ipa-mcp ipa-mcp`.

The server finds the synced folder by itself (OneDrive's registry on Windows, the
usual places on macOS). If it does not, set `IPA_LIBRARY` to the folder, or tell the
assistant where it is. The first time it matters, the assistant asks who you are and
which lab you are in, and remembers it in `~/.ipa-mcp/config.json`.

**It is not on PyPI, and will not be:** it only makes sense for the department's
site, so it is installed from git. `uvx ipa-mcp` alone does not work. To stay on
one version, add it to the URL (`git+https://github.com/unige-biochem/ipa-mcp@v0.1.0`).
`uvx` keeps what it built: to pick up a newer version, run the same command once with
`--refresh` after `uvx`.

### Testing from a checkout (Windows)

Clone the repository, then double-click one script in `install/`. Each one registers
the checkout as the server named `ipa`, pointing at `uv run --directory <checkout> ipa-mcp`:

| Script | Registers in | Undo |
| --- | --- | --- |
| `install\claude-desktop.bat` | Claude Desktop (`%APPDATA%\Claude\claude_desktop_config.json`); restart it | `claude-desktop.bat --remove` |
| `install\claude-code.bat` | Claude Code, user scope | `claude mcp remove ipa` |
| `install\vscode.bat` | VS Code, user profile | *MCP: List Servers* in VS Code |
| `install\check.bat` | nothing: prints whether the library was found | |

Or, for Claude Desktop without a checkout: pack the bundle (see
[DEVELOPMENT.md](DEVELOPMENT.md)) and open the `.mcpb` file with Claude Desktop,
which asks for the library folder; `uv` must be installed.

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

Created by: Nicolas Chiaruttini. GitLab (development, issues):
https://gitlab.unige.ch/unige-biochem/common/ipa-mcp. GitHub (public copy, to install
from): https://github.com/unige-biochem/ipa-mcp

Data folder (Windows): `I:\common\ipa-mcp`. macOS (Finder, Go, Connect to Server):
`smb://isis.unige.ch/nasac/s/biochem/biochem-ipa/ipa_biochemistry/common/ipa-mcp`.

Confidentiality level for this project: **open**: code, scientific question and sample
images may be shown to AI tools.
