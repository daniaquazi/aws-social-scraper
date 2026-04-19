import json
import os
import logging
import boto3

from scraper import get_subreddit_posts, get_post_comments, SUBREDDITS
from parser import parse_posts, parse_comments

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get("S3_BUCKET", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "prod")


def lambda_handler(event, context):
    """
    Entry point for the Lambda function.
    Triggered by SQS — each message contains a subreddit to scrape.
    Fetches hot posts and their comments, saves to S3.
    """
    results = []

    for record in event.get("Records", []):
        message = json.loads(record["body"])
        subreddit = message.get("subreddit")

        if not subreddit:
            logger.warning("No subreddit in message — using defaults")
            subreddit = SUBREDDITS[0]

        logger.info("Processing r/%s", subreddit)

        try:
            raw_posts = get_subreddit_posts(subreddit, limit=10)
            parsed_posts = parse_posts(raw_posts, subreddit)
            save_to_s3(raw_posts, parsed_posts, subreddit, "posts")

            all_comments = []
            for post in raw_posts[:3]:
                post_id = post.get("id")
                if post_id:
                    raw_comments = get_post_comments(subreddit, post_id, limit=20)
                    parsed_comments = parse_comments(raw_comments, subreddit, post_id)
                    all_comments.extend(parsed_comments)

            if all_comments:
                save_to_s3(all_comments, all_comments, subreddit, "comments")

            results.append({
                "subreddit": subreddit,
                "status": "success",
                "posts_scraped": len(parsed_posts),
                "comments_scraped": len(all_comments)
            })

            logger.info(
                "Done r/%s — %d posts, %d comments",
                subreddit, len(parsed_posts), len(all_comments)
            )

        except Exception as e:
            logger.error("Failed to scrape r/%s: %s", subreddit, str(e))
            results.append({
                "subreddit": subreddit,
                "status": "failed",
                "error": str(e)
            })
            raise

    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }


def save_to_s3(raw_data, parsed_data, subreddit, data_type):
    """Save raw and processed data to S3."""
    from datetime import datetime

    s3 = boto3.client("s3")
    timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H%M%S")

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"raw/{subreddit}/{data_type}/{timestamp}.json",
        Body=json.dumps(raw_data, indent=2),
        ContentType="application/json"
    )

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"processed/{subreddit}/{data_type}/{timestamp}.json",
        Body=json.dumps(parsed_data, indent=2),
        ContentType="application/json"
    )

    logger.info("Saved %s/%s to S3", subreddit, data_type)
