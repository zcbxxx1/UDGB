#!/usr/bin/env python3
"""Fetch and repack the Unity Windows Mono support package for a given version.

The script mimics the behaviour of the original UDGB extractor but is written in
pure Python so it can be used independently of the C# project.  By default it
locates the macOS Windows-Mono support installer for the requested version,
extracts all managed DLLs, and places them into a flattened zip archive (matching
UDGB's output).

Example usage:
    python download_unity_windows_mono.py 6000.0.58f2 -o 6000.0.58.zip

Requirements:
    * Python 3.8+
    * A working "7z" command (from 7-Zip or p7zip).  You can override the path
      with the --seven-zip argument or SEVEN_ZIP environment variable.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable, Optional

UNITY_WHATS_NEW_URL = "https://unity.com/releases/editor/whats-new/"
UNITY_DOWNLOAD_HOST = "https://download.unity3d.com/download_unity/"
DEFAULT_VERSION = "6000.0.58f2"


def debug(message: str) -> None:
    print(f"[download_unity] {message}")


def sanitize_version(version: str) -> str:
    """Return a filesystem-friendly name without the build suffix."""
    return re.sub(r"[a-z]\d+$", "", version)


class DownloadError(RuntimeError):
    pass


def fetch_installer_url(version: str) -> str:
    """Scrape the Unity 'What's New' page to find the Windows Mono support pkg."""
    whats_new_url = f"{UNITY_WHATS_NEW_URL}{version}#installs"
    debug(f"Fetching install page: {whats_new_url}")

    try:
        request = urllib.request.Request(
            whats_new_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; UDGB/1.0)"},
        )
        with urllib.request.urlopen(request) as response:
            html = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        # Unity sometimes omits the suffix in the fallback URL.
        if exc.code == 404:
            fallback_url = f"{UNITY_WHATS_NEW_URL}{sanitize_version(version)}#installs"
            debug(f"Primary page missing, trying fallback: {fallback_url}")
            request = urllib.request.Request(
                fallback_url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; UDGB/1.0)"},
            )
            with urllib.request.urlopen(request) as response:
                html = response.read().decode("utf-8", errors="replace")
        else:
            raise DownloadError(f"Failed to fetch release page: {exc}") from exc

    pattern = re.compile(
        rf"{re.escape(UNITY_DOWNLOAD_HOST)}[0-9a-f]+/.+?UnitySetup-Windows-Mono-Support-for-Editor-{re.escape(version)}\\.pkg",
        re.IGNORECASE,
    )
    match = pattern.search(html)
    if not match:
        raise DownloadError("Unable to locate the Windows Mono support download link.")

    url = match.group(0)
    debug(f"Found installer: {url}")
    return url


def download_file(url: str, destination: Path) -> None:
    debug(f"Downloading to {destination}")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as response, destination.open("wb") as fh:
        shutil.copyfileobj(response, fh)


def run_7z(seven_zip: str, args: Iterable[str]) -> None:
    cmd = [seven_zip, *args]
    debug("Running: " + " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise DownloadError(
            "7z executable not found. Install 7-Zip/p7zip or provide --seven-zip."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise DownloadError(f"7z command failed with exit code {exc.returncode}") from exc


def extract_payload(pkg_path: Path, seven_zip: str, temp_root: Path) -> Path:
    pkg_extract = temp_root / "pkg"
    payload_extract = temp_root / "payload"
    pkg_extract.mkdir(parents=True, exist_ok=True)
    payload_extract.mkdir(parents=True, exist_ok=True)

    run_7z(seven_zip, ["x", str(pkg_path), f"-o{pkg_extract}", "-y"])

    payload_files = list(pkg_extract.glob("Payload~*"))
    if not payload_files:
        raise DownloadError("No Payload~ file found after extracting the pkg installer.")

    for payload in payload_files:
        run_7z(seven_zip, ["x", str(payload), f"-o{payload_extract}", "-y"])

    return payload_extract


def locate_managed(payload_dir: Path) -> Path:
    candidates = [path for path in payload_dir.rglob("Managed") if path.is_dir()]
    for managed in candidates:
        if managed.parent.name == "Data":
            return managed
    if candidates:
        return candidates[0]
    raise DownloadError("Managed directory not found inside payload.")


def make_zip(managed_dir: Path, output_path: Path) -> None:
    files = sorted(path for path in managed_dir.rglob("*") if path.is_file())
    if not files:
        raise DownloadError("Managed directory is empty; nothing to package.")

    seen_names = set()
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            name = file_path.name
            if name in seen_names:
                raise DownloadError(f"Duplicate file name encountered: {name}")
            seen_names.add(name)
            zf.write(file_path, arcname=name)


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", default=DEFAULT_VERSION)
    parser.add_argument("-o", "--output", type=Path, help="Destination zip file.")
    parser.add_argument(
        "--workdir",
        type=Path,
        help="Optional directory to use for temporary files (defaults to system temp).",
    )
    parser.add_argument(
        "--seven-zip",
        dest="seven_zip",
        default=os.environ.get("SEVEN_ZIP", "7z"),
        help="Path to the 7z executable (defaults to $SEVEN_ZIP or '7z').",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    version = args.version
    output = args.output
    if output is None:
        output = Path(f"{sanitize_version(version)}.zip")
    else:
        output = output.expanduser().resolve()

    if output.exists():
        debug(f"Removing existing output file {output}")
        output.unlink()

    workdir_cm = (
        tempfile.TemporaryDirectory(dir=str(args.workdir))
        if args.workdir
        else tempfile.TemporaryDirectory()
    )
    with workdir_cm as workdir_path:
        temp_root = Path(workdir_path)
        debug(f"Using temporary directory {temp_root}")

        installer_url = fetch_installer_url(version)
        pkg_path = temp_root / f"UnitySetup-Windows-Mono-Support-for-Editor-{version}.pkg"
        download_file(installer_url, pkg_path)

        payload_dir = extract_payload(pkg_path, args.seven_zip, temp_root)
        managed_dir = locate_managed(payload_dir)
        debug(f"Located managed directory: {managed_dir}")

        output.parent.mkdir(parents=True, exist_ok=True)
        make_zip(managed_dir, output)

    debug(f"Created archive: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DownloadError as exc:
        debug(str(exc))
        raise SystemExit(1)
