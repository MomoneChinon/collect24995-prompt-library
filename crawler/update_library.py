#!/usr/bin/env python3
"""Append new @collect24995 prompts into data/prompts.json (ids 0–9999)."""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_prompts import fetch_yahoo, walk_tweets, pair_prompts, USER  # noqa: E402

JST = timezone(timedelta(hours=8))
MAX_ID = 9999

def main() -> int:
    data_path = ROOT / "data" / "prompts.json"
    keys_path = ROOT / "data" / "used_keys.json"
    doc = json.loads(data_path.read_text()) if data_path.exists() else {
        "meta": {"source": f"@{USER}", "id_range": "0-9999", "count": 0},
        "prompts": [],
    }
    keys_doc = json.loads(keys_path.read_text()) if keys_path.exists() else {"keys": []}
    used = set(keys_doc.get("keys") or [])
    for p in doc.get("prompts") or []:
        if p.get("main_status_id") and p.get("reply_status_id"):
            used.add(f"{p['main_status_id']}:{p['reply_status_id']}")

    tweets = walk_tweets(fetch_yahoo(f"ID:{USER} プロンプト"))
    pairs = pair_prompts(tweets)
    pairs.sort(key=lambda p: int(p["main"]["id"]), reverse=True)

    next_id = max((int(p["id"]) for p in doc.get("prompts") or []), default=-1) + 1
    added = []
    for pair in pairs:
        if next_id > MAX_ID:
            break
        main, reply = pair["main"], pair["reply"]
        key = f"{main['id']}:{reply['id']}"
        if key in used:
            continue
        body = reply["body"]
        if len(body) < 40 or ("追加" in body and "縦長" not in body and "横長" not in body):
            continue
        ts = None
        if main.get("createdAt"):
            ts = datetime.fromtimestamp(main["createdAt"], tz=JST).strftime("%Y-%m-%d %H:%M Asia/Shanghai")
        item = {
            "id": next_id,
            "main_status_id": main["id"],
            "reply_status_id": reply["id"],
            "main_url": main["url"],
            "reply_url": reply["url"],
            "posted_at": ts,
            "captured_at": datetime.now(JST).isoformat(),
            "selection": "crawler",
            "raw_prompt": body,
        }
        doc.setdefault("prompts", []).append(item)
        used.add(key)
        added.append(item)
        next_id += 1

    doc["meta"] = {
        "source": f"@{USER}",
        "id_range": "0-9999",
        "count": len(doc.get("prompts") or []),
        "updated_at": datetime.now(JST).isoformat(),
    }
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    keys_path.write_text(json.dumps({"keys": sorted(used)}, ensure_ascii=False, indent=2) + "\n")

    # also refresh public/ if present
    pub = ROOT / "public" / "data"
    if pub.exists():
        import shutil
        shutil.copy2(data_path, pub / "prompts.json")
        prompts = doc["prompts"]
        latest = max(prompts, key=lambda x: int(x["id"])) if prompts else {}
        (pub / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n")
        idx = {str(p["id"]): {"main_status_id": p.get("main_status_id"), "reply_status_id": p.get("reply_status_id")} for p in prompts}
        (pub / "index.json").write_text(json.dumps({"meta": doc["meta"], "index": idx}, ensure_ascii=False, indent=2) + "\n")
        by = pub / "by-id"
        by.mkdir(exist_ok=True)
        for p in prompts:
            (by / f"{p['id']}.json").write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n")
        (pub / "used_keys.json").write_text(json.dumps({"keys": sorted(used)}, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({"added": len(added), "total": doc["meta"]["count"], "ids": [a["id"] for a in added]}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
