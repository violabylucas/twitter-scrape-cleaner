#!/usr/bin/env python3
"""
Clean a Zeeschuimer / X / Twitter NDJSON export into analysis-ready outputs.

Keeps:
- tweet text and language
- timestamps: posted, collected, last updated
- account name, screen name, user ID
- location where available
- tweet engagement counts
- user/account scale metrics
- quoted tweet text
- quoted tweet author bio

Drops by omission:
- your interaction state (favorited, bookmarked, retweeted, followedby, following, etc.)
- image/video/media payloads
- most bloat metadata

Outputs:
- cleaned JSONL
- cleaned CSV
- summary JSON

Usage:
    python clean_x_zeeschuimer.py input.ndjson
    python clean_x_zeeschuimer.py input.ndjson --outdir cleaned_output
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


TWEET_FIELDS = [
    "tweet_id",
    "conversation_id",
    "tweet_text",
    "tweet_lang",
    "tweet_created_at",
    "collected_at",
    "last_updated_at",
    "user_id",
    "user_name",
    "screen_name",
    "user_location",
    "user_description",
    "user_description_lang",
    "quoted_tweet_text",
    "quoted_tweet_author_bio",
    "like_count",
    "reply_count",
    "retweet_count",
    "quote_count",
    "view_count",
    "bookmark_count",
    "followers_count",
    "following_count",
    "statuses_count",
    "listed_count",
    "favourites_count",
    "media_count",
    "is_quote_status",
    "in_reply_to_screen_name",
    "in_reply_to_user_id",
    "source_platform",
    "source_url",
    "search_url",
]


def flatten_dict(obj: Any, prefix: str = "", out: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if out is None:
        out = {}

    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            flatten_dict(v, key, out)
    elif isinstance(obj, list):
        if all(not isinstance(x, (dict, list)) for x in obj):
            out[prefix] = obj
        else:
            for i, v in enumerate(obj):
                key = f"{prefix}.{i}" if prefix else str(i)
                flatten_dict(v, key, out)
    else:
        out[prefix] = obj

    return out


def normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def build_index(flat: Dict[str, Any]) -> Dict[str, List[Tuple[str, Any]]]:
    idx: Dict[str, List[Tuple[str, Any]]] = {}
    for k, v in flat.items():
        nk = normalize_key(k)
        idx.setdefault(nk, []).append((k, v))
    return idx


def pick_first(idx: Dict[str, List[Tuple[str, Any]]], *candidates: str) -> Any:
    for cand in candidates:
        nk = normalize_key(cand)
        if nk in idx:
            for _, value in idx[nk]:
                if value not in (None, "", [], {}):
                    return value
    return None


def pick_longest(idx: Dict[str, List[Tuple[str, Any]]], *candidates: str) -> Any:
    found = []
    for cand in candidates:
        nk = normalize_key(cand)
        if nk in idx:
            found.extend(v for _, v in idx[nk] if v not in (None, "", [], {}))
    if not found:
        return None
    return sorted(found, key=lambda x: len(str(x)), reverse=True)[0]


def to_int(value: Any) -> Optional[int]:
    if value in (None, "", "null"):
        return None
    try:
        if isinstance(value, bool):
            return int(value)
        return int(float(value))
    except (ValueError, TypeError):
        return None


def to_str(value: Any) -> Optional[str]:
    if value in (None, "", "null"):
        return None
    s = str(value).strip()
    return s if s else None


def extract_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    collected_at = raw.get("timestamp_collected")
    last_updated_at = raw.get("last_updated")
    source_platform = raw.get("source_platform")
    search_url = raw.get("source_platform_url")
    source_url = raw.get("source_url")

    payload = raw.get("data", {})
    if not isinstance(payload, dict):
        return {}

    flat = flatten_dict(payload)
    idx = build_index(flat)

    row = {
        "tweet_id": to_str(pick_first(
            idx,
            "legacy.id_str",
            "rest_id",
            "id"
        )),
        "conversation_id": to_str(pick_first(
            idx,
            "legacy.conversation_id_str"
        )),
        "tweet_text": to_str(pick_longest(
            idx,
            "legacy.full_text",
            "note_tweet.note_tweet_results.result.text",
            "note_tweet.results.result.text",
            "legacy.text"
        )),
        "tweet_lang": to_str(pick_first(
            idx,
            "legacy.lang"
        )),
        "tweet_created_at": to_str(pick_first(
            idx,
            "legacy.created_at"
        )),
        "collected_at": to_int(collected_at),
        "last_updated_at": to_int(last_updated_at),

        "user_id": to_str(pick_first(
            idx,
            "core.user_results.result.rest_id",
            "legacy.user_id_str"
        )),
        "user_name": to_str(pick_first(
            idx,
            "core.user_results.result.legacy.name",
            "core.user_results.result.core.name"
        )),
        "screen_name": to_str(pick_first(
            idx,
            "core.user_results.result.core.screen_name",
            "core.user_results.result.legacy.screen_name"
        )),
        "user_location": to_str(pick_first(
            idx,
            "core.user_results.result.location.location",
            "core.user_results.result.legacy.location"
        )),
        "user_description": to_str(pick_first(
            idx,
            "core.user_results.result.legacy.description",
            "core.user_results.result.profile_bio.description"
        )),
        "user_description_lang": to_str(pick_first(
            idx,
            "core.user_results.result.profile_bio.description_language",
            "core.user_results.result.profile_description_language"
        )),

        "quoted_tweet_text": to_str(pick_longest(
            idx,
            "quoted_status_result.result.legacy.full_text",
            "quoted_status_result.result.note_tweet.note_tweet_results.result.text",
            "quoted_status_result.result.note_tweet.results.result.text",
            "quoted_status_result.result.legacy.text"
        )),
        "quoted_tweet_author_bio": to_str(pick_first(
            idx,
            "quoted_status_result.result.core.user_results.result.legacy.description",
            "quoted_status_result.result.core.user_results.result.profile_bio.description"
        )),

        "like_count": to_int(pick_first(idx, "legacy.favorite_count")),
        "reply_count": to_int(pick_first(idx, "legacy.reply_count")),
        "retweet_count": to_int(pick_first(idx, "legacy.retweet_count")),
        "quote_count": to_int(pick_first(idx, "legacy.quote_count")),
        "view_count": to_int(pick_first(idx, "views.count")),
        "bookmark_count": to_int(pick_first(idx, "legacy.bookmark_count")),

        "followers_count": to_int(pick_first(idx, "core.user_results.result.legacy.followers_count")),
        "following_count": to_int(pick_first(idx, "core.user_results.result.legacy.friends_count")),
        "statuses_count": to_int(pick_first(idx, "core.user_results.result.legacy.statuses_count")),
        "listed_count": to_int(pick_first(idx, "core.user_results.result.legacy.listed_count")),
        "favourites_count": to_int(pick_first(idx, "core.user_results.result.legacy.favourites_count")),
        "media_count": to_int(pick_first(idx, "core.user_results.result.legacy.media_count")),

        "is_quote_status": pick_first(idx, "legacy.is_quote_status"),
        "in_reply_to_screen_name": to_str(pick_first(idx, "legacy.in_reply_to_screen_name")),
        "in_reply_to_user_id": to_str(pick_first(idx, "legacy.in_reply_to_user_id_str")),

        "source_platform": to_str(source_platform),
        "source_url": to_str(source_url),
        "search_url": to_str(search_url),
    }

    row = {k: v for k, v in row.items() if v not in (None, "", [], {})}
    return row


def clean_file(input_path: Path, outdir: Path) -> Tuple[Path, Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)

    jsonl_path = outdir / f"{input_path.stem}.cleaned.jsonl"
    csv_path = outdir / f"{input_path.stem}.cleaned.csv"
    summary_path = outdir / f"{input_path.stem}.summary.json"

    rows: List[Dict[str, Any]] = []
    total_input_lines = 0
    bad_json_lines = 0
    empty_lines = 0
    unsupported_lines = 0
    dict_lines = 0

    with input_path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                empty_lines += 1
                continue

            total_input_lines += 1

            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                bad_json_lines += 1
                continue

            if not isinstance(raw, dict):
                unsupported_lines += 1
                continue

            dict_lines += 1
            cleaned = extract_record(raw)

            if cleaned.get("tweet_id") or cleaned.get("tweet_text"):
                rows.append(cleaned)

    fieldnames = sorted(set().union(*(row.keys() for row in rows))) if rows else TWEET_FIELDS

    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "input_file": str(input_path),
        "output_jsonl": str(jsonl_path),
        "output_csv": str(csv_path),
        "total_input_lines": total_input_lines,
        "bad_json_lines": bad_json_lines,
        "empty_lines": empty_lines,
        "unsupported_lines": unsupported_lines,
        "dict_lines": dict_lines,
        "cleaned_rows_written": len(rows),
        "fields_kept": fieldnames,
        "notes": [
            "Top-level wrapper fields are preserved only where useful for provenance and timestamps.",
            "Tweet and user content are extracted from raw['data'].",
            "Quoted tweet text and quoted author bio are included when present.",
            "Media fields are excluded by omission.",
            "User interaction / relationship fields are excluded by omission."
        ]
    }

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return jsonl_path, csv_path, summary_path


def main():
    parser = argparse.ArgumentParser(description="Clean Zeeschuimer/X NDJSON export")
    parser.add_argument("input", help="Path to input .ndjson file")
    parser.add_argument("--outdir", default="cleaned_output", help="Directory for outputs")
    args = parser.parse_args()

    input_path = Path(args.input)
    outdir = Path(args.outdir)

    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    clean_file(input_path, outdir)


if __name__ == "__main__":
    main()