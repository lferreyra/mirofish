"""
Pack / unpack a CheckpointData into a `.tar.zst` archive on disk.

Falls back to `.tar.gz` if `zstandard` isn't installed so the feature works
on a vanilla Python install.
"""

from __future__ import annotations

import io
import os
import tarfile
import time
from typing import Optional

from .serializer import CheckpointData


def _has_zstd() -> bool:
    try:
        import zstandard  # noqa: F401
        return True
    except ImportError:
        return False


def _archive_ext() -> str:
    return ".tar.zst" if _has_zstd() else ".tar.gz"


def default_archive_path(*, simulation_dir: str, round_num: int) -> str:
    ext = _archive_ext()
    checkpoints_dir = os.path.join(simulation_dir, "checkpoints")
    os.makedirs(checkpoints_dir, exist_ok=True)
    return os.path.join(checkpoints_dir, f"round-{round_num:05d}{ext}")


def save_checkpoint(
    checkpoint: CheckpointData,
    *,
    simulation_dir: str,
    out_path: Optional[str] = None,
) -> str:
    """Serialize `checkpoint` and write a compressed archive. Returns the
    final file path."""
    out_path = out_path or default_archive_path(
        simulation_dir=simulation_dir, round_num=checkpoint.round_num,
    )
    # Build the tar in-memory first so compression is a single pass.
    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tar:
        body = checkpoint.to_json().encode("utf-8")
        info = tarfile.TarInfo(name="checkpoint.json")
        info.size = len(body)
        info.mtime = int(time.time())
        tar.addfile(info, io.BytesIO(body))
    raw = tar_buf.getvalue()

    if out_path.endswith(".tar.zst"):
        import zstandard
        cctx = zstandard.ZstdCompressor(level=10)
        compressed = cctx.compress(raw)
        with open(out_path, "wb") as fh:
            fh.write(compressed)
    else:
        # gzip fallback
        import gzip
        with gzip.open(out_path, "wb") as fh:
            fh.write(raw)
    return out_path


def restore_checkpoint(archive_path: str) -> CheckpointData:
    """Inverse of `save_checkpoint` — decompresses and parses the inner JSON."""
    with open(archive_path, "rb") as fh:
        raw_compressed = fh.read()
    if archive_path.endswith(".tar.zst"):
        import zstandard
        dctx = zstandard.ZstdDecompressor()
        raw = dctx.decompress(raw_compressed)
    else:
        import gzip
        raw = gzip.decompress(raw_compressed)

    with tarfile.open(fileobj=io.BytesIO(raw), mode="r") as tar:
        member = tar.getmember("checkpoint.json")
        fh = tar.extractfile(member)
        if fh is None:
            raise ValueError(f"archive missing checkpoint.json: {archive_path}")
        return CheckpointData.from_json(fh.read().decode("utf-8"))
