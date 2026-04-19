import json
import pytest
from unittest.mock import patch, MagicMock


SAMPLE_POSTS_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "id": "abc123",
                    "title": "GPT-4 just blew my mind with this response",
                    "author": "techuser1",
                    "score": 1500,
                    "upvote_ratio": 0.95,
                    "num_comments": 342,
                    "url": "https://reddit.com/r/artificial/abc123",
                    "permalink": "/r/artificial/comments/abc123/gpt4_just_blew/",
                    "created_utc": 1700000000,
                    "selftext": "I asked it to explain quantum computing..."
                }
            },
            {
                "data": {
                    "id": "def456",
                    "title": "Is AI going to replace programmers?",
                    "author": "devuser2",
                    "score": 980,
                    "upvote_ratio": 0.88,
                    "num_comments": 210,
                    "url": "https://reddit.com/r/artificial/def456",
                    "permalink": "/r/artificial/comments/def456/ai_replace/",
                    "created_utc": 1700001000,
                    "selftext": ""
                }
            }
        ]
    }
}

SAMPLE_COMMENTS_RESPONSE = [
    {"data": {"children": []}},
    {
        "data": {
            "children": [
                {
                    "data": {
                        "id": "c1",
                        "author": "commenter1",
                        "body": "This is genuinely impressive, I tried it myself.",
                        "score": 200,
                        "created_utc": 1700000100
                    }
                },
                {
                    "data": {
                        "id": "c2",
                        "author": "commenter2",
                        "body": "[deleted]",
                        "score": 0,
                        "created_utc": 1700000200
                    }
                },
                {
                    "data": {
                        "id": "c3",
                        "author": "commenter3",
                        "body": "AI still has a long way to go before replacing anyone.",
                        "score": 150,
                        "created_utc": 1700000300
                    }
                }
            ]
        }
    }
]


@patch("scraper._get_json")
def test_get_subreddit_posts(mock_get_json):
    """Fetches and returns posts from a subreddit."""
    from scraper import get_subreddit_posts

    mock_get_json.return_value = SAMPLE_POSTS_RESPONSE
    posts = get_subreddit_posts("artificial", limit=2)

    assert len(posts) == 2
    assert posts[0]["id"] == "abc123"
    assert posts[0]["title"] == "GPT-4 just blew my mind with this response"
    assert posts[0]["subreddit"] == "artificial"


@patch("scraper._get_json")
def test_get_post_comments_filters_deleted(mock_get_json):
    """Filters out deleted comments from results."""
    from scraper import get_post_comments

    mock_get_json.return_value = SAMPLE_COMMENTS_RESPONSE
    comments = get_post_comments("artificial", "abc123")

    assert len(comments) == 2
    bodies = [c["body"] for c in comments]
    assert "[deleted]" not in bodies


def test_parse_posts():
    """Parser structures posts correctly."""
    from parser import parse_posts

    raw = [
        {
            "id": "abc123",
            "title": "  GPT-4 test  ",
            "author": "user1",
            "score": 500,
            "upvote_ratio": 0.9,
            "num_comments": 100,
            "permalink": "/r/artificial/abc123",
            "selftext": "some body text",
            "created_utc": 1700000000
        }
    ]
    parsed = parse_posts(raw, "artificial")

    assert len(parsed) == 1
    assert parsed[0]["title"] == "GPT-4 test"
    assert parsed[0]["subreddit"] == "artificial"
    assert parsed[0]["score"] == 500


def test_parse_comments_filters_short_and_deleted():
    """Parser removes deleted and very short comments."""
    from parser import parse_comments

    raw = [
        {"id": "c1", "author": "u1", "body": "Great post!", "score": 10, "created_utc": 1700000000},
        {"id": "c2", "author": "u2", "body": "[deleted]", "score": 0, "created_utc": 1700000001},
        {"id": "c3", "author": "u3", "body": "ok", "score": 1, "created_utc": 1700000002},
        {"id": "c4", "author": "u4", "body": "Really interesting take on AI safety.", "score": 50, "created_utc": 1700000003},
    ]
    parsed = parse_comments(raw, "artificial", "abc123")

    assert len(parsed) == 2
    assert all(c["body"] not in ("[deleted]", "[removed]") for c in parsed)
    assert all(len(c["body"]) >= 5 for c in parsed)


def test_parse_comments_includes_word_count():
    """Parser adds word count to each comment."""
    from parser import parse_comments

    raw = [
        {"id": "c1", "author": "u1", "body": "This has five words here", "score": 5, "created_utc": 1700000000}
    ]
    parsed = parse_comments(raw, "artificial", "abc123")

    assert parsed[0]["word_count"] == 5
