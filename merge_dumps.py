#!/usr/bin/env python3
"""
Merge the chunked browser dumps (from extract_browser.js `__v2.dump(...)`) into one raw JSON.

    python merge_dumps.py <dump files...> [-o output/dribl_raw_2026_v2.json]

Each input is either the raw JSON string the dump() call returned, or the Claude tool-result
wrapper ([{type:"text", text:"<json string>"}] with trailing metadata). Parts are detected
from the `part` field: meta | mc | members | all.
"""
import argparse
import json
from pathlib import Path


def unwrap(path: Path) -> dict:
    dec = json.JSONDecoder()
    data = path.read_text()
    while not isinstance(data, dict) or "part" not in data and "fixtures" not in data:
        if isinstance(data, str):
            data, _ = dec.raw_decode(data.lstrip())
        elif isinstance(data, list):
            data = data[0]
        elif isinstance(data, dict) and "text" in data:
            data = data["text"]
        else:
            raise ValueError(f"cannot unwrap {path}")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("output/dribl_raw_2026_v2.json"))
    args = ap.parse_args()

    merged = {"leagues": [], "fixtures": [], "mc": {}, "members": {}, "ladders": {}, "errors": []}
    for f in args.files:
        d = unwrap(f)
        part = d.get("part", "all")
        for k in ("extracted_at", "tenant", "season"):
            if k in d:
                merged[k] = d[k]
        for k in ("leagues", "fixtures", "errors"):
            if d.get(k):
                merged[k] = d[k] if k != "errors" else merged[k] + d[k]
        for k in ("mc", "members", "ladders"):
            if d.get(k):
                merged[k].update(d[k])
        print(f"{f.name}: part={part} " + ", ".join(f"{k}={len(d[k])}" for k in ("leagues", "fixtures", "mc", "members", "ladders") if k in d))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(merged, fh)
    print(f"merged -> {args.out}: fixtures={len(merged['fixtures'])} mc={len(merged['mc'])} members={len(merged['members'])} "
          f"ladders={len(merged['ladders'])} errors={len(merged['errors'])} ({args.out.stat().st_size/1e6:.1f} MB)")
    missing_mc = [f["match_hash_id"] for f in merged["fixtures"] if f["match_hash_id"] not in merged["mc"]]
    missing_mem = [f["match_hash_id"] for f in merged["fixtures"] for s in ("home", "away") if f"{f['match_hash_id']}:{s}" not in merged["members"]]
    print(f"fixtures missing matchcentre: {len(missing_mc)}, missing lineups: {len(missing_mem)}")


if __name__ == "__main__":
    main()
