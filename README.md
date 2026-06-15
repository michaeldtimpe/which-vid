# which-vid

Paste a release listing (NZB/torrent search results from Sonarr, Radarr, Prowlarr, etc.) and get the best picks ranked for your specific Plex setup.

Default profile: **Plex on a Synology NAS → Apple TV 4K → Sonos**. The scorer favors releases that play end-to-end without anything having to transcode or downmix.

## Why

The Apple TV 4K direct-plays almost everything (HEVC, 10-bit, HDR/Dolby Vision, H.264), so the NAS isn't the bottleneck — it just streams the file. The real constraints are at the ends of the chain:

- **Audio → Sonos:** Sonos decodes Dolby (Dolby Digital / DD+ / DDP-Atmos), but **DTS, DTS-HD MA, TrueHD, and FLAC don't pass cleanly** through the Apple TV → Sonos hop — they downmix or drop surround. Prefer DDP/EAC3/AC3.
- **Legacy video codecs:** the Apple TV can't hardware-decode **VC-1 or MPEG-2** (common on old BluRay/broadcast rips), which forces a heavy transcode or fails outright.

This tool reads the release names, scores each candidate against those realities, and surfaces the few that will Just Work.

## Install

No dependencies — just stdlib Python 3.10+.

```bash
git clone git@github.com:michaeldtimpe/which-vid.git
cd which-vid
chmod +x which_vid.py
```

## Usage

```bash
# Auto-read from macOS clipboard
python3 which_vid.py

# Pipe from clipboard explicitly
pbpaste | python3 which_vid.py

# From a file
python3 which_vid.py < listing.txt
```

Paste the multi-line search output from your indexer UI. The script extracts release titles, infers resolution/codec/source/audio/size from the names, dedupes cross-indexer duplicates, scores each release, and prints a ranked **Top Picks** list plus an **Avoid** list.

## Example

Input (abridged):

```
nzb    44 days
Train.Dreams.2025.2160p.NF.WEB-DL.DDP5.1.Atmos.H.265-XEBEC-AsRequested
NZBgeek        11.9 GiB        English    WEBDL-2160p
nzb    178 days
Train.Dreams.2025.1080p.10bit.WEBRip.6CH.X265.HEVC-PSA
NzbPlanet        1.7 GiB        English    WEBRip-1080p
...
```

Output:

```
TOP PICKS
  [ 67] Train.Dreams.2025.2160p.NF.WEB-DL.DDP5.1.Atmos.H.265-XEBEC-AsRequested
        2160p - 11.9 GiB
        + 4K, HEVC, WEB-DL, Atmos (DDP), DDP/EAC3
  ...

AVOID
  [ 34] Train.Dreams.2025.1080p.10bit.WEBRip.6CH.X265.HEVC-PSA
        - WEBRip, small 1080p
```

## Scoring

| Signal | Effect |
| --- | --- |
| 2160p / 1080p / 720p | +30 / +22 / +8 |
| HEVC (H.265/x265) | +10 |
| H.264 / x264 | +9 |
| WEB-DL source | +15 |
| WEBRip source | +4 |
| HDTV source | −5 |
| Atmos audio (in DDP/EAC3) | +8 |
| DDP / EAC3 audio | +4 |
| AC3 / Dolby Digital audio | +3 |
| DTS / DTS-HD / TrueHD / FLAC | −8 (won't pass Apple TV → Sonos cleanly) |
| AAC audio | −2 (no Dolby surround for Sonos) |
| Legacy video (VC-1 / MPEG-2 / XviD / DivX) | −12 (Apple TV can't hardware-decode) |
| Multi-audio (MULTI/DUAL/iTA-ENG) | −3 (wrong default track risk) |
| SDR tag | label only (no HDR tone-mapping required) |
| 2160p under 8 GiB | −5 (low bitrate) |
| 2160p over 20 GiB | −3 (very large) |
| 1080p under 2.5 GiB | −2 (small) |

## Tuning the profile

Open `which_vid.py` and edit the `score()` function. Each heuristic is a few lines — adjust weights, add codecs, or comment out checks that don't apply to your client.

If you have a different setup (Nvidia Shield, beefy NAS that transcodes happily, an old Roku that hates HEVC), the weights to flip are:

- **Strong NAS, weak client**: penalize HEVC, reward H.264.
- **Weak NAS, strong client**: keep defaults — Direct Play matters most.
- **HDR-capable client**: remove the SDR pro, and consider rewarding `DV` / `HDR10` / `HDR10+` tokens.

## Limitations

- Heuristic-only: scoring is based on the release *name*, not file inspection. A mislabeled release will be misranked.
- macOS-first: clipboard auto-read uses `pbpaste`. On Linux/Windows, pipe input via stdin.
- Format-tolerant but not format-agnostic: parsing assumes dot-separated release names with embedded resolution tags (2160p/1080p/720p/480p). Works with Sonarr/Radarr/Prowlarr interactive search output and most indexer dumps.

## License

Personal-use script. Do whatever.
