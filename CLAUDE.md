# AI assistance

**Confidentiality level: open**: code, scientific question and sample images may be shown to AI tools.

Nothing to restrict. The data folder is still outside this repository, at `I:\common\ipa-mcp`.

# Working on this repo

- [DEVELOPMENT.md](DEVELOPMENT.md) says how the server is built and released; [readme.md](readme.md) is for users.
- The server is **read-only** and **never reads `private/`** of the library. Keep both; they are tested.
- The data conventions belong to the site's publishing repo (`common/sharepoint-biochem-ipa`,
  `docs/measurements.md` and `docs/library.md`). Do not redefine them here; read them there.
- Tests run against a fake library in a temp folder (`tests/test_server.py`), never against
  the real synced library, and never write into it.
- Never publish to PyPI: the server is installed from git (`github.com/unige-biochem/ipa-mcp`,
  a public copy of the GitLab repo), and the `Private :: Do Not Upload` classifier stays.
  Do not build a bundle unless asked.
