import time
import random
import logging
import boto3
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

MAX_RETRIES = 5
BASE_DELAY = 2

SUBREDDITS = [
    "artificial",
    "ChatGPT",
]


class RateLimitError(Exception):
    pass


class ScrapeError(Exception):
    pass


def get_subreddit_posts(subreddit, limit=25, sort="hot"):
    """
    Fetch posts from a subreddit using Reddit's public JSON API.
    Returns a list of post dictionaries.
    """
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    logger.info("Fetching posts from r/%s", subreddit)

    data = _get_json(url)
    posts = data.get("data", {}).get("children", [])

    results = []
    for post in posts:
        p = post.get("data", {})
        results.append({
            "id": p.get("id"),
            "title": p.get("title"),
            "author": p.get("author"),
            "score": p.get("score"),
            "upvote_ratio": p.get("upvote_ratio"),
            "num_comments": p.get("num_comments"),
            "url": p.get("url"),
            "permalink": f"https://www.reddit.com{p.get('permalink', '')}",
            "created_utc": p.get("created_utc"),
            "selftext": p.get("selftext", "")[:500],
            "subreddit": subreddit
        })

    logger.info("Fetched %d posts from r/%s", len(results), subreddit)
    return results


def get_post_comments(subreddit, post_id, limit=50):
    """
    Fetch comments for a specific Reddit post.
    Returns a list of comment dictionaries.
    """
    url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}.json?limit={limit}"
    logger.info("Fetching comments for post %s", post_id)

    data = _get_json(url)

    comments = []
    if len(data) > 1:
        comment_data = data[1].get("data", {}).get("children", [])
        for comment in comment_data:
            c = comment.get("data", {})
            if c.get("body") and c.get("body") != "[deleted]":
                comments.append({
                    "id": c.get("id"),
                    "author": c.get("author"),
                    "body": c.get("body", "")[:1000],
                    "score": c.get("score"),
                    "created_utc": c.get("created_utc"),
                    "post_id": post_id,
                    "subreddit": subreddit
                })

    logger.info("Fetched %d comments for post %s", len(comments), post_id)
    return comments


def _get_json(url):
    """
    Make a GET request with exponential backoff and jitter.
    Returns parsed JSON response.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)

            if response.status_code == 429:
                log_rate_limit(url)
                wait = _get_retry_after(response) or _backoff(attempt)
                logger.warning("Rate limited — waiting %ds", wait)
                time.sleep(wait)
                continue

            if response.status_code >= 500:
                wait = _backoff(attempt)
                logger.warning("Server error %d — waiting %ds", response.status_code, wait)
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


def _get_retry_after(response):
    """Read Retry-After header if present."""
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return int(retry_after)
        except ValueError:
            return None
    return None


def _random_delay():
    """Add a random human-like delay between requests."""
    time.sleep(random.uniform(1, 3))


def log_rate_limit(url):
    """Send a rate limit hit metric to CloudWatch."""
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
