# hf-aria

Fast HuggingFace downloader using aria2c — cache-compatible with `huggingface_hub`.

Downloads models, datasets, and spaces from HuggingFace Hub using `aria2c` for maximum parallelism, writing directly to the HF cache layout (`blobs/` + symlinks) so `transformers` and other HF libraries can use them immediately.

## Install

### 1. Install aria2

```bash
# macOS
brew install aria2

# Linux
sudo apt install aria2      # Debian/Ubuntu
sudo dnf install aria2      # Fedora

# Windows
winget install aria2        # or choco install aria2
```

### 2. Install hf-aria

```bash
# From GitHub Releases (recommended)
pip install https://github.com/joaoeudes7/hf-aria/releases/latest/download/hf_aria-0.1.0-py3-none-any.whl

# Or latest commit
pip install git+https://github.com/joaoeudes7/hf-aria.git
```

> All releases: https://github.com/joaoeudes7/hf-aria/releases

## Usage

```bash
# Download model to HF cache (compatible with transformers)
hf-aria Qwen/Qwen2.5-1.5B-Instruct

# Download only safetensors files
hf-aria Qwen/Qwen2.5-1.5B-Instruct --include "*.safetensors"

# Exclude optimizer checkpoint files
hf-aria Qwen/Qwen2.5-1.5B-Instruct --exclude "*optimizer*"

# Download dataset
hf-aria --repo-type dataset HuggingFaceH4/ultrachat_200k

# Custom parallelism
hf-aria Qwen/Qwen2.5-1.5B-Instruct -x 8 -s 8 -j 4

# Symlinks to a local directory
hf-aria Qwen/Qwen2.5-1.5B-Instruct -o ./my-model

# Dry-run (show what would be downloaded)
hf-aria Qwen/Qwen2.5-1.5B-Instruct --dry-run

# URLs only (pipe-friendly)
hf-aria Qwen/Qwen2.5-1.5B-Instruct --dry-run --urls-only

# Gated model with token
hf-aria meta-llama/Llama-3.1-70B --token "$HF_TOKEN"

# Install shell alias (auto-detects from $SHELL)
hf-aria --install-alias
hf-aria --install-alias bash
hf-aria --install-alias zsh
hf-aria --install-alias fish

# Self-update
hf-aria --update
```

## How it works

1. Queries the HuggingFace Hub API to list repository files
2. Downloads files using `aria2c` with multi-connection parallelism
3. Commits to `~/.cache/huggingface/hub/` — full HF cache layout (`blobs/` + symlinks in `snapshots/<sha>/`)
4. Supports resuming partial downloads via aria2c `--continue=true`

## Development

```bash
git clone https://github.com/joaoeudes7/hf-aria.git
cd hf-aria
uv sync
uv run hf-aria --help
```

## License

MIT
