"""
Blueprint Backend — Tests for Figma Design Context Transformer

Verifies transform_design_context produces compact, LLM-ready structure
from raw Figma API response. Pure function — no mocks needed.
"""

import json
import pytest

from app.figma_context import transform_design_context


@pytest.fixture
def sample_figma_response() -> dict:
    """Sample design_context matching Figma API response structure."""
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
                    "paddingTop": 48,
                    "paddingBottom": 24,
                    "fills": [{"type": "SOLID", "color": {"r": 1, "g": 1, "b": 1, "a": 1}}],
                    "children": [
                        {
                            "id": "1:1",
                            "type": "TEXT",
                            "name": "Title",
                            "characters": "Welcome back",
                            "style": {
                                "fontFamily": "Inter",
                                "fontSize": 24,
                                "fontWeight": 700,
                                "lineHeightPx": 32,
                            },
                            "fills": [
                                {"type": "SOLID", "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1}}
                            ],
                            "absoluteBoundingBox": {"x": 24, "y": 48, "width": 327, "height": 32},
                        },
                        {
                            "id": "1:2",
                            "type": "RECTANGLE",
                            "name": "Button",
                            "absoluteBoundingBox": {"x": 24, "y": 200, "width": 327, "height": 44},
                            "fills": [
                                {"type": "SOLID", "color": {"r": 0.76, "g": 0.48, "b": 0.3, "a": 1}}
                            ],
                            "cornerRadius": 8,
                        },
                        {
                            "id": "1:3",
                            "type": "VECTOR",
                            "name": "Icon",
                            "absoluteBoundingBox": {"x": 50, "y": 300, "width": 24, "height": 24},
                            "fills": [{"type": "SOLID", "color": {"r": 0, "g": 0, "b": 0, "a": 1}}],
                        },
                    ],
                }
            }
        },
        "components": {"comp1": {"name": "Button"}},
        "styles": {"style1": {"name": "Heading"}},
    }


