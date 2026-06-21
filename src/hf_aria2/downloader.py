from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from hf_aria2.resolver import DownloadBatch


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_aria2c_path() -> str | None:
    return shutil.which("aria2c")


def _is_cached(snapshot_dir: Path, filename: str) -> bool:
    path = snapshot_dir / filename
    if path.is_symlink():
        target = path.resolve()
        if target.exists():
            return True
        path.unlink()
    return False


def _commit_file(temp_path: Path, filename: str, batch: DownloadBatch, expected_sha: str | None = None):
    if expected_sha:
        shasum = expected_sha
    else:
        shasum = _sha256(temp_path)
    blob_path = batch.blobs_dir / shasum

    if not blob_path.exists():
        shutil.move(str(temp_path), str(blob_path))
    else:
        temp_path.unlink()

    symlink_path = batch.snapshot_dir / filename
    symlink_path.parent.mkdir(parents=True, exist_ok=True)
    rel = os.path.relpath(blob_path, symlink_path.parent)
    symlink_path.symlink_to(rel)


def _write_refs(batch: DownloadBatch):
    refs_dir = batch.repo_dir / "refs"
    refs_dir.mkdir(parents=True, exist_ok=True)
    (refs_dir / batch.revision).write_text(batch.sha)


def _write_no_exist(batch: DownloadBatch):
    if batch.no_exist_dir.exists():
        shutil.rmtree(batch.no_exist_dir)
    for f in batch.excluded:
        if (batch.snapshot_dir / f).exists():
            continue
        p = batch.no_exist_dir / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()


def _create_local_symlinks(batch: DownloadBatch):
    if not batch.local_dir:
        return
    batch.local_dir.mkdir(parents=True, exist_ok=True)
    for entry in batch.snapshot_dir.iterdir():
        if entry.is_symlink() or entry.is_file():
            target = entry.resolve()
            link = batch.local_dir / entry.name
            if not link.exists():
                rel = os.path.relpath(target, batch.local_dir)
                link.symlink_to(rel)


def _format_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def _install_hint():
    if sys.platform == "darwin":
        return "brew install aria2"
    elif sys.platform == "win32":
        return "choco install aria2  (or winget install aria2)"
    else:
        return "sudo apt install aria2  (or sudo dnf install aria2)"



def run_download(batch: DownloadBatch, args):
    aria2c_path = _get_aria2c_path()
    if not aria2c_path:
        print("error: aria2c not found. Install it:", file=sys.stderr)
        print(f"  {_install_hint()}", file=sys.stderr)
        sys.exit(1)

    batch.snapshot_dir.mkdir(parents=True, exist_ok=True)
    batch.blobs_dir.mkdir(parents=True, exist_ok=True)
    batch.no_exist_dir.mkdir(parents=True, exist_ok=True)

    to_download = [
        (url, fname) for url, fname in batch.files if not _is_cached(batch.snapshot_dir, fname)
    ]
    already_cached = len(batch.files) - len(to_download)

    if not to_download:
        print(f"✓ All {len(batch.files)} files already cached at {batch.snapshot_dir}")
        _write_refs(batch)
        _create_local_symlinks(batch)
        return

    if already_cached:
        print(f"✓ {already_cached} files already cached, {len(to_download)} to download")

    staging = batch.repo_dir / ".staging"
    staging.mkdir(parents=True, exist_ok=True)

    input_file = staging / "aria2_input.txt"
    with open(input_file, "w") as f:
        for url, fname in to_download:
            f.write(f"{url}\n  out={fname}\n")
            sha = batch.lfs_hashes.get(fname)
            if sha:
                f.write(f"  checksum=sha-256={sha}\n")
        f.write(f"  header=User-Agent: hf-aria2\n")
        if batch.token:
            f.write(f"  header=Authorization: Bearer {batch.token}\n")

    cmd = [
        aria2c_path,
        "-i", str(input_file),
        "-d", str(staging),
        "-x", str(args.x),
        "-s", str(args.s),
        "-j", str(args.j),
        "--continue=true",
        "--auto-file-renaming=false",
        "--file-allocation=none",
        "--download-result=hide",
        "--max-tries=10",
        "--retry-wait=10",
    ]

    spinners = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    bar_len = 20
    t0 = time.time()
    proc = subprocess.Popen(cmd, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    frame = 0

    while True:
        try:
            proc.wait(timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            downloaded = sum(
                f.stat().st_size for f in staging.iterdir()
                if f.is_file() and f.name != "aria2_input.txt"
            )
            now = time.time()
            pct = min(int(downloaded * 100 / batch.total_size), 99) if batch.total_size else 0
            filled = pct * bar_len // 100
            bar = "█" * filled + "░" * (bar_len - filled)
            speed = downloaded / (now - t0) if (now - t0) > 0 else 0
            elapsed_fmt = f"{int(now - t0)}s"
            spin = spinners[frame % len(spinners)]
            frame += 1
            print(f"\r  {spin} {bar} {pct}%  {_format_bytes(speed)}/s  {elapsed_fmt}", end="", flush=True)

    print()
    elapsed = time.time() - t0

    if proc.returncode != 0:
        print(f"\nerror: aria2c failed (exit {proc.returncode})", file=sys.stderr)
        print(f"  Staging files kept at: {staging}", file=sys.stderr)
        print("  Re-run to resume downloads", file=sys.stderr)
        sys.exit(1)

    print("\r  ═══ Committing files ═══")
    for i, (_, fname) in enumerate(to_download, 1):
        staged = staging / fname
        if staged.exists():
            sz = staged.stat().st_size
            label = "✔" if fname in batch.lfs_hashes else "⌛"
            print(f"\r  {label} [{i}/{len(to_download)}] {fname} ({_format_bytes(sz)})", end="", flush=True)
            _commit_file(staged, fname, batch, batch.lfs_hashes.get(fname))
    print()

    _write_refs(batch)

    if batch.excluded:
        _write_no_exist(batch)

    _create_local_symlinks(batch)

    if staging.exists():
        shutil.rmtree(staging)

    total = sum(
        f.stat().st_size
        for f in batch.blobs_dir.iterdir()
        if f.is_file() and len(f.name) == 64
    )
    speed = total / elapsed if elapsed > 0 else 0
    print(f"\n  ✓ Downloaded {len(to_download)} files")
    print(f"    Cache:  {batch.snapshot_dir}")
    print(f"    Size:   {_format_bytes(total)}")
    print(f"    Time:   {elapsed:.1f}s  ({_format_bytes(speed)}/s)")
