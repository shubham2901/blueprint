"""
Blueprint Backend — Figma Design Context Transformer

Converts raw Figma API response to compact, LLM-friendly structure for code generation.
Mirrors Figma MCP get_design_context quality.

Purpose: Raw Figma nodes are verbose (100KB+). LLM needs structured, pruned context.
Output: frame, tree, components, styles — JSON-serializable for LLM.

Usage:
    from app.figma_context import transform_design_context
    compact = transform_design_context(raw_design_context)
"""

import time
from typing import Any

from app.config import log


def transform_design_context(raw: dict) -> dict:
    """
    Transform raw Figma design_context to compact, code-ready structure for LLM.

    Input: raw design_context from FigmaImportResponse (nodes, components, styles).
    Output structure:
        {
            "frame": { "name": str, "width": int, "height": int },
            "tree": [ { "id", "type", "name", "layout"?, "style"?, "content"?, "children": [...] } ],
            "components": {},  # pass through from raw
            "styles": {}       # pass through from raw
        }

    Args:
        raw: Raw design context dict from Figma API (nodes, components, styles).

    Returns:
        Compact dict suitable for LLM prompt. JSON-serializable.
    """
    start = time.perf_counter()
    nodes = raw.get("nodes", {})
    components = raw.get("components", {})
    styles = raw.get("styles", {})

    if not nodes:
        log("WARN", "design context transform empty input")
        return {
            "frame": {"name": None, "width": None, "height": None},
            "tree": [],
            "components": components,
            "styles": styles,
        }

    frame_name = None
    frame_width = None
    frame_height = None
    tree: list[dict] = []
    icon_count = 0
    image_count = 0

    for node_data in nodes.values():
        if not isinstance(node_data, dict):
            continue
        doc = node_data.get("document", {})
        if not doc:
            continue
        bbox = doc.get("absoluteBoundingBox", {})
        frame_name = doc.get("name")
        frame_width = bbox.get("width")
        frame_height = bbox.get("height")
        if frame_width is not None:
            frame_width = int(frame_width)
        if frame_height is not None:
            frame_height = int(frame_height)
        break

    log(
        "INFO",
        "design context transform started",
        node_count=len(nodes),
        frame_name=frame_name,
    )

    for node_data in nodes.values():
        if not isinstance(node_data, dict):
            continue
        doc = node_data.get("document", {})
        if not doc:
            continue
        flattened, icons, images = _flatten_node(doc, max_depth=5, depth=0)
        tree.extend(flattened)
        icon_count += icons
        image_count += images

    duration_ms = int((time.perf_counter() - start) * 1000)
    node_count_output = sum(1 for _ in _count_nodes(tree))

    log(
        "INFO",
        "design context transform completed",
        tree_depth=5,
        node_count_output=node_count_output,
        icon_count=icon_count,
        image_count=image_count,
        duration_ms=duration_ms,
    )

    return {
        "frame": {
            "name": frame_name,
            "width": frame_width,
            "height": frame_height,
        },
        "tree": tree,
        "components": components,
        "styles": styles,
    }


def _count_nodes(tree: list[dict]) -> list:
    """Recursively yield all nodes for counting."""
    for node in tree:
        yield node
        for child in node.get("children", []):
            yield from _count_nodes([child])