class TestTransformDesignContext:
    """Unit tests for transform_design_context."""

    def test_transform_empty_input(self):
        """Empty dict returns valid structure with empty tree."""
        result = transform_design_context({})
        assert result["frame"]["name"] is None
        assert result["frame"]["width"] is None
        assert result["frame"]["height"] is None
        assert result["tree"] == []
        assert result["components"] == {}
        assert result["styles"] == {}

    def test_transform_minimal_frame(self, sample_figma_response):
        """Single FRAME node produces correct frame metadata (name, width, height)."""
        result = transform_design_context(sample_figma_response)
        assert result["frame"]["name"] == "Login"
        assert result["frame"]["width"] == 375
        assert result["frame"]["height"] == 812

    def test_transform_text_node(self, sample_figma_response):
        """TEXT node extracts characters, fontFamily, fontSize, fontWeight, color."""
        result = transform_design_context(sample_figma_response)

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
        assert text["content"] == "Welcome back"
        assert text["style"]["fontFamily"] == "Inter"
        assert text["style"]["fontSize"] == 24
        assert text["style"]["fontWeight"] == 700
        assert "color" in text["style"]

    def test_transform_rectangle_node(self, sample_figma_response):
        """RECTANGLE extracts fills (solid color), cornerRadius, dimensions."""
        result = transform_design_context(sample_figma_response)

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
        assert "fill" in rect["style"]
        assert rect["style"]["cornerRadius"] == 8
        assert rect.get("width") == 327
        assert rect.get("height") == 44

    def test_transform_layout_properties(self, sample_figma_response):
        """FRAME with layoutMode=VERTICAL extracts mode, gap (itemSpacing), padding."""
        result = transform_design_context(sample_figma_response)
        frame = next((n for n in result["tree"] if n.get("type") == "FRAME"), None)
        assert frame is not None
        assert frame["layout"]["mode"] == "VERTICAL"
        assert frame["layout"]["gap"] == 16
        assert frame["layout"]["padding"] == {
            "left": 24,
            "right": 24,
            "top": 48,
            "bottom": 24,
        }

    def test_transform_nested_children(self, sample_figma_response):
        """Parent with children produces nested tree structure."""
        result = transform_design_context(sample_figma_response)
        frame = next((n for n in result["tree"] if n.get("type") == "FRAME"), None)
        assert frame is not None
        assert "children" in frame
        children = frame["children"]
        assert len(children) >= 2
        types = [c["type"] for c in children]
        assert "TEXT" in types
        assert "RECTANGLE" in types
        assert "VECTOR" in types

    def test_transform_depth_limit(self):
        """Deeply nested tree (>5 levels) is pruned at max_depth."""
        # Build 7 levels deep
        child = {"id": "leaf", "type": "RECTANGLE", "name": "Leaf", "children": []}
        for i in range(6):
            child = {
                "id": f"level-{i}",
                "type": "FRAME",
                "name": f"Level{i}",
                "children": [child],
            }
        raw = {
            "nodes": {
                "1:1": {
                    "document": {
                        "id": "1:1",
                        "name": "Root",
                        "type": "FRAME",
                        "absoluteBoundingBox": {"width": 100, "height": 100},
                        "children": [child],
                    }
                }
            },
            "components": {},
            "styles": {},
        }
        result = transform_design_context(raw)
        # Tree should be pruned — deepest nodes beyond depth 5 should not appear
        def max_depth(nodes, d=0):
            if not nodes:
                return d
            return max(max_depth(n.get("children", []), d + 1) for n in nodes)

        assert max_depth(result["tree"]) <= 5

    def test_transform_vector_marked_as_icon(self, sample_figma_response):
        """VECTOR node gets icon=True flag."""
        result = transform_design_context(sample_figma_response)

        def find_vector(nodes):
            for n in nodes:
                if n.get("type") == "VECTOR":
                    return n
                for c in n.get("children", []):
                    found = find_vector([c])
                    if found:
                        return found
            return None

        vector = find_vector(result["tree"])
        assert vector is not None
        assert vector.get("icon") is True

    def test_transform_boolean_operation_marked_as_icon(self):
        """BOOLEAN_OPERATION node gets icon=True flag."""
        raw = {
            "nodes": {
                "1:1": {
                    "document": {
                        "id": "1:1",
                        "name": "Frame",
                        "type": "FRAME",
                        "absoluteBoundingBox": {"width": 100, "height": 100},
                        "children": [
                            {
                                "id": "1:2",
                                "name": "Icon",
                                "type": "BOOLEAN_OPERATION",
                                "absoluteBoundingBox": {"width": 24, "height": 24},
                            }
                        ],
                    }
                }
            },
            "components": {},
            "styles": {},
        }
        result = transform_design_context(raw)

        def find_boolean(nodes):
            for n in nodes:
                if n.get("type") == "BOOLEAN_OPERATION":
                    return n
                for c in n.get("children", []):
                    found = find_boolean([c])
                    if found:
                        return found
            return None

        node = find_boolean(result["tree"])
        assert node is not None
        assert node.get("icon") is True

    def test_transform_image_fill_detected(self):
        """Node with fills containing type IMAGE gets image=True and dimensions."""
        raw = {
            "nodes": {
                "1:1": {
                    "document": {
                        "id": "1:1",
                        "name": "Frame",
                        "type": "FRAME",
                        "absoluteBoundingBox": {"width": 100, "height": 100},
                        "children": [
                            {
                                "id": "1:2",
                                "name": "Photo",
                                "type": "RECTANGLE",
                                "absoluteBoundingBox": {"width": 80, "height": 60},
                                "fills": [{"type": "IMAGE", "imageRef": "abc"}],
                            }
                        ],
                    }
                }
            },
            "components": {},
            "styles": {},
        }
        result = transform_design_context(raw)

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
        assert rect.get("image") is True
        assert rect.get("width") == 80
        assert rect.get("height") == 60

    def test_transform_components_passed_through(self, sample_figma_response):
        """Raw components dict passed through to output."""
        result = transform_design_context(sample_figma_response)
        assert result["components"] == {"comp1": {"name": "Button"}}

    def test_transform_styles_passed_through(self, sample_figma_response):
        """Raw styles dict passed through to output."""
        result = transform_design_context(sample_figma_response)
        assert result["styles"] == {"style1": {"name": "Heading"}}

    def test_transform_malformed_node(self):
        """Node missing document key handled gracefully (no crash)."""
        raw = {"nodes": {"x": {"document": None}}, "components": {}, "styles": {}}
        result = transform_design_context(raw)
        assert result["tree"] == []

        raw2 = {"nodes": {"x": {}}, "components": {}, "styles": {}}
        result2 = transform_design_context(raw2)
        assert result2["tree"] == []

    def test_transform_output_is_json_serializable(self, sample_figma_response):
        """Output can be json.dumps'd without error."""
        result = transform_design_context(sample_figma_response)
        json_str = json.dumps(result)
        assert len(json_str) > 0
        parsed = json.loads(json_str)
        assert parsed["frame"]["name"] == "Login"
