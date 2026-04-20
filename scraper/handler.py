import json
import os
import logging
import boto3
from datetime import datetime

from scraper import get_top_stories, get_comments
from parser import parse_story, parse_comments

logger = logging.getLogger()
logger.setLevel(logging.INFO)

S3_BUCKET = os.environ.get("S3_BUCKET", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "prod")


def lambda_handler(event, context):
    """
    Entry point for the Lambda function.
    Triggered by SQS — scrapes top Hacker News stories and comments.
    Saves raw and processed data to S3.
    """
    results = []

    for record in event.get("Records", []):
        message = json.loads(record["body"])
        limit = message.get("limit", 5)

        logger.info("Fetching top %d Hacker News stories", limit)

        try:
            raw_stories = get_top_stories(limit=limit)
            all_stories = []
            all_comments = []

            for raw_story in raw_stories:
                parsed_story = parse_story(raw_story)
                all_stories.append(parsed_story)

                story_id = raw_story.get("id")
                if story_id:
                    raw_comments = get_comments(story_id, limit=10)
                    parsed = parse_comments(raw_comments, story_id)
                    all_comments.extend(parsed)

            timestamp = datetime.utcnow().strftime("%Y/%m/%d/%H%M%S")

            if all_stories:
                save_to_s3(all_stories, "stories", timestamp)

            if all_comments:
                save_to_s3(all_comments, "comments", timestamp)

            results.append({
                "status": "success",
                "stories_scraped": len(all_stories),
                "comments_scraped": len(all_comments)
            })

            logger.info(
                "Done — %d stories, %d comments",
                len(all_stories), len(all_comments)
            )

        except Exception as e:
            logger.error("Failed: %s", str(e))
            results.append({
                "status": "failed",
                "error": str(e)
            })
            raise

    return {
        "statusCode": 200,
        "body": json.dumps(results)
    }


def save_to_s3(data, data_type, timestamp):
    """Save data to S3 under raw/ and processed/ prefixes."""
    s3 = boto3.client("s3")

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"raw/hackernews/{data_type}/{timestamp}.json",
        Body=json.dumps(data, indent=2),
        ContentType="application/json"
    )

    s3.put_object(
        Bucket=S3_BUCKET,
        Key=f"processed/hackernews/{data_type}/{timestamp}.json",
        Body=json.dumps(data, indent=2),
        ContentType="application/json"
    )

    logger.info("Saved %s to S3", data_type)
