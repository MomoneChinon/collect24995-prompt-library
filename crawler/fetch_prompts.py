#!/usr/bin/env python3
"""Standalone crawler: fetch AI image prompts from @collect24995 via Yahoo Realtime Search.
Dedupes by main_status_id + reply_status_id. Does not call chat bots.
"""
from __future__ import annotations
import argparse, json, re, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

JST = timezone(timedelta(hours=8))
UA = {"User-Agent": "Mozilla/5.0 (compatible; x-prompt-crawler/1.0)"}
USER = "collect24995"
UID = "1850214362470072321"

def fetch_yahoo(query: str) -> dict:
    url = "https://search.yahoo.co.jp/realtime/search?p=" + urllib.parse.quote(query) + "&ei=UTF-8"
    req = urllib.request.Request(url, headers=UA)
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', raw, re.S)
    if not m:
        raise RuntimeError("Yahoo __NEXT_DATA__ missing")
    return json.loads(m.group(1))

def walk_tweets(data):
    out = []
    def walk(o):
        if isinstance(o, dict):
            if "id" in o and "displayTextBody" in o and o.get("screenName") == USER:
                body = (o.get("displayTextBody") or "").replace("\tSTART\t", "").replace("\tEND\t", "")
                ir = o.get("inReplyTo")
                reply_to = None
                if isinstance(ir, dict):
                    reply_to = str(ir.get("id") or ir.get("statusId") or "") or None
                elif ir:
                    reply_to = str(ir)
                out.append({
                    "id": str(o["id"]),
                    "createdAt": o.get("createdAt"),
                    "body": body,
                    "inReplyTo": reply_to,
                    "url": f"https://x.com/{USER}/status/{o['id']}",
                })
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(data)
    # dedupe by id
    seen = {}
    for t in out:
        seen[t["id"]] = t
    return list(seen.values())

def is_prompt_reply(body: str) -> bool:
    b = body.strip()
    return b.startswith("プロンプト") and ("GPT" in b or "縦長" in b or "横長" in b or "ネガティブ" in b)

def is_prompt_main(body: str) -> bool:
    return "プロンプトはリプ" in body or "プロンプトはリプ欄" in body

def pair_prompts(tweets):
    by_id = {t["id"]: t for t in tweets}
    pairs = []
    # replies that look like prompt bodies: prefer those whose id is just after a lip main
    mains = [t for t in tweets if is_prompt_main(t["body"])]
    replies = [t for t in tweets if is_prompt_reply(t["body"])]
    # heuristic: reply id numerically near main (same second)
    used_r = set()
    for main in sorted(mains, key=lambda t: int(t["id"]), reverse=True):
        mid = int(main["id"])
        best = None
        for r in replies:
            if r["id"] in used_r:
                continue
            rid = int(r["id"])
            if 0 < rid - mid < 50:  # typically reply snowflake slightly larger
                best = r
                break
        if not best:
            # fallback: any prompt reply with inReplyTo == main
            for r in replies:
                if r["id"] in used_r:
                    continue
                if r.get("inReplyTo") == main["id"]:
                    best = r
                    break
        if best:
            used_r.add(best["id"])
            pairs.append({"main": main, "reply": best})
    return pairs

def load_used(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {"used": []}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(Path(__file__).resolve().parents[1] / "data"))
    ap.add_argument("--mark", action="store_true", help="mark selected as used")
    args = ap.parse_args()
    data_dir = Path(args.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    used_path = data_dir / "used.json"
    used = load_used(used_path)
    used_keys = {u.get("key") for u in used.get("used", [])}

    data = fetch_yahoo(f"ID:{USER} プロンプト")
    tweets = walk_tweets(data)
    pairs = pair_prompts(tweets)
    # newest first
    pairs.sort(key=lambda p: int(p["main"]["id"]), reverse=True)

    selected = None
    selection = None
    for i, p in enumerate(pairs):
        key = f"{p['main']['id']}:{p['reply']['id']}"
        if key in used_keys:
            continue
        # skip incomplete additive-only replies
        body = p["reply"]["body"]
        if len(body) < 40 or ("追加" in body and "縦長" not in body and "横長" not in body):
            continue
        selected = p
        selection = "new_latest" if i == 0 else "backfill_unused"
        break

    out = {"ok": bool(selected), "selection": selection, "tweet_count": len(tweets), "pair_count": len(pairs)}
    if selected:
        main, reply = selected["main"], selected["reply"]
        ts = datetime.fromtimestamp(main["createdAt"], tz=JST).strftime("%Y-%m-%d %H:%M") if main.get("createdAt") else None
        rec = {
            "key": f"{main['id']}:{reply['id']}",
            "main_status_id": main["id"],
            "reply_status_id": reply["id"],
            "main_url": main["url"],
            "reply_url": reply["url"],
            "posted_at_jst": f"{ts} Asia/Shanghai" if ts else None,
            "selection": selection,
            "raw_prompt": reply["body"],
            "main_body": main["body"],
        }
        out["record"] = rec
        (data_dir / "current_selection.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
        if args.mark:
            used.setdefault("used", []).append({**rec, "processed_at": datetime.now(JST).isoformat()})
            used_path.write_text(json.dumps(used, ensure_ascii=False, indent=2))
    (data_dir / "last_crawl.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
