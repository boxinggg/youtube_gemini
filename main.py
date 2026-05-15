import os
import json
import time
import logging
from pathlib import Path

import feedparser
import requests
from dotenv import load_dotenv
from google import genai

BASE_DIR = Path(__file__).resolve().parent
PROCESSED_FILE = BASE_DIR / "processed_videos.json"
CHANNELS_FILE = BASE_DIR / "channels.txt"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
PUSHPLUS_TOKEN = os.getenv("PUSHPLUS_TOKEN")
CLAWBOT_WEBHOOK = os.getenv("CLAWBOT_WEBHOOK")

if not GEMINI_API_KEY:
    raise ValueError("请设置 GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)


def load_processed():
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text(encoding="utf-8")))
    return set()


def save_processed(processed):
    PROCESSED_FILE.write_text(
        json.dumps(sorted(processed), ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def load_channels():
    if not CHANNELS_FILE.exists():
        raise FileNotFoundError("未找到 channels.txt")
    return [
        line.strip()
        for line in CHANNELS_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def get_latest_video(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(url)
    if not feed.entries:
        return None

    entry = feed.entries[0]
    return {
        "video_id": getattr(entry, "yt_videoid", None),
        "title": entry.title,
        "link": entry.link,
        "channel": getattr(entry, "author", "Unknown"),
    }


def summarize_video(title, url, channel):
    prompt = f"""
请根据以下 YouTube 视频信息，用简体中文生成结构化摘要。

频道：{channel}
标题：{title}
链接：{url}

输出格式：
1. 核心观点（3-5条）
2. 关键数据（如果有）
3. 投资启发（如果适用）
4. 一句话总结

如果无法直接获取视频内容，请基于标题和公开信息进行合理总结，并明确说明。
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text


def send_pushplus(message, title):
    if not PUSHPLUS_TOKEN:
        return False

    response = requests.post(
        "https://www.pushplus.plus/send",
        json={
            "token": PUSHPLUS_TOKEN,
            "title": title,
            "content": message,
            "template": "txt"
        },
        timeout=30
    )
    response.raise_for_status()
    return True


def send_clawbot(message, title):
    if not CLAWBOT_WEBHOOK:
        return False

    # 通用 JSON 格式；如你的 ClawBot 接口字段不同，可按 README 调整
    response = requests.post(
        CLAWBOT_WEBHOOK,
        json={
            "title": title,
            "content": message,
            "text": message
        },
        timeout=30
    )
    response.raise_for_status()
    return True


def send_notifications(message, title):
    sent = False

    try:
        sent = send_pushplus(message, title) or sent
        if PUSHPLUS_TOKEN:
            logging.info("PushPlus 推送成功")
    except Exception:
        logging.exception("PushPlus 推送失败")

    try:
        sent = send_clawbot(message, title) or sent
        if CLAWBOT_WEBHOOK:
            logging.info("ClawBot 推送成功")
    except Exception:
        logging.exception("ClawBot 推送失败")

    if not sent:
        logging.warning("未配置任何推送渠道，输出到控制台。")
        print("\n" + "=" * 80)
        print(message)
        print("=" * 80 + "\n")


def process_once():
    processed = load_processed()

    for channel_id in load_channels():
        try:
            latest = get_latest_video(channel_id)
            if not latest or not latest["video_id"]:
                continue

            if latest["video_id"] in processed:
                continue

            logging.info("发现新视频: %s", latest["title"])

            summary = summarize_video(
                latest["title"],
                latest["link"],
                latest["channel"]
            )

            message = (
                f"📺 {latest['channel']}\n"
                f"📝 {latest['title']}\n\n"
                f"{summary}\n\n"
                f"🔗 {latest['link']}"
            )

            send_notifications(message, latest["title"])

            processed.add(latest["video_id"])
            save_processed(processed)

            time.sleep(3)

        except Exception as e:
            logging.exception("处理频道 %s 时出错: %s", channel_id, e)


if __name__ == "__main__":
    process_once()
