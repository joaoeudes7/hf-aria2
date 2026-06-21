# Hf-Aria2

Fast HuggingFace downloader using `aria2c` — saves directly to the HF cache (`blobs/` + symlinks), ready for `transformers` and friends.

## Install

```bash
# 1. Install aria2
# Linux/macOS
sudo apt install aria2                   # Debian/Ubuntu
brew install aria2                       # macOS
dnf install aria2                        # Fedora

# Windows
winget install aria2
choco install aria2

# Or install via pip (Linux/Windows only, no macOS wheel)
pip install hf-aria2[aria2]

# 2. Install hf-aria2
pip install https://github.com/joaoeudes7/hf-aria2/releases/latest/download/##GET_VERSION##.whl

# or latest commit
pip install git+https://github.com/joaoeudes7/hf-aria2.git
```

## Usage

```bash
# Download a model
hf-aria2 <id_model>

# Filter by pattern
hf-aria2 <id_model> --include "*.safetensors" --exclude "*optimizer*"

# Download a dataset
hf-aria2 --repo-type dataset <id_dataset>

# Tweak parallelism (aggressive)
hf-aria2 <id_model> -x 16 -s 16 -j 8

# Dry-run (see what would be downloaded)
hf-aria2 <id_model> --dry-run
hf-aria2 <id_model> --dry-run --urls-only   # pipe-friendly

# Symlinks to a local folder
hf-aria2 <id_model> -o ./my-model

# Install shell alias (auto-detect: zsh/bash/fish)
hf-aria2 --install-alias

# Self-update
hf-aria2 --update
```

## How it works

1. Lists repo files via HuggingFace Hub API
2. Downloads in parallel with `aria2c`
3. Writes to `~/.cache/huggingface/hub/` (official format: blobs + symlinks)
4. Partial downloads resume automatically (`--continue=true`)

## Dev

```bash
git clone https://github.com/joaoeudes7/hf-aria2.git
cd hf-aria2
uv sync
uv run hf-aria2 --help
```

MIT
