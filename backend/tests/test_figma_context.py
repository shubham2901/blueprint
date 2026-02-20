"""
Blueprint Backend — Tests for Figma Design Context Transformer

Verifies transform_design_context produces compact, LLM-ready structure
from raw Figma API response.
"""

import pytest

from app.figma_context import transform_design_context


def _sample_figma_import_response() -> dict:
    """Sample design_context matching FigmaImportResponse structure."""
    return {
        "nodes": {
            "123:456": {
                "document": {
                    "id": "123:456",
                    "name": "Login",
                    "type": "FRAME",
                    "absoluteBoundingBox": {"x": 0, "y": 0, "width": 375, "height": 812},
                    "layoutMode": "VERTICAL",
                    "itemSpacing": 16,
                    "paddingLeft": 24,
                    "paddingRight": 24,
                    "paddingTop": 24,
                    "paddingBottom": 24,
                    "children": [
                        {
                            "id": "123:457",
                            "name": "Welcome back",
                            "type": "TEXT",
                            "characters": "Welcome back",
                            "style": {
                                "fontFamily": "Inter",
                                "fontSize": 24,
                                "fontWeight": 700,
                                "lineHeightPx": 32,
                            },
                            "fills": [{"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1}}],
                        },
                        {
                            "id": "123:458",
                            "name": "Button",
                            "type": "RECTANGLE",
                            "absoluteBoundingBox": {"x": 24, "y": 100, "width": 200, "height": 44},
                            "fills": [{"type": "SOLID", "color": {"r": 0.88, "g": 0.49, "b": 0.28, "a": 1}}],
                            "cornerRadius": 8,
                        },
                    ],
                },
            },
        },
        "components": {},
        "styles": {},
    }


def _sample_with_vector_and_image() -> dict:
    """Sample with VECTOR (icon) and IMAGE fill for Task 2 verification."""
    return {
        "nodes": {
            "1:1": {
                "document": {
                    "id": "1:1",
                    "name": "Frame",
                    "type": "FRAME",
                    "absoluteBoundingBox": {"x": 0, "y": 0, "width": 100, "height": 100},
                    "children": [
                        {
                            "id": "1:2",
                            "name": "Icon",
                            "type": "VECTOR",
                            "absoluteBoundingBox": {"x": 10, "y": 10, "width": 24, "height": 24},
                        },
                        {
                            "id": "1:3",
                            "name": "Photo",
                            "type": "RECTANGLE",
                            "absoluteBoundingBox": {"x": 10, "y": 50, "width": 80, "height": 60},
                            "fills": [{"type": "IMAGE", "imageRef": "abc123"}],
                        },
                    ],
                },
            },
        },
        "components": {},
        "styles": {},
    }


def test_transform_returns_valid_structure():
    """Output has frame, tree, components, styles."""
    raw = _sample_figma_import_response()
    result = transform_design_context(raw)

    assert "frame" in result
    assert "tree" in result
    assert "components" in result
    assert "styles" in result
    assert result["frame"]["name"] == "Login"
    assert result["frame"]["width"] == 375
    assert result["frame"]["height"] == 812
    assert len(result["tree"]) > 0


def test_tree_nodes_have_layout_style_content():
    """Tree nodes have layout/style/content where applicable."""
    raw = _sample_figma_import_response()
    result = transform_design_context(raw)

    # Find FRAME (has layout)
    frame = next((n for n in result["tree"] if n.get("type") == "FRAME"), None)
    assert frame is not None
    assert "layout" in frame
    assert frame["layout"]["mode"] == "VERTICAL"
    assert frame["layout"]["gap"] == 16
    assert "padding" in frame["layout"]

    # Find TEXT (has content, style)
    def find_text(nodes):
        for n in nodes:
            if n.get("type") == "TEXT":
                return n
            for c in n.get("children", []):
                found = find_text([c])
                if found:
                    return found
        return None

    text = find_text(result["tree"])
    assert text is not None
    assert text.get("content") == "Welcome back"
    assert "style" in text
    assert text["style"].get("fontFamily") == "Inter"
    assert text["style"].get("fontSize") == 24

    # Find RECTANGLE (has style)
    def find_rect(nodes):
        for n in nodes:
            if n.get("type") == "RECTANGLE":
                return n
            for c in n.get("children", []):
                found = find_rect([c])
                if found:
                    return found
        return None

    rect = find_rect(result["tree"])
    assert rect is not None
    assert "style" in rect
    assert "fill" in rect["style"]


def test_empty_input_no_crash():
    """Empty or malformed input does not crash."""
    assert transform_design_context({})["tree"] == []
    assert transform_design_context({"nodes": {}})["tree"] == []
    assert transform_design_context({"nodes": {"x": None}})["tree"] == []
    assert transform_design_context({"nodes": {"x": {"document": None}}})["tree"] == []


def test_icon_identification():
    """VECTOR and BOOLEAN_OPERATION nodes get icon: True."""
    raw = _sample_with_vector_and_image()
    result = transform_design_context(raw)

    def find_by_type(nodes, t):
        for n in nodes:
            if n.get("type") == t:
                return n
            for c in n.get("children", []):
                found = find_by_type([c], t)
                if found:
                    return found
        return None

    vector = find_by_type(result["tree"], "VECTOR")
    assert vector is not None
    assert vector.get("icon") is True


def test_image_identification():
    """Nodes with IMAGE fills get image: True, width, height."""
    raw = _sample_with_vector_and_image()
    result = transform_design_context(raw)

    def find_by_type(nodes, t):
        for n in nodes:
            if n.get("type") == t:
                return n
            for c in n.get("children", []):
                found = find_by_type([c], t)
                if found:
                    return found
        return None

    rect = find_by_type(result["tree"], "RECTANGLE")
    assert rect is not None
    assert rect.get("image") is True
    assert rect.get("width") == 80
    assert rect.get("height") == 60


def test_output_is_json_serializable():
    """Result can be JSON-serialized (no non-serializable types)."""
    import json

    raw = _sample_figma_import_response()
    result = transform_design_context(raw)
    # Should not raise
    json_str = json.dumps(result)
    assert len(json_str) > 0
