"""Session state management for HTTP transport.

FastMCP handles session state internally via Mcp-Session-Id headers.
This module is reserved for any custom session tracking needs
(e.g., per-session subscription lists for resource notifications).
"""

from __future__ import annotations

from collections import defaultdict


class SessionSubscriptions:
    """Track resource subscriptions per session."""

    def __init__(self) -> None:
        self._subscriptions: dict[str, set[str]] = defaultdict(set)

    def subscribe(self, session_id: str, resource_uri: str) -> None:
        self._subscriptions[session_id].add(resource_uri)

    def unsubscribe(self, session_id: str, resource_uri: str) -> None:
        self._subscriptions[session_id].discard(resource_uri)

    def get_subscribers(self, resource_uri: str) -> set[str]:
        """Get all session IDs subscribed to a resource."""
        return {
            sid for sid, uris in self._subscriptions.items()
            if resource_uri in uris
        }

    def remove_session(self, session_id: str) -> None:
        self._subscriptions.pop(session_id, None)


# Singleton for the server
subscriptions = SessionSubscriptions()
