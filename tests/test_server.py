"""Basic tests for server startup and manifest."""

from usaspending_mcp import extension_manifest


def test_extension_manifest_fields():
    assert extension_manifest["name"] == "usaspending-mcp"
    assert "stdio" in extension_manifest["transport_modes"]
    assert "http" in extension_manifest["transport_modes"]
    assert extension_manifest["no_auth_required"] is True


def test_extension_manifest_capabilities():
    caps = extension_manifest["capabilities"]
    assert "tools" in caps
    assert "resources" in caps
    assert "elicitation" in caps
    assert "notifications" in caps
