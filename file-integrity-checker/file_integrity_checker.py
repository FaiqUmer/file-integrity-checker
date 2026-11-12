"""
File Integrity Checker
Author: Faiq Umer (ZYNVEX-CERT-2217)

A simple File Integrity Monitoring (FIM) tool. It stores a SHA-256 hash of
every file in a folder (the "baseline") and later reports which files were
modified, added or deleted.

Usage:
    python file_integrity_checker.py init  <folder> [--baseline FILE]
    python file_integrity_checker.py check <folder> [--baseline FILE]

Exit codes: 0 = OK / baseline created, 1 = changes detected, 2 = error.
"""

import argparse
import hashlib
import json
import os
import sys

DEFAULT_BASELINE = "baseline.json"


def hash_file(path):
    """Return the SHA-256 hex digest of a file, read in chunks."""
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def scan_folder(folder, skip=None):
    """Return {relative_path: hash} for every file under folder.

    `skip` is an absolute path (the baseline file) that is never hashed,
    so the baseline can safely live inside the monitored folder.
    """
    hashes = {}
    for root, _, files in os.walk(folder):
        for name in sorted(files):
            full_path = os.path.join(root, name)
            if skip and os.path.abspath(full_path) == skip:
                continue
            rel_path = os.path.relpath(full_path, folder)
            hashes[rel_path] = hash_file(full_path)
    return hashes


def create_baseline(folder, baseline_file=DEFAULT_BASELINE):
    hashes = scan_folder(folder, os.path.abspath(baseline_file))
    with open(baseline_file, "w") as f:
        json.dump(hashes, f, indent=4, sort_keys=True)
    print(f"[+] Baseline saved for {len(hashes)} file(s) -> {baseline_file}")
    return hashes


def compare(old, new):
    """Compare two {path: hash} dicts -> (modified, added, deleted)."""
    modified = sorted(p for p in new if p in old and new[p] != old[p])
    added = sorted(p for p in new if p not in old)
    deleted = sorted(p for p in old if p not in new)
    return modified, added, deleted


def check_integrity(folder, baseline_file=DEFAULT_BASELINE):
    """Print a report. Returns True if no changes, False if changed,
    None if the baseline is missing."""
    if not os.path.exists(baseline_file):
        print("[!] No baseline found. Run 'init' first.")
        return None

    with open(baseline_file) as f:
        old = json.load(f)
    new = scan_folder(folder, os.path.abspath(baseline_file))
    modified, added, deleted = compare(old, new)

    print("\n===== Integrity Report =====")
    print(f"Modified : {len(modified)}")
    for p in modified:
        print(f"  [~] {p}")
    print(f"New      : {len(added)}")
    for p in added:
        print(f"  [+] {p}")
    print(f"Deleted  : {len(deleted)}")
    for p in deleted:
        print(f"  [-] {p}")

    if not (modified or added or deleted):
        print("\n[OK] All files are intact. No changes detected.")
        return True
    print("\n[WARNING] Changes detected!")
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description="SHA-256 file integrity checker")
    parser.add_argument("command", choices=["init", "check"])
    parser.add_argument("folder")
    parser.add_argument("--baseline", default=DEFAULT_BASELINE,
                        help=f"baseline file (default: {DEFAULT_BASELINE})")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.folder):
        print(f"[!] Folder not found: {args.folder}")
        return 2
    if args.command == "init":
        create_baseline(args.folder, args.baseline)
        return 0
    result = check_integrity(args.folder, args.baseline)
    if result is None:
        return 2
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
