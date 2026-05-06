import os
import json
import hashlib
import requests
from pathlib import Path

REDDIT_URL = "https://www.reddit.com/r/FreeGameFindings/new.json?limit=20"
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


def fetch_posts():
    headers = {
        "User-Agent": "tiantian-free-game-bot/1.0"
    }

    response = requests.get(REDDIT_URL, headers=headers, timeout=20)
    response.raise_for_status()

    data = response.json()
    posts = []

    for child in data.get("data", {}).get("children", []):
        post = child.get("data", {})

        title = post.get("title", "未知遊戲情報")
        reddit_link = "https://www.reddit.com" + post.get("permalink", "")
        external_link = post.get("url_overridden_by_dest") or post.get("url") or reddit_link
        post_id = post.get("id") or hashlib.sha256(reddit_link.encode("utf-8")).hexdigest()

        posts.append({
            "id": post_id,
            "title": title,
            "reddit_link": reddit_link,
            "external_link": external_link,
        })

    return posts


def is_relevant(title, external_link):
    text = f"{title} {external_link}".lower()
    return any(keyword in text for keyword in KEYWORDS)


def send_to_discord(title, external_link, reddit_link):
    message = f"""【天天情報網｜免費遊戲速報】

🎮 {title}

🔗 領取 / 商店連結：
{external_link}

🧾 情報來源：
{reddit_link}

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

    posts = fetch_posts()
    seen = load_seen()
    new_seen = set(seen)

    # 第一次啟動時，避免把舊文章洗版全發出去
    if not seen:
        for post in posts:
            new_seen.add(post["id"])
        save_seen(new_seen)
        print("First run: saved existing items only, no messages sent.")
        return

    new_posts = []

    for post in posts:
        post_id = post["id"]
        title = post["title"]
        external_link = post["external_link"]
        reddit_link = post["reddit_link"]

        if post_id not in seen and is_relevant(title, external_link):
            new_posts.append(post)

        new_seen.add(post_id)

    # 從舊到新發，避免順序亂掉
    for post in reversed(new_posts):
        send_to_discord(
            post["title"],
            post["external_link"],
            post["reddit_link"]
        )
        print(f"Sent: {post['title']}")

    save_seen(new_seen)


if __name__ == "__main__":
    main()
