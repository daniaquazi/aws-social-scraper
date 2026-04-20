import time
import random
import logging
import boto3
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

BASE_URL = "https://hn.algolia.com/api/v1"

HEADERS = {
    "User-Agent": "aws-social-scraper/1.0"
}

MAX_RETRIES = 5
BASE_DELAY = 2


class ScrapeError(Exception):
    pass


def get_top_stories(limit=10):
    """
    Fetch top stories from Hacker News via Algolia API.
    Returns a list of story dictionaries directly.
    """
    url = f"{BASE_URL}/search?tags=front_page&hitsPerPage={limit}"
    logger.info("Fetching top %d stories from Hacker News", limit)

    data = _get_json(url)
    stories = data.get("hits", [])

    results = []
    for s in stories:
        results.append({
            "id": s.get("objectID"),
            "title": s.get("title"),
            "url": s.get("url"),
            "author": s.get("author"),
            "score": s.get("points", 0),
            "num_comments": s.get("num_comments", 0),
            "created_utc": s.get("created_at"),
            "text": s.get("story_text", "")
        })

    logger.info("Got %d stories", len(results))
    return results


def get_comments(story_id, limit=20):
    """
    Fetch comments for a story via Algolia API.
    Returns list of comment dictionaries.
    """
    url = f"{BASE_URL}/search?tags=comment,story_{story_id}&hitsPerPage={limit}"
    logger.info("Fetching comments for story %s", story_id)

    data = _get_json(url)
    hits = data.get("hits", [])

    comments = []
    for c in hits:
        text = c.get("comment_text", "")
        if not text or len(text) < 10:
            continue

        comments.append({
            "id": c.get("objectID"),
            "author": c.get("author"),
            "text": text[:1000],
            "created_utc": c.get("created_at"),
            "parent_id": c.get("parent_id"),
            "story_id": story_id
        })

    logger.info("Fetched %d comments for story %s", len(comments), story_id)
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
                log_rate_limit(url)
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
            _random_delay()
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
