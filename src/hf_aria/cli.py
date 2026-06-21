import argparse
import os
import sys
from pathlib import Path


def parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(
        prog="hf-aria",
        description="Fast HuggingFace downloader using aria2c — cache-compatible with huggingface_hub",
    )

    p.add_argument("repo", nargs="?", help="Repository ID (e.g. org/model or org/dataset)")

    p.add_argument("--include", nargs="*", default=None,
                   help="Glob patterns to include (e.g. *.safetensors *.json)")
    p.add_argument("--exclude", nargs="*", default=None,
                   help="Glob patterns to exclude (e.g. *optimizer* *training*)")

    p.add_argument("--revision", default="main",
                   help="Revision, tag, or branch (default: main)")
    p.add_argument("--token", default=None,
                   help="HF token for gated models (default: $HF_TOKEN)")
    p.add_argument("--repo-type", default="model", choices=["model", "dataset", "space"],
                   help="Repository type (default: model)")

    p.add_argument("-o", "--local-dir", default=None,
                   help="Output directory with symlinks to blobs")

    g = p.add_argument_group("aria2c performance tuning")
    g.add_argument("-x", type=int, default=16, metavar="N",
                   help="Max connections per server (default: 16)")
    g.add_argument("-s", type=int, default=16, metavar="N",
                   help="Split count per file (default: 16)")
    g.add_argument("-j", type=int, default=8, metavar="N",
                   help="Parallel downloads (default: 8)")

    g = p.add_argument_group("execution control")
    g.add_argument("--dry-run", action="store_true",
                   help="Show what would be downloaded without downloading")
    g.add_argument("--urls-only", action="store_true",
                   help="With --dry-run, print only URLs (pipe-friendly)")
    g.add_argument("-y", "--yes", action="store_true",
                   help="Skip confirmation prompt")

    g = p.add_argument_group("utilities")
    g.add_argument("--install-alias", nargs="?", const="_auto_", default=None,
                   metavar="{zsh,bash,fish}",
                   help="Install 'hfa' alias in rc file (auto-detect shell if omitted)")
    g.add_argument("--update", action="store_true",
                   help="Update hf-aria to latest version from GitHub")

    args = p.parse_args(argv)

    if not args.repo and not args.install_alias and not args.update:
        p.print_usage()
        print("error: repo is required (or use --install-alias / --update)", file=sys.stderr)
        sys.exit(1)

    if not args.token:
        args.token = os.environ.get("HF_TOKEN")

    if args.urls_only and not args.dry_run:
        print("error: --urls-only requires --dry-run", file=sys.stderr)
        sys.exit(1)

    return args


def handle_early_exit(args) -> bool:
    if args.install_alias:
        _install_alias(args.install_alias)
        return True
    if args.update:
        _self_update()
        return True
    return False


def _install_alias(shell: str):
    if shell == "_auto_":
        path = os.environ.get("SHELL", "")
        if path.endswith("zsh"):
            shell = "zsh"
        elif path.endswith("bash"):
            shell = "bash"
        elif path.endswith("fish"):
            shell = "fish"

    rc_files = {
        "zsh": (".zshrc", 'alias hfa="hf-aria"'),
        "bash": (".bashrc", 'alias hfa="hf-aria"'),
        "fish": (".config/fish/config.fish", 'alias hfa "hf-aria"'),
    }
    entry = rc_files.get(shell)
    if not entry:
        print(f"error: unsupported shell '{shell}'. Use --install-alias zsh, bash, or fish", file=sys.stderr)
        sys.exit(1)

    rc_name, alias_line = entry
    rc = Path.home() / rc_name
    if not rc.exists():
        print(f"error: {rc} not found", file=sys.stderr)
        sys.exit(1)

    lines = ["\n# hf-aria", alias_line]

    existing = rc.read_text() if rc.stat().st_size > 0 else ""
    if alias_line in existing:
        print(f"✓ alias 'hfa' already installed in {rc}")
        return

    with open(rc, "a") as f:
        f.write("\n".join(lines) + "\n")

    print(f"✓ alias 'hfa' installed in {rc}")
    print(f"  Run: source {rc}")


def _self_update():
    import subprocess

    GIT_URL = "git+https://github.com/joaoeudes7/hf-aria.git"

    cmds = [
        ([sys.executable, "-m", "pip", "install", "--upgrade", GIT_URL], "pip (GitHub)"),
    ]

    for cmd, label in cmds:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError:
            continue
        ret = result.returncode
        out = (result.stdout + result.stderr).lower()
        if ret == 0:
            print(f"✓ hf-aria updated via {label}")
            return
        if "already satisfied" in out:
            print("✓ hf-aria already up-to-date")
            return

    print("error: could not update. Try manually:", file=sys.stderr)
    print(f"  pip install --upgrade {GIT_URL}", file=sys.stderr)
    sys.exit(1)

