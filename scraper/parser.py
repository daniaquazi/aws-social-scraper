import logging
import re
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def parse_story(raw_story):
    """
    Clean and structure a raw Hacker News story.
    """
    return {
        "id": raw_story.get("id"),
        "title": raw_story.get("title", "").strip(),
        "url": raw_story.get("url"),
        "author": raw_story.get("author"),
        "score": raw_story.get("score", 0),
        "num_comments": raw_story.get("num_comments", 0),
        "text": _clean_html(raw_story.get("text", "")),
        "created_utc": raw_story.get("created_utc"),
        "parsed_at": datetime.utcnow().isoformat(),
        "source": "hackernews"
    }


def parse_comments(raw_comments, story_id):
    """
    Clean and structure raw Hacker News comments.
    Filters out empty or very short comments.
    """
    parsed = []

    for comment in raw_comments:
        text = _clean_html(comment.get("text", "")).strip()

        if not text or len(text) < 10:
            continue

        parsed.append({
            "id": comment.get("id"),
            "story_id": story_id,
            "author": comment.get("author"),
            "text": text[:1000],
            "word_count": len(text.split()),
            "created_utc": comment.get("created_utc"),
            "parsed_at": datetime.utcnow().isoformat(),
            "source": "hackernews"
        })

    logger.info("Parsed %d comments for story %s", len(parsed), story_id)
    return parsed


def _clean_html(text):
    """
    Remove HTML tags from Hacker News comment text.
    HN comments contain basic HTML like <p>, <a>, <i>.
    """
    if not text:
        return ""

    text = re.sub(r"<a[^>]*>(.*?)</a>", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&#x27;", "'")
    text = text.replace("&quot;", '"')
    text = text.replace("&amp;", "&")
    text = text.replace("&gt;", ">")
    text = text.replace("&lt;", "<")
    text = " ".join(text.split())

    return text.strip()
