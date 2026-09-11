"""Inspect staged publication contents; report filenames only for suspicious matches."""

import re
import subprocess
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    paths = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
    patterns = {
        "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}"),
        "API key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{30,}"),
        "AWS access key": re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
        "personal absolute path": re.compile(r"[A-Z]:[/\\]Users[/\\]", re.I),
    }
    findings, size, count = [], 0, 0
    for name in filter(None, paths):
        path = root / name
        content = path.read_bytes()
        size += len(content)
        count += 1
        if len(content) > 2_000_000:
            findings.append((name, "file above 2 MB"))
        if any(
            part in {"node_modules", ".venv", ".tools", "artifacts", "test-results"}
            for part in path.relative_to(root).parts
        ):
            findings.append((name, "generated/private directory"))
        if path.name == ".env":
            findings.append((name, "environment secrets file"))
        if path.suffix == ".png":
            continue
        text = content.decode("utf-8", errors="replace")
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append((name, label))
    print(f"Reviewed {count} tracked files, {size:,} bytes.")
    for name, label in findings:
        print(f"FLAG: {name}: {label}")
    if findings:
        raise SystemExit(1)
    print("No matches in the targeted secret/path scan; no oversized or excluded generated files tracked.")


if __name__ == "__main__":
    main()
