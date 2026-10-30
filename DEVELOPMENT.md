# Developing and releasing ipa-mcp

Users read [readme.md](readme.md). This file does not ship in the bundle (`.mcpbignore`).

## How it works

`src/ipa_mcp/__init__.py` is a thin stdio MCP server (the `mcp` SDK's FastMCP) with no
knowledge of SharePoint: it reads files in the synced library and returns structured
answers. The reasoning is the assistant's; the MCP instructions
(`src/ipa_mcp/data/instructions.md`) tell it how to use the tools and how to answer.

| Module | What |
| --- | --- |
| `library.py` | finds the synced library (`IPA_LIBRARY`, the saved config, OneDrive's registry keys on Windows, the usual folders), the user's config in `~/.ipa-mcp/config.json` (`IPA_MCP_HOME`), the site's URLs, the `private/` guard, OneDrive placeholder detection |
| `pages.py` | `site/<name>.md`: sections, outline, markers (`<!-- list: ... -->`), search |
| `records.py` | the registry, objective tags, name resolution with synonyms, laser-power series and trend, PSF sessions, builds, file listings |
| `__init__.py` | the tools, the instructions, `main()` |

The conventions it relies on are the site's, documented in the publishing repository
`sharepoint-biochem-ipa` (`docs/measurements.md`, `docs/library.md`): slugs
`<lab>_<kind>_<name>`, objective tags `<mag>x-<NA*100>-<immersion>`, one PSF session
folder per (scope, objective, path, date), `laser-power.csv` with one row per file.
A change there is a change here.

Handy:

```
uv run ipa-mcp --status               # where the library is, counts
uv run ipa-mcp --print-instructions   # what the assistant is told
uv run pytest                         # tests against a fake library in a temp folder
```

To try it in an assistant from the checkout: command `uv`, arguments
`run --directory <this folder> ipa-mcp`, or `install\<app>.bat -Checkout`.

The Windows installers are `install/install.ps1`, run by one `.bat` per application.
They are what department users double-click, so keep them safe to rerun: check uv and
git, start the server once with `--refresh --status` (the first start downloads and
builds it, which can outlast an application's start-up wait), replace the `ipa` entry
at user scope, and say what to restart.

## Principles

- **Read-only, and never `private/`.** The server does not write to the library and
  refuses to list or read the restricted folder, whatever the request.
- **No credentials.** The synced copy is the only source; the user's OneDrive account
  decides what is there. No Graph, no token.
- **Structured where the data is structured, prose where it is prose.** A number comes
  from a CSV or the registry; a procedure comes from the page, cited.
- **"Not measured" is an answer**, with the protocol page and whom to ask.
- **Raw data on demand only.** A tool lists files with their download state; nothing
  reads a raw acquisition unless asked for by path.

## Where it lives, and why not PyPI

The server is only useful for the department's site, so it is **not published to
PyPI**: users install it from git, `uvx --from git+https://github.com/unige-biochem/ipa-mcp ipa-mcp`.
The `Private :: Do Not Upload` classifier in `pyproject.toml` makes PyPI refuse an
upload made by mistake; keep it.

The repository's home is GitHub; the GitLab project is kept as the facility's record:

| Remote | URL | For |
| --- | --- | --- |
| `origin` | `github.com/unige-biochem/ipa-mcp` (public) | the code, issues, releases; what users install from, no account needed |
| `gitlab` | `gitlab.unige.ch/unige-biochem/common/ipa-mcp` | the facility's project status issue; a copy of `main` |

`git push origin main && git push gitlab main`, and the same with `--tags`.

## Releasing

1. Set the version in `pyproject.toml` and `manifest.json`.
2. `uv run pytest`, `uv build` (checks the package builds; the wheel is not uploaded).
3. Tag `v<version>` and push it to both remotes. Users who pin a version use
   `git+https://github.com/unige-biochem/ipa-mcp@v<version>`; the others get `main`.
4. Bundle for Claude Desktop: `npx @anthropic-ai/mcpb validate manifest.json`, then
   `npx @anthropic-ai/mcpb pack . ipa-mcp-<version>.mcpb`, attached to the GitHub release
   of the tag.
