#!/usr/bin/env python3
"""Validate local Markdown links, image paths and heading fragments.

This deliberately uses only the Python standard library. It scans repository
Markdown outside fenced code blocks and reports missing local targets or anchors.
External URLs are not fetched; link availability on the public internet is out
of scope for this deterministic, offline CI check.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".venv", "venv", "build", "dist", "node_modules", "__pycache__"}
FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
LINK_RE = re.compile(
    r"(?P<image>!)?\[(?P<label>(?:\\.|[^\]])*)\]\(\s*"
    r"(?:<(?P<angle>[^>]+)>|(?P<url>[^\s)]+))"
)
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}"


def unfenced_lines(content: str) -> list[tuple[int, str]]:
    """Return numbered lines outside fenced code blocks."""
    result: list[tuple[int, str]] = []
    fence_char = ""
    fence_size = 0
    for number, line in enumerate(content.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if not fence_char:
                fence_char, fence_size = marker[0], len(marker)
                continue
            if marker[0] == fence_char and len(marker) >= fence_size:
                fence_char, fence_size = "", 0
                continue
        if not fence_char:
            result.append((number, line))
    return result


def plain_heading(raw: str) -> str:
    """Remove common inline Markdown syntax while retaining rendered text."""
    value = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", raw)
    value = re.sub(r"`([^`]*)`", r"\1", value)
    value = re.sub(r"[*_~]", "", value)
    value = re.sub(r"<[^>]+>", "", value)
    return value.strip()


def heading_slugs(lines: list[tuple[int, str]]) -> set[str]:
    """Compute GitHub-style heading slugs, including duplicate suffixes."""
    counts: dict[str, int] = {}
    result: set[str] = set()
    for _, line in lines:
        match = HEADING_RE.match(line)
        if not match:
            continue
        text = plain_heading(match.group(2)).lower()
        text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
        text = re.sub(r"\s+", "-", text.strip())
        count = counts.get(text, 0)
        counts[text] = count + 1
        result.add(text if count == 0 else f"{text}-{count}")
    return result


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*.md")
        if not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
    )


def resolve_target(raw_path: str, source: Path, root: Path) -> Path:
    """Resolve a local Markdown destination against the file or repository root."""
    decoded = unquote(raw_path)
    if decoded.startswith("/"):
        candidate = (root / decoded.lstrip("/")).resolve()
    elif decoded:
        candidate = (source.parent / decoded).resolve()
    else:
        candidate = source.resolve()

    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        raise ValueError("link resolves outside the repository") from None

    if candidate.is_dir():
        for name in ("README.md", "index.md"):
            page = candidate / name
            if page.is_file():
                return page
    return candidate


def validate(root: Path) -> list[Finding]:
    root = root.resolve()
    pages: dict[Path, tuple[list[tuple[int, str]], set[str]]] = {}
    findings: list[Finding] = []

    for source in markdown_files(root):
        try:
            lines = unfenced_lines(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeError) as exc:
            findings.append(Finding(source.relative_to(root), 1, f"cannot read Markdown: {exc}"))
            continue
        pages[source] = (lines, heading_slugs(lines))

    for source, (lines, _) in pages.items():
        for line_number, line in lines:
            for match in LINK_RE.finditer(line):
                raw_url = match.group("angle") or match.group("url") or ""
                if not raw_url or SCHEME_RE.match(raw_url) or raw_url.startswith("//"):
                    continue

                parts = urlsplit(raw_url)
                if parts.scheme or parts.netloc:
                    continue
                try:
                    target = resolve_target(parts.path, source, root)
                except ValueError as exc:
                    findings.append(Finding(source.relative_to(root), line_number, f"{raw_url}: {exc}"))
                    continue

                if not target.is_file():
                    findings.append(
                        Finding(
                            source.relative_to(root),
                            line_number,
                            f"missing local target '{raw_url}' (resolved to {target.relative_to(root) if target.is_relative_to(root) else target})",
                        )
                    )
                    continue

                fragment = unquote(parts.fragment)
                if fragment and not match.group("image") and target.suffix.lower() == ".md":
                    target_page = pages.get(target.resolve())
                    if target_page is None:
                        try:
                            target_lines = unfenced_lines(target.read_text(encoding="utf-8"))
                        except (OSError, UnicodeError):
                            continue
                        slugs = heading_slugs(target_lines)
                    else:
                        slugs = target_page[1]
                    if fragment not in slugs:
                        findings.append(
                            Finding(
                                source.relative_to(root),
                                line_number,
                                f"missing heading '#{fragment}' in {target.relative_to(root)}",
                            )
                        )

    return sorted(findings, key=lambda item: (str(item.path), item.line, item.message))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="repository root to scan")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    findings = validate(root)
    for finding in findings:
        print(finding)
    count = len(markdown_files(root))
    print(f"\nMarkdown validation: {len(findings)} error(s), {count} file(s) scanned.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
