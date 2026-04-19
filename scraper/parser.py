import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def parse_posts(raw_posts, subreddit):
    """
    Clean and structure raw Reddit post data.
    Returns a list of clean post dictionaries.
    """
    parsed = []

    for post in raw_posts:
        if not post.get("title"):
            continue

        parsed.append({
            "id": post.get("id"),
            "subreddit": subreddit,
            "title": post.get("title", "").strip(),
            "author": post.get("author", "[deleted]"),
            "score": post.get("score", 0),
            "upvote_ratio": post.get("upvote_ratio", 0),
            "num_comments": post.get("num_comments", 0),
            "permalink": post.get("permalink"),
            "body": post.get("selftext", "").strip()[:500] or None,
            "created_utc": post.get("created_utc"),
            "parsed_at": datetime.utcnow().isoformat(),
        })

    logger.info("Parsed %d posts from r/%s", len(parsed), subreddit)
    return parsed


def parse_comments(raw_comments, subreddit, post_id):
    """
    Clean and structure raw Reddit comment data.
    Filters out deleted/empty comments.
    Returns a list of clean comment dictionaries.
    """
    parsed = []

    for comment in raw_comments:
        body = comment.get("body", "").strip()

        if not body or body in ("[deleted]", "[removed]"):
            continue

        if len(body) < 5:
            continue

        parsed.append({
            "id": comment.get("id"),
            "post_id": post_id,
            "subreddit": subreddit,
            "author": comment.get("author", "[deleted]"),
            "body": body[:1000],
            "score": comment.get("score", 0),
            "created_utc": comment.get("created_utc"),
            "parsed_at": datetime.utcnow().isoformat(),
            "word_count": len(body.split())
        })

    logger.info("Parsed %d comments for post %s", len(parsed), post_id)
    return parsed