def _flatten_node(doc: dict, max_depth: int, depth: int = 0) -> tuple[list[dict], int, int]:
    """
    Recursively flatten a Figma document node.

    Returns:
        (list of node dicts for this level, icon_count, image_count)
    """
    if depth >= max_depth:
        return [], 0, 0

    node_type = doc.get("type", "UNKNOWN")
    node_id = doc.get("id", "")
    name = doc.get("name", "")

    node: dict[str, Any] = {
        "id": node_id,
        "type": node_type,
        "name": name,
    }

    icon_count = 0
    image_count = 0

    # Icon identification: VECTOR and BOOLEAN_OPERATION
    if node_type in ("VECTOR", "BOOLEAN_OPERATION"):
        node["icon"] = True
        icon_count += 1

    # Layout extraction
    layout_mode = doc.get("layoutMode")
    if layout_mode:
        layout: dict[str, Any] = {"mode": layout_mode}
        if doc.get("itemSpacing") is not None:
            layout["gap"] = doc.get("itemSpacing")
        padding = doc.get("paddingLeft"), doc.get("paddingRight"), doc.get("paddingTop"), doc.get("paddingBottom")
        if any(p is not None for p in padding):
            layout["padding"] = {
                "left": doc.get("paddingLeft"),
                "right": doc.get("paddingRight"),
                "top": doc.get("paddingTop"),
                "bottom": doc.get("paddingBottom"),
            }
        node["layout"] = layout

    # Bounding box
    bbox = doc.get("absoluteBoundingBox", {})
    if bbox:
        width = bbox.get("width")
        height = bbox.get("height")
        if width is not None:
            node["width"] = int(width)
        if height is not None:
            node["height"] = int(height)

    # TEXT
    if node_type == "TEXT":
        node["content"] = doc.get("characters", "")
        style = doc.get("style", {})
        text_style: dict[str, Any] = {}
        if style.get("fontFamily"):
            text_style["fontFamily"] = style["fontFamily"]
        if style.get("fontSize") is not None:
            text_style["fontSize"] = style["fontSize"]
        if style.get("fontWeight") is not None:
            text_style["fontWeight"] = style["fontWeight"]
        if style.get("lineHeightPx") is not None:
            text_style["lineHeightPx"] = style["lineHeightPx"]
        fills = doc.get("fills", [])
        color = _extract_color_from_fills(fills)
        if color:
            text_style["color"] = color
        if text_style:
            node["style"] = text_style

    # RECTANGLE, ELLIPSE
    elif node_type in ("RECTANGLE", "ELLIPSE"):
        node["style"] = _extract_fill_style(doc)
        # Check for IMAGE fills
        fills = doc.get("fills", [])
        for fill in fills if isinstance(fills, list) else []:
            if isinstance(fill, dict) and fill.get("type") == "IMAGE":
                node["image"] = True
                if bbox:
                    node["width"] = int(bbox.get("width", 0)) if bbox.get("width") is not None else None
                    node["height"] = int(bbox.get("height", 0)) if bbox.get("height") is not None else None
                image_count += 1
                break

    # VECTOR, BOOLEAN_OPERATION, IMAGE (fills with type IMAGE)
    elif node_type in ("VECTOR", "BOOLEAN_OPERATION"):
        node["style"] = _extract_fill_style(doc)
    else:
        # Generic: check for IMAGE fills in any node
        fills = doc.get("fills", [])
        for fill in fills if isinstance(fills, list) else []:
            if isinstance(fill, dict) and fill.get("type") == "IMAGE":
                node["image"] = True
                if bbox:
                    node["width"] = int(bbox.get("width", 0)) if bbox.get("width") is not None else None
                    node["height"] = int(bbox.get("height", 0)) if bbox.get("height") is not None else None
                image_count += 1
                break

    # Children
    children = doc.get("children", [])
    child_nodes: list[dict] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        child_list, c_icons, c_images = _flatten_node(child, max_depth, depth + 1)
        child_nodes.extend(child_list)
        icon_count += c_icons
        image_count += c_images

    if child_nodes:
        node["children"] = child_nodes

    return [node], icon_count, image_count


def _extract_color_from_fills(fills: list) -> str | None:
    """Extract solid fill color as hex string."""
    if not isinstance(fills, list):
        return None
    for fill in fills:
        if not isinstance(fill, dict):
            continue
        if fill.get("type") != "SOLID":
            continue
        color = fill.get("color", {})
        if not color:
            continue
        r = color.get("r", 0)
        g = color.get("g", 0)
        b = color.get("b", 0)
        a = color.get("a", 1)
        opacity = fill.get("opacity")
        if opacity is not None:
            a = a * opacity
        r = int(r * 255)
        g = int(g * 255)
        b = int(b * 255)
        if a >= 0.999:
            return f"#{r:02x}{g:02x}{b:02x}"
        return f"rgba({r},{g},{b},{round(a, 2)})"
    return None


def _extract_fill_style(doc: dict) -> dict:
    """Extract fill, cornerRadius, strokes for RECTANGLE/ELLIPSE/VECTOR."""
    style: dict[str, Any] = {}
    fills = doc.get("fills", [])
    color = _extract_color_from_fills(fills)
    if color:
        style["fill"] = color

    bbox = doc.get("absoluteBoundingBox", {})
    if bbox:
        w = bbox.get("width")
        h = bbox.get("height")
        if w is not None:
            style["width"] = int(w)
        if h is not None:
            style["height"] = int(h)

    corner_radius = doc.get("cornerRadius")
    if corner_radius is not None:
        style["cornerRadius"] = corner_radius

    strokes = doc.get("strokes", [])
    if strokes:
        stroke_color = _extract_color_from_fills(strokes)
        if stroke_color:
            style["stroke"] = stroke_color

    return style
