#!/usr/bin/env python3
"""which-vid: paste a release list, get best picks for your Plex setup.

Default profile: Plex on older Synology NAS -> Apple TV 4K.
Prefers Direct Play candidates (HEVC/H.264 + DDP/Atmos, WEB-DL over WEBRip,
no surprise 10-bit/multi-audio that tends to force NAS transcoding).

Usage:
    pbpaste | python3 which_vid.py      # pipe clipboard
    python3 which_vid.py                # reads clipboard automatically on macOS
    python3 which_vid.py < listing.txt  # from file
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field

PROFILE_NAME = "Plex (older Synology NAS) -> Apple TV 4K"

RES_RE = re.compile(r"\b(2160p|1080p|720p|480p)\b", re.I)
SIZE_RE = re.compile(r"([\d.]+)\s*(GiB|MiB|GB|MB)\b", re.I)


@dataclass
class Release:
    title: str
    size_gb: float = 0.0
    resolution: str = ""
    score: int = 0
    pros: list = field(default_factory=list)
    cons: list = field(default_factory=list)


def parse_size(line: str) -> float:
    m = SIZE_RE.search(line)
    if not m:
        return 0.0
    val, unit = float(m.group(1)), m.group(2).lower()
    return val / 1024 if unit.startswith("m") else val


def looks_like_title(line: str) -> bool:
    line = line.strip()
    if not RES_RE.search(line):
        return False
    # release titles are dot-separated; 4+ dots filters out prose
    return line.count(".") >= 4


def parse(text: str) -> list[Release]:
    lines = [l for l in text.splitlines() if l.strip()]
    releases: list[Release] = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not looks_like_title(line):
            continue
        r = Release(title=line)
        r.resolution = RES_RE.search(line).group(1).lower()
        # size is usually on the next non-title line within a few lines
        for j in range(i + 1, min(i + 4, len(lines))):
            if not looks_like_title(lines[j]) and SIZE_RE.search(lines[j]):
                r.size_gb = parse_size(lines[j])
                break
        # dedupe identical titles (same release listed on multiple indexers)
        if not any(x.title == r.title and abs(x.size_gb - r.size_gb) < 0.1 for x in releases):
            releases.append(r)
    return releases


def score(r: Release) -> Release:
    t = re.sub(r"[\s._\-]+", "", r.title.lower())
    s = 0
    pros: list[str] = []
    cons: list[str] = []

    if r.resolution == "2160p":
        s += 30
        pros.append("4K")
    elif r.resolution == "1080p":
        s += 22
        pros.append("1080p")
    elif r.resolution == "720p":
        s += 8
        pros.append("720p")

    if any(c in t for c in ("h265", "hevc", "x265")):
        s += 10
        pros.append("HEVC")
    elif any(c in t for c in ("h264", "x264")):
        s += 9
        pros.append("H.264")

    if "webdl" in t:
        s += 15
        pros.append("WEB-DL")
    elif "webrip" in t:
        s += 4
        cons.append("WEBRip")
    elif "hdtv" in t:
        s -= 5
        cons.append("HDTV")

    if "atmos" in t:
        s += 8
        pros.append("Atmos")
    if "ddp" in t or "eac3" in t:
        s += 4
        pros.append("DDP/EAC3")
    if "aac" in t and r.resolution == "2160p":
        s -= 3
        cons.append("AAC on 4K (likely transcode)")

    if "10bit" in t and r.resolution != "2160p":
        s -= 5
        cons.append("10-bit (transcode risk)")

    if any(m in t for m in ("multi", "dual", "itaeng")):
        s -= 3
        cons.append("multi-audio (transcode risk)")

    if "sdr" in t:
        pros.append("SDR (no HDR remap)")

    if r.resolution == "2160p":
        if 0 < r.size_gb < 8:
            s -= 5
            cons.append("low 4K bitrate")
        elif r.size_gb > 20:
            s -= 3
            cons.append("very large")
    elif r.resolution == "1080p":
        if 0 < r.size_gb < 2.5:
            s -= 2
            cons.append("small 1080p")

    r.score = s
    r.pros = pros
    r.cons = cons
    return r


def read_input() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read()
    try:
        out = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, timeout=2, check=False
        )
        if out.stdout.strip():
            print("(read from clipboard)\n")
            return out.stdout
    except FileNotFoundError:
        pass
    print("Paste the release listing, then Ctrl+D:\n")
    return sys.stdin.read()


def main() -> None:
    print(f"Profile: {PROFILE_NAME}")
    text = read_input()
    releases = [score(r) for r in parse(text)]
    if not releases:
        print("No releases detected.")
        return
    releases.sort(key=lambda r: -r.score)

    print(f"Parsed {len(releases)} releases. Ranked best -> worst for Direct Play.\n")
    print("=" * 78)
    print("TOP PICKS")
    print("=" * 78)
    for r in releases[:5]:
        size = f"{r.size_gb:.1f} GiB" if r.size_gb else "size?"
        print(f"\n  [{r.score:>3}] {r.title}")
        print(f"        {r.resolution} - {size}")
        if r.pros:
            print(f"        + {', '.join(r.pros)}")
        if r.cons:
            print(f"        - {', '.join(r.cons)}")

    if len(releases) > 8:
        print("\n" + "-" * 78)
        print("AVOID")
        print("-" * 78)
        for r in releases[-3:]:
            print(f"  [{r.score:>3}] {r.title}")
            if r.cons:
                print(f"        - {', '.join(r.cons)}")


if __name__ == "__main__":
    main()
