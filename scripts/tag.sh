#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: ./scripts/tag.sh <version>"
  exit 1
fi

raw_version="$1"
normalized_version="$(printf '%s' "$raw_version" | tr -d '[:space:]' | sed -E 's/^[vV]+//')"

if [[ -z "$normalized_version" ]]; then
  echo "Error: version is empty after normalization."
  exit 1
fi

tag_name="v$normalized_version"
manifest_path="custom_components/github_chatter/manifest.json"

git checkout main
git pull --ff-only origin main

current_version="$(sed -n 's/.*"version": "\([^"]*\)".*/\1/p' "$manifest_path")"

if [[ -z "$current_version" ]]; then
  echo "Error: could not read version from $manifest_path"
  exit 1
fi

if [[ "$current_version" != "$normalized_version" ]]; then
  sed -E -i '' 's/("version": ")[^"]*(")/\1'"$normalized_version"'\2/' "$manifest_path"
  git add "$manifest_path"
  git commit -m "$tag_name"
fi

git pull --ff-only origin main
if git rev-parse "$tag_name" >/dev/null 2>&1; then
  echo "Error: tag '$tag_name' already exists locally."
  exit 1
fi
git tag "$tag_name"
git push origin main "$tag_name"

origin_url="$(git config --get remote.origin.url)"
repo_slug="$(printf '%s' "$origin_url" | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')"

gh api --method POST "repos/$repo_slug/releases" -f tag_name="$tag_name" -f name="$tag_name"
