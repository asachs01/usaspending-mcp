"""Tests for transport configuration and session management."""

from usaspending_mcp.transport.http import get_http_config
from usaspending_mcp.transport.session import SessionSubscriptions


def test_http_config_defaults():
    config = get_http_config()
    assert config["host"] == "0.0.0.0"
    assert config["port"] == 8765


def test_session_subscriptions():
    subs = SessionSubscriptions()

    subs.subscribe("session-1", "usaspending://agencies")
    subs.subscribe("session-1", "usaspending://data-freshness")
    subs.subscribe("session-2", "usaspending://agencies")

    # Both sessions subscribed to agencies
    assert subs.get_subscribers("usaspending://agencies") == {"session-1", "session-2"}

    # Only session-1 subscribed to data-freshness
    assert subs.get_subscribers("usaspending://data-freshness") == {"session-1"}

    # No subscribers for glossary
    assert subs.get_subscribers("usaspending://glossary") == set()


def test_session_unsubscribe():
    subs = SessionSubscriptions()
    subs.subscribe("s1", "usaspending://agencies")
    subs.unsubscribe("s1", "usaspending://agencies")
    assert subs.get_subscribers("usaspending://agencies") == set()


def test_session_removal():
    subs = SessionSubscriptions()
    subs.subscribe("s1", "usaspending://agencies")
    subs.subscribe("s1", "usaspending://data-freshness")
    subs.remove_session("s1")
    assert subs.get_subscribers("usaspending://agencies") == set()
    assert subs.get_subscribers("usaspending://data-freshness") == set()
