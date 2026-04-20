import time
import random
import logging
import boto3
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BASE_URL = "https://hacker-news.firebaseio.com/v1"

HEADERS = {
    "User-Agent": "aws-social-scraper/1.0"
}

MAX_RETRIES = 5
BASE_DELAY = 2


class ScrapeError(Exception):
    pass


def get_top_stories(limit=10):
    """
    Fetch top story IDs from Hacker News.
    Returns a list of story IDs.
    """
    url = f"{BASE_URL}/topstories.json"
    logger.info("Fetching top story IDs from Hacker News")

    data = _get_json(url)
    story_ids = data[:limit]

    logger.info("Got %d story IDs", len(story_ids))
    return story_ids


def get_story(story_id):
    """
    Fetch a single story by ID.
    Returns story dictionary or None.
    """
    url = f"{BASE_URL}/item/{story_id}.json"
    data = _get_json(url)

    if not data or data.get("type") != "story":
        return None

    return {
        "id": data.get("id"),
        "title": data.get("title"),
        "url": data.get("url"),
        "author": data.get("by"),
        "score": data.get("score", 0),
        "num_comments": data.get("descendants", 0),
        "comment_ids": data.get("kids", []),
        "created_utc": data.get("time"),
        "text": data.get("text", "")
    }


def get_comments(comment_ids, limit=20):
    """
    Fetch comments for a story.
    Returns list of comment dictionaries.
    """
    comments = []

    for comment_id in comment_ids[:limit]:
        url = f"{BASE_URL}/item/{comment_id}.json"
        data = _get_json(url)

        if not data:
            continue

        text = data.get("text", "")
        if not text or data.get("deleted") or data.get("dead"):
            continue

        comments.append({
            "id": data.get("id"),
            "author": data.get("by"),
            "text": text[:1000],
            "created_utc": data.get("time"),
            "parent_id": data.get("parent")
        })

        _random_delay()

    logger.info("Fetched %d comments", len(comments))
    return comments


def _get_json(url):
    """
    Make a GET request with exponential backoff.
    Returns parsed JSON.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)

            if response.status_code == 429:
                wait = _backoff(attempt)
                logger.warning("Rate limited — waiting %ds", wait)
                time.sleep(wait)
                continue

            if response.status_code >= 500:
                wait = _backoff(attempt)
                logger.warning("Server error — waiting %ds", wait)
                time.sleep(wait)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            time.sleep(_backoff(attempt))
        except requests.exceptions.ConnectionError:
            time.sleep(_backoff(attempt))

    raise ScrapeError(f"Failed to fetch {url} after {MAX_RETRIES} attempts")


def _backoff(attempt):
    """Exponential backoff with jitter."""
    return (BASE_DELAY ** attempt) + random.uniform(0, 1)


def _random_delay():
    """Add a small delay between requests."""
    time.sleep(random.uniform(0.5, 1.5))


def log_rate_limit(url):
    """Send rate limit metric to CloudWatch."""
    try:
        cloudwatch = boto3.client("cloudwatch", region_name="eu-west-2")
        cloudwatch.put_metric_data(
            Namespace="Scraper",
            MetricData=[{
                "MetricName": "RateLimitHit",
                "Dimensions": [{"Name": "URL", "Value": url[:256]}],
                "Value": 1,
                "Unit": "Count"
            }]
        )
    except Exception as e:
        logger.warning("Failed to log rate limit metric: %s", str(e))
