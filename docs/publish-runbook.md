# GitHub Publish Runbook

This project is ready to publish once GitHub authentication is available.

## Create Repository

The local repository already has an initial commit. Both
`codex/nexus-resolve-build` and `main` point at the build commit.

```powershell
cd D:\Hackathon\nexus-resolve
git checkout main
gh repo create nexus-resolve --public --source . --remote origin --push
```

If `gh` is unavailable, create a public repository named `nexus-resolve` in the
GitHub UI, then run:

```powershell
git remote add origin https://github.com/<your-user>/nexus-resolve.git
git checkout main
git push -u origin main
```

## Configure Pages

1. Open the repository settings.
2. Go to Pages.
3. Set source to GitHub Actions.
4. Run the `Deploy GitHub Pages` workflow if it does not start automatically.
5. Copy the public Pages URL into `README.md`.

## Verify Public Replay

Open the Pages URL and confirm:

- The top bar shows `Replay Mode`.
- `INC-2026-00421` appears in Ticket Details.
- `SOP beats history` appears.
- Approval buttons are disabled in Replay Mode.
- RCA and metrics appear after the timeline completes.
