# GitHub Chatter

GitHub Chatter is a Home Assistant custom integration that tracks issue and issue-comment activity for a GitHub repository and exposes sensors you can graph in Lovelace.

## Features

- Rolling window issue creation counts (`15m`, `1h`, `24h`, `7d`)
- Rolling window issue comment counts (`15m`, `1h`, `24h`, `7d`)
- Comment concentration (HHI) per window
- Top commented issue per window
- Composite pulse score (`0-100`)

## Install with HACS

1. Open HACS in Home Assistant.
2. Add this repository as a custom repository.
3. Category: `Integration`.
4. Install `GitHub Chatter`.
5. Restart Home Assistant.

## Configuration

Add integration from Settings -> Devices & Services -> Add Integration -> `GitHub Chatter`.

You need:

- Repository in `owner/name` format (example: `home-assistant/core`)
- GitHub personal access token with read access to repository metadata, issues, and issue comments

### PAT permissions

For a fine-grained personal access token, grant:

- Repository access: `Only select repositories` (or `All repositories` if you prefer)
- Repository permissions:
  - `Metadata`: `Read-only`
  - `Issues`: `Read-only`

For a classic token, use:

- `public_repo` for public repositories only
- `repo` if you need to access private repositories

## Graphing

Use History Graph or Statistics Graph cards with these numeric sensors:

- `issue_creation_count_*`
- `issue_comment_count_*`
- `comment_hhi_*`
- `pulse_score`

Top issue sensors include attributes (`number`, `title`, `url`, `comment_count`) for automations and drill-down.
