import json
import pytest
from unittest.mock import patch

SAMPLE_STORIES_RESPONSE = {
    "hits": [
        {
            "objectID": "43001234",
            "title": "GPT-5 released with major improvements",
            "url": "https://example.com/gpt5",
            "author": "techuser1",
            "points": 500,
            "num_comments": 120,
            "created_at": "2026-04-20T10:00:00.000Z",
            "story_text": ""
        },
        {
            "objectID": "43001235",
            "title": "Is AI going to replace programmers?",
            "url": "https://example.com/ai-programmers",
            "author": "devuser2",
            "points": 300,
            "num_comments": 80,
            "created_at": "2026-04-20T09:00:00.000Z",
            "story_text": ""
        }
    ]
}

SAMPLE_COMMENTS_RESPONSE = {
    "hits": [
        {
            "objectID": "c1",
            "author": "commenter1",
            "comment_text": "This is a really interesting development in AI.",
            "created_at": "2026-04-20T10:05:00.000Z",
            "parent_id": "43001234",
            "story_id": "43001234"
        },
        {
            "objectID": "c2",
            "author": "commenter2",
            "comment_text": "",
            "created_at": "2026-04-20T10:06:00.000Z",
            "parent_id": "43001234",
            "story_id": "43001234"
        },
        {
            "objectID": "c3",
            "author": "commenter3",
            "comment_text": "I think the implications for software development are huge.",
            "created_at": "2026-04-20T10:07:00.000Z",
            "parent_id": "43001234",
            "story_id": "43001234"
        }
    ]
}


@patch("scraper._get_json")
def test_get_top_stories(mock_get_json):
    """Fetches and returns stories from Hacker News."""
    from scraper import get_top_stories

    mock_get_json.return_value = SAMPLE_STORIES_RESPONSE
    stories = get_top_stories(limit=2)

    assert len(stories) == 2
    assert stories[0]["id"] == "43001234"
    assert stories[0]["title"] == "GPT-5 released with major improvements"
    assert stories[0]["score"] == 500


@patch("scraper._random_delay")
@patch("scraper._get_json")
def test_get_comments_filters_empty(mock_get_json, mock_delay):
    """Filters out comments with no text."""
    from scraper import get_comments

    mock_get_json.return_value = SAMPLE_COMMENTS_RESPONSE
    comments = get_comments("43001234", limit=10)

    assert len(comments) == 2
    texts = [c["text"] for c in comments]
    assert "" not in texts


def test_parse_story():
    """Parser structures story correctly."""
    from parser import parse_story

    raw = {
        "id": "43001234",
        "title": "  AI News  ",
        "url": "https://example.com",
        "author": "user1",
        "score": 200,
        "num_comments": 50,
        "text": "",
        "created_utc": "2026-04-20T10:00:00.000Z"
    }
    parsed = parse_story(raw)

    assert parsed["title"] == "AI News"
    assert parsed["score"] == 200
    assert parsed["source"] == "hackernews"


def test_parse_comments_filters_short():
    """Parser removes comments that are too short."""
    from parser import parse_comments

    raw = [
        {"id": "1", "author": "u1", "text": "ok", "created_utc": "2026-04-20T10:00:00.000Z"},
        {"id": "2", "author": "u2", "text": "This is a much longer and more useful comment.", "created_utc": "2026-04-20T10:01:00.000Z"},
        {"id": "3", "author": "u3", "text": "Great post with lots of detail here.", "created_utc": "2026-04-20T10:02:00.000Z"},
    ]
    parsed = parse_comments(raw, "43001234")

    assert len(parsed) == 2


def test_clean_html():
    """HTML cleaner strips tags and decodes entities."""
    from parser import _clean_html

    html = "<p>This is <b>bold</b> and has &amp; entity &gt; here</p>"
    cleaned = _clean_html(html)

    assert "<p>" not in cleaned
    assert "<b>" not in cleaned
    assert "&amp;" not in cleaned
    assert "bold" in cleaned
    assert "&" in cleaned


def test_parse_comments_includes_word_count():
    """Parser adds word count to each comment."""
    from parser import parse_comments

    raw = [
        {"id": "1", "author": "u1", "text": "This has exactly five words here", "created_utc": "2026-04-20T10:00:00.000Z"}
    ]
    parsed = parse_comments(raw, "43001234")

    assert parsed[0]["word_count"] == 6
