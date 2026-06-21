#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <version>"
  echo "  e.g. $0 0.2.4"
  exit 1
fi

VERSION="$1"
TAG="v$VERSION"

cd "$(dirname "$0")"

sed -i '' "s/^version = .*/version = \"$VERSION\"/" pyproject.toml
sed -i '' "s|hf-aria2/[0-9.]*|hf-aria2/$VERSION|" src/hf_aria2/downloader.py
sed -i '' "s|hf_aria2-[0-9.]*-py3-none-any.whl|hf_aria2-$VERSION-py3-none-any.whl|" README.md

uv build

git add -A
git commit -m "$TAG"
git tag -f "$TAG"
git tag -f latest

git push origin "$TAG"
git push origin latest --force

gh release delete "$TAG" --yes 2>/dev/null || true
gh release create "$TAG" --title "$TAG" --generate-notes dist/*.tar.gz dist/*.whl

echo "✅ Released $TAG + latest"
