import os
import json
import hashlib
import feedparser
import requests
from pathlib import Path

RSS_URL = "https://www.reddit.com/r/FreeGameFindings/new/.rss"
SEEN_FILE = Path("seen_items.json")

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

KEYWORDS = [
    "steam",
    "free",
    "free to keep",
    "100%",
    "giveaway",
]


def load_seen():
    if not SEEN_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_FILE.read_text(encoding="utf-8"))
        return set(data)
    except Exception:
        return set()


def save_seen(seen):
    SEEN_FILE.write_text(
        json.dumps(sorted(list(seen)), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def item_id(entry):
    base = entry.get("id") or entry.get("link") or entry.get("title")
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def is_relevant(title):
    text = title.lower()
    return any(keyword in text for keyword in KEYWORDS)


def send_to_discord(title, link):
    message = f"""【天天情報網｜免費遊戲速報】

🎮 {title}
🔗 {link}

⚠️ 自動轉發情報，實際平台、免費類型與截止時間請以原文及商店頁面為準。"""

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json={
            "username": "天天情報員",
            "content": message
        },
        timeout=20
    )

    response.raise_for_status()


def main():
    if not DISCORD_WEBHOOK_URL:
        raise RuntimeError("Missing DISCORD_WEBHOOK_URL secret.")

    feed = feedparser.parse(RSS_URL)
    seen = load_seen()
    new_seen = set(seen)

    # 第一次啟動時，避免把舊文章洗版全發出去
    if not seen:
        for entry in feed.entries[:20]:
            new_seen.add(item_id(entry))
        save_seen(new_seen)
        print("First run: saved existing items only, no messages sent.")
        return

    new_entries = []

    for entry in feed.entries[:20]:
        uid = item_id(entry)
        title = entry.get("title", "未知遊戲情報")
        link = entry.get("link", "")

        if uid not in seen and is_relevant(title):
            new_entries.append((title, link, uid))

        new_seen.add(uid)

    # 從舊到新發，避免順序亂掉
    for title, link, uid in reversed(new_entries):
        send_to_discord(title, link)
        print(f"Sent: {title}")

    save_seen(new_seen)


if __name__ == "__main__":
    main()
