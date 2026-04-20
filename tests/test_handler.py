import json
import pytest
from unittest.mock import patch, MagicMock

SAMPLE_TOP_STORIES = [1001, 1002, 1003]

SAMPLE_STORY = {
    "id": 1001,
    "type": "story",
    "title": "GPT-5 released with major improvements",
    "url": "https://example.com/gpt5",
    "by": "techuser1",
    "score": 500,
    "descendants": 120,
    "kids": [2001, 2002, 2003],
    "time": 1700000000,
    "text": ""
}

SAMPLE_COMMENT_1 = {
    "id": 2001,
    "type": "comment",
    "by": "commenter1",
    "text": "This is a really interesting development in AI.",
    "time": 1700000100,
    "parent": 1001
}

SAMPLE_COMMENT_2 = {
    "id": 2002,
    "type": "comment",
    "by": "commenter2",
    "text": "",
    "time": 1700000200,
    "parent": 1001
}

SAMPLE_COMMENT_3 = {
    "id": 2003,
    "type": "comment",
    "by": "commenter3",
    "text": "I think the implications for software development are huge.",
    "time": 1700000300,
    "parent": 1001
}


@patch("scraper._get_json")
def test_get_top_stories(mock_get_json):
    """Fetches and limits top story IDs."""
    from scraper import get_top_stories

    mock_get_json.return_value = SAMPLE_TOP_STORIES
    stories = get_top_stories(limit=2)

    assert len(stories) == 2
    assert stories[0] == 1001


@patch("scraper._get_json")
def test_get_story(mock_get_json):
    """Fetches and returns a story correctly."""
    from scraper import get_story

    mock_get_json.return_value = SAMPLE_STORY
    story = get_story(1001)

    assert story["id"] == 1001
    assert story["title"] == "GPT-5 released with major improvements"
    assert story["score"] == 500
    assert story["comment_ids"] == [2001, 2002, 2003]


@patch("scraper._random_delay")
@patch("scraper._get_json")
def test_get_comments_filters_empty(mock_get_json, mock_delay):
    """Filters out comments with no text."""
    from scraper import get_comments

    mock_get_json.side_effect = [
        SAMPLE_COMMENT_1,
        SAMPLE_COMMENT_2,
        SAMPLE_COMMENT_3
    ]
    comments = get_comments([2001, 2002, 2003])

    assert len(comments) == 2
    texts = [c["text"] for c in comments]
    assert "" not in texts


def test_parse_story():
    """Parser structures story correctly."""
    from parser import parse_story

    raw = {
        "id": 1001,
        "title": "  AI News  ",
        "url": "https://example.com",
        "author": "user1",
        "score": 200,
        "num_comments": 50,
        "text": "",
        "created_utc": 1700000000
    }
    parsed = parse_story(raw)

    assert parsed["title"] == "AI News"
    assert parsed["score"] == 200
    assert parsed["source"] == "hackernews"


def test_parse_comments_filters_short():
    """Parser removes comments that are too short."""
    from parser import parse_comments

    raw = [
        {"id": 1, "author": "u1", "text": "ok", "created_utc": 1700000000},
        {"id": 2, "author": "u2", "text": "This is a much longer and more useful comment.", "created_utc": 1700000001},
        {"id": 3, "author": "u3", "text": "Great post with lots of detail here.", "created_utc": 1700000002},
    ]
    parsed = parse_comments(raw, 1001)

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
