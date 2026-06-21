from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from huggingface_hub import HfApi, hf_hub_url


@dataclass
class DownloadBatch:
    repo_id: str
    revision: str
    sha: str
    files: list[tuple[str, str]] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)
    repo_dir: Path = field(default_factory=Path)
    snapshot_dir: Path = field(default_factory=Path)
    blobs_dir: Path = field(default_factory=Path)
    no_exist_dir: Path = field(default_factory=Path)
    local_dir: Path | None = None
    token: str | None = None
    repo_type: str = "model"


def _get_cache_root() -> Path:
    hf_home = os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")
    return Path(hf_home) / "hub"


def _repo_dirname(repo_id: str, repo_type: str) -> str:
    prefix = {"model": "models", "dataset": "datasets", "space": "spaces"}.get(
        repo_type, "models"
    )
    return f"{prefix}--{repo_id.replace('/', '--')}"


def _should_include(
    path: str, include: list[str] | None, exclude: list[str] | None
) -> bool:
    if include and not any(fnmatch(path, p) for p in include):
        return False
    if exclude and any(fnmatch(path, p) for p in exclude):
        return False
    return True


def _confirm_download(batch: DownloadBatch, to_download: int, total_size_hint: str):
    print(f"\nRepository: {batch.repo_id}@{batch.revision}")
    print(f"  Type:     {batch.repo_type}")
    print(f"  Files:    {len(batch.files)} total, {to_download} to download")
    if batch.local_dir:
        print(f"  Symlinks: {batch.local_dir}")
    print(f"  Cache:    {batch.snapshot_dir}")
    if total_size_hint:
        print(f"  Size:     ~{total_size_hint}")
    answer = input("\nProceed with download? [Y/n] ").strip().lower()
    if answer not in ("", "y", "yes"):
        print("Aborted.")
        sys.exit(0)


def resolve_batch(args) -> DownloadBatch:
    api = HfApi(token=args.token)

    try:
        info = api.repo_info(
            args.repo, revision=args.revision, repo_type=args.repo_type
        )
    except Exception as e:
        print(f"error: failed to fetch repo info for {args.repo}: {e}", file=sys.stderr)
        sys.exit(1)

    siblings = [s.rfilename for s in info.siblings]

    included = [f for f in siblings if _should_include(f, args.include, args.exclude)]
    excluded = [f for f in siblings if not _should_include(f, args.include, args.exclude)]

    files = [
        (
            hf_hub_url(
                args.repo,
                f,
                revision=args.revision,
                repo_type=args.repo_type,
            ),
            f,
        )
        for f in included
    ]

    cache_root = _get_cache_root()
    repo_dir_name = _repo_dirname(args.repo, args.repo_type)
    repo_dir = cache_root / repo_dir_name
    snapshot_dir = repo_dir / "snapshots" / info.sha

    batch = DownloadBatch(
        repo_id=args.repo,
        revision=args.revision,
        sha=info.sha,
        files=files,
        excluded=excluded,
        repo_dir=repo_dir,
        snapshot_dir=snapshot_dir,
        blobs_dir=repo_dir / "blobs",
        no_exist_dir=repo_dir / ".no_exist" / info.sha,
        local_dir=Path(args.local_dir) if args.local_dir else None,
        token=args.token or os.environ.get("HF_TOKEN"),
        repo_type=args.repo_type,
    )

    if args.dry_run:
        if args.urls_only:
            for url, _ in files:
                print(url)
        else:
            print(f"Repository: {batch.repo_id}@{batch.revision}")
            print(f"Type:       {batch.repo_type}")
            print(f"Revision:   {batch.sha}")
            print(f"Files:      {len(files)} to download")
            print(f"Cache:      {batch.snapshot_dir}")
            if batch.local_dir:
                print(f"Symlinks:   {batch.local_dir}")
            if excluded:
                print(f"Excluded:   {len(excluded)} files")
            print()
            for url, fname in files:
                print(f"  {fname}")
        sys.exit(0)

    if not args.yes:
        _confirm_download(batch, len(files), "")

    return batch
