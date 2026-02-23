"""
Dry-run scraper for AlternativeTo.net — via Jina Reader

Jina Reader renders the JS-heavy page and returns clean markdown.
This script tests real extraction and shows what we'd store.

Usage:
    cd backend
    python3 -m scripts.dry_run_alternativeto
"""

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field

import httpx


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AlternativeItem:
    name: str = ""
    description: str = ""               # from comparison text
    url: str = ""                       # alternativeto.net URL
    platforms: list[str] = field(default_factory=list)
    license_model: str = ""             # "Free", "Freemium", "Paid", "Open Source"
    features: list[str] = field(default_factory=list)
    comments_count: int = 0             # community engagement signal
    comparison_notes: list[str] = field(default_factory=list)  # "X is Free and Open Source"


@dataclass
class ScrapeResult:
    product_name: str = ""
    source_url: str = ""
    alternatives_count: int = 0
    alternatives: list[AlternativeItem] = field(default_factory=list)
    raw_markdown_length: int = 0
    scrape_duration_ms: int = 0
    error: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Jina Reader Client
# ─────────────────────────────────────────────────────────────────────────────

JINA_API_KEY = os.environ.get("JINA_API_KEY", "")


async def fetch_via_jina(client: httpx.AsyncClient, url: str) -> str:
    jina_url = f"https://r.jina.ai/{url}"
    headers = {
        "Accept": "text/markdown",
        "User-Agent": "Mozilla/5.0 (compatible; Blueprint/1.0)",
    }
    if JINA_API_KEY:
        headers["Authorization"] = f"Bearer {JINA_API_KEY}"
    resp = await client.get(jina_url, headers=headers, timeout=30.0)
    resp.raise_for_status()
    return resp.text


# ─────────────────────────────────────────────────────────────────────────────
# Parser — based on ACTUAL Jina markdown output from AlternativeTo
# ─────────────────────────────────────────────────────────────────────────────
#
# Real format discovered (Slack example):
#
#   1.                                    <-- numbered list item starts entry
#   #### Cost / License                   <-- license section
#       *   Free Personal
#       *   Open Source([AGPL-3.0](...))
#   #### Platforms                        <-- platforms section
#       *   Mac
#       *   Windows
#       *   ...
#   ![Image: screenshots...]              <-- screenshots (skip)
#   Is**Element**a good alternative ...   <-- NAME is here!
#   13 comments                           <-- engagement count
#       *   Element is**Free**...Slack... <-- comparison notes
#   2.                                    <-- next entry
# ─────────────────────────────────────────────────────────────────────────────


def parse_alternatives_from_jina_markdown(markdown: str, product_name: str) -> list[AlternativeItem]:
    """Parse AlternativeTo alternatives from Jina-rendered markdown."""
    alternatives: list[AlternativeItem] = []
    lines = markdown.split("\n")

    current: AlternativeItem | None = None
    section = ""  # "license", "platforms", "comparison"

    for line in lines:
        stripped = line.strip()

        # ── New entry: numbered list item (e.g., "1.   " or "12.   ")
        if re.match(r'^\d+\.\s*$', stripped):
            # Save previous entry if it has a name
            if current and current.name:
                alternatives.append(current)
            current = AlternativeItem()
            section = ""
            continue

        if current is None:
            continue

        # ── Section header: #### Cost / License
        if stripped.startswith("####") and "cost" in stripped.lower() or "license" in stripped.lower():
            if stripped.startswith("####"):
                section = "license"
                continue

        # ── Section header: #### Platforms
        if stripped.startswith("####") and "platform" in stripped.lower():
            section = "platforms"
            continue

        # ── Section header: anything else with ####
        if stripped.startswith("####"):
            # Could be "##### Element vs Slack Comments" etc.
            if "comments" in stripped.lower() or "vs" in stripped.lower():
                section = "comparison"
            else:
                section = "other"
            continue

        # ── Extract name: Is**ProductName**a good alternative to {product}?
        name_match = re.match(r'^Is\*\*(.+?)\*\*\s*a good alternative', stripped)
        if name_match:
            current.name = name_match.group(1).strip()
            # Build URL from name
            slug = current.name.lower().strip().replace(" ", "-").replace(".", "-")
            current.url = f"https://alternativeto.net/software/{slug}/"
            section = "post_name"
            continue

        # ── Extract comment count: "13 comments" or "77 comments"
        comment_match = re.match(r'^(\d+)\s+comments?$', stripped)
        if comment_match:
            current.comments_count = int(comment_match.group(1))
            continue

        # ── License items: *   Free Personal / *   Open Source([MIT](...))
        if section == "license" and stripped.startswith("*"):
            item = stripped.lstrip("*").strip()
            # Clean markdown links from license
            item = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', item)
            item = re.sub(r'\(.*?\)', '', item).strip()
            if item:
                if current.license_model:
                    current.license_model += " • " + item
                else:
                    current.license_model = item

        # ── Platform items: *   Mac / *   Windows / etc.
        elif section == "platforms" and stripped.startswith("*"):
            platform = stripped.lstrip("*").strip()
            if platform and len(platform) < 40:
                current.platforms.append(platform)

        # ── Comparison notes: *   Element is**Free**and**Open Source**...
        elif stripped.startswith("*") and "is**" in stripped:
            note = stripped.lstrip("*").strip()
            # Clean up bold markers and fix spacing
            note = note.replace("**", "")
            # Fix missing spaces around "is", "and", "also" caused by bold removal
            note = re.sub(r'(\w)(is|and|also|not)(\w)', r'\1 \2 \3', note)
            note = re.sub(r'\s+', ' ', note).strip()
            current.comparison_notes.append(note)

        # ── Skip image lines, empty lines, etc.

    # Don't forget the last entry
    if current and current.name:
        alternatives.append(current)

    return alternatives


def parse_category_from_jina_markdown(markdown: str) -> list[dict]:
    """
    Parse category page for product listings with rich data.

    Category page format (via Jina):
        [LibreOffice -----------](url)
        3124 likes
        Free and open-source office suite...
        * [Word Processor](...)
        * Free
        * Open Source([GPL-3.0](...))
        * Mac
        * Windows
        ...
    """
    products = []
    lines = markdown.split("\n")
    seen = set()

    current: dict | None = None
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        # ── Product link: [Name ---...](url)
        link_match = re.match(
            r'\[([^\]]+?)(?:\s*-+)?\]\((?:https://alternativeto\.net)?/software/([^/]+)/(?:about/)?\s*(?:"[^"]*")?\)',
            stripped,
        )
        if link_match:
            name = link_match.group(1).strip().rstrip("-").strip()
            slug = link_match.group(2)

            if name in seen or len(name) < 2:
                i += 1
                continue

            # Save previous
            if current and current.get("name"):
                products.append(current)

            seen.add(name)
            current = {
                "name": name,
                "slug": slug,
                "url": f"https://alternativeto.net/software/{slug}/",
                "description": "",
                "likes": 0,
                "license": "",
                "platforms": [],
                "category": "",
            }
            i += 1
            continue

        if current is None:
            i += 1
            continue

        # ── Likes: "3124 likes"
        likes_match = re.match(r'^(\d[\d,]*)\s+likes?$', stripped)
        if likes_match and current:
            current["likes"] = int(likes_match.group(1).replace(",", ""))
            i += 1
            continue

        # ── Description: plain text lines (not starting with *, not images, not links)
        if (
            not current.get("description")
            and stripped
            and not stripped.startswith("*")
            and not stripped.startswith("![")
            and not stripped.startswith("[")
            and not stripped.startswith("#")
            and "likes" not in stripped
            and len(stripped) > 30
        ):
            current["description"] = stripped[:300]
            i += 1
            continue

        # ── List items: * Category, License, Platform info
        if stripped.startswith("*") and current:
            item = stripped.lstrip("*").strip()
            # Clean markdown links
            clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', item)
            clean = re.sub(r'\(.*?\)', '', clean).strip()

            if not clean:
                i += 1
                continue

            # Categorize the item
            if clean in ("Free", "Freemium", "Paid", "Free Personal"):
                current["license"] = clean
            elif "Open Source" in clean:
                lic = current.get("license", "")
                current["license"] = f"{lic} • Open Source".lstrip(" •") if lic else "Open Source"
            elif "Proprietary" in clean:
                lic = current.get("license", "")
                current["license"] = f"{lic} • Proprietary".lstrip(" •") if lic else "Proprietary"
            elif any(cat in clean for cat in [
                "Tool", "Client", "Manager", "Editor", "Processor", "Software",
                "Service", "Platform", "App", "System", "Suite",
            ]):
                current["category"] = clean
            elif clean in (
                "Mac", "Windows", "Linux", "Online", "Android", "iPhone", "iPad",
                "BSD", "Chrome OS", "Self-Hosted",
            ) or len(clean) < 30:
                current["platforms"].append(clean)

        i += 1

    # Last entry
    if current and current.get("name"):
        products.append(current)

    return products


# ─────────────────────────────────────────────────────────────────────────────
# Cache Format Mappers
# ─────────────────────────────────────────────────────────────────────────────


def to_current_schema(product_name: str, alts: list[AlternativeItem], source_url: str) -> dict:
    """Current PLAN.md schema: name, description, platforms."""
    return {
        "product_name": product_name,
        "normalized_name": " ".join(product_name.lower().strip().split()),
        "alternatives": [
            {"name": a.name, "description": a.description or "; ".join(a.comparison_notes), "platforms": a.platforms}
            for a in alts
        ],
        "source_url": source_url,
    }


def to_enhanced_schema(product_name: str, alts: list[AlternativeItem], source_url: str) -> dict:
    """Proposed enhanced schema with richer data."""
    return {
        "product_name": product_name,
        "normalized_name": " ".join(product_name.lower().strip().split()),
        "alternatives": [
            {
                "name": a.name,
                "description": "; ".join(a.comparison_notes) if a.comparison_notes else "",
                "platforms": a.platforms,
                "license": a.license_model,
                "comments": a.comments_count,
                "url": a.url,
                "source": "alternativeto",
            }
            for a in alts
        ],
        "source_url": source_url,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

TEST_PRODUCTS = ["Slack", "Figma", "Notion"]
TEST_CATEGORIES = ["productivity"]


async def main():
    print("=" * 80)
    print("  AlternativeTo — Dry Run Scraper (Jina Reader)")
    print("=" * 80)
    print(f"  Jina API key: {'...' + JINA_API_KEY[-6:] if JINA_API_KEY else '(free tier)'}")
    print()

    async with httpx.AsyncClient() as client:

        # ══════════════════════════════════════════════════════════════════════
        #  PART 1: Product Alternatives
        # ══════════════════════════════════════════════════════════════════════
        print("─" * 80)
        print("  PART 1: Scraping product alternatives")
        print("─" * 80)

        all_results: list[tuple[str, list[AlternativeItem], str]] = []

        for product in TEST_PRODUCTS:
            slug = product.lower().replace(" ", "-")
            url = f"https://alternativeto.net/software/{slug}/"
            print(f"\n▸ {product} → {url}")

            start = time.monotonic()
            try:
                markdown = await fetch_via_jina(client, url)
                ms = int((time.monotonic() - start) * 1000)

                # Check for CAPTCHA/block
                if "security verification" in markdown.lower() or "captcha" in markdown.lower():
                    print(f"  ✗ CAPTCHA/blocked ({ms}ms, {len(markdown)} chars)")
                    print(f"  → Jina got a Cloudflare challenge page.")
                    await asyncio.sleep(5)
                    continue

                print(f"  ✓ Fetched {len(markdown)} chars ({ms}ms)")

                # Save raw for inspection
                with open(f"/tmp/alt_{product.lower()}_raw.md", "w") as f:
                    f.write(markdown)

                # Parse
                alts = parse_alternatives_from_jina_markdown(markdown, product)
                print(f"  🔍 Parsed {len(alts)} alternatives\n")

                all_results.append((product, alts, url))

                # Show all parsed alternatives
                for i, alt in enumerate(alts):
                    print(f"  [{i+1:>2}] {alt.name}")
                    if alt.license_model:
                        print(f"       License: {alt.license_model}")
                    if alt.platforms:
                        plats = ", ".join(alt.platforms[:8])
                        extra = f" +{len(alt.platforms)-8}" if len(alt.platforms) > 8 else ""
                        print(f"       Platforms: {plats}{extra}")
                    if alt.comments_count:
                        print(f"       Comments: {alt.comments_count}")
                    if alt.comparison_notes:
                        for note in alt.comparison_notes[:2]:
                            print(f"       → {note[:100]}")
                    print()

            except Exception as e:
                ms = int((time.monotonic() - start) * 1000)
                print(f"  ✗ Error: {e} ({ms}ms)")

            print("  ⏳ Rate limit pause (4s)...")
            await asyncio.sleep(4)

        # ══════════════════════════════════════════════════════════════════════
        #  PART 2: Category Pages
        # ══════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 80)
        print("  PART 2: Category page scraping (for bulk seeding)")
        print("─" * 80)

        for category in TEST_CATEGORIES:
            cat_url = f"https://alternativeto.net/category/{category}/"
            print(f"\n▸ Category: {category}")

            start = time.monotonic()
            try:
                markdown = await fetch_via_jina(client, cat_url)
                ms = int((time.monotonic() - start) * 1000)

                if "security verification" in markdown.lower():
                    print(f"  ✗ CAPTCHA/blocked ({ms}ms)")
                    continue

                print(f"  ✓ Fetched {len(markdown)} chars ({ms}ms)")

                with open(f"/tmp/alt_cat_{category}_raw.md", "w") as f:
                    f.write(markdown)

                products = parse_category_from_jina_markdown(markdown)
                print(f"  🔍 Found {len(products)} products\n")
                for j, p in enumerate(products[:15]):
                    desc = p.get('description', '')[:60]
                    likes = p.get('likes', 0)
                    lic = p.get('license', '')
                    plats = ", ".join(p.get('platforms', [])[:4])
                    cat = p.get('category', '')
                    print(f"    [{j+1:>2}] {p['name']} ({p['slug']})")
                    if likes: print(f"         👍 {likes} likes")
                    if desc: print(f"         📝 {desc}...")
                    if lic: print(f"         📜 {lic}")
                    if cat: print(f"         📂 {cat}")
                    if plats: print(f"         💻 {plats}")
                    print()
                if len(products) > 15:
                    print(f"    ... +{len(products) - 15} more products")

            except Exception as e:
                ms = int((time.monotonic() - start) * 1000)
                print(f"  ✗ Error: {e} ({ms}ms)")

        # ══════════════════════════════════════════════════════════════════════
        #  PART 3: Storage Format Demo
        # ══════════════════════════════════════════════════════════════════════
        print("\n" + "─" * 80)
        print("  PART 3: How this data maps to the DB")
        print("─" * 80)

        for product, alts, src_url in all_results:
            if not alts:
                continue

            print(f"\n  ── {product}: {len(alts)} alternatives ──\n")

            # Current schema
            current = to_current_schema(product, alts, src_url)
            print(f"  CURRENT schema (PLAN.md):")
            print(f"  alternatives_cache.alternatives JSONB shape:")
            print(f'  {json.dumps(current["alternatives"][0], indent=4)}')

            # Enhanced schema
            enhanced = to_enhanced_schema(product, alts, src_url)
            print(f"\n  PROPOSED ENHANCED schema:")
            print(f"  alternatives_cache.alternatives JSONB shape:")
            print(f'  {json.dumps(enhanced["alternatives"][0], indent=4)}')

            # Size
            cur_bytes = len(json.dumps(current["alternatives"]))
            enh_bytes = len(json.dumps(enhanced["alternatives"]))
            print(f"\n  JSONB size for {len(alts)} alternatives:")
            print(f"    Current:  {cur_bytes:>6,} bytes")
            print(f"    Enhanced: {enh_bytes:>6,} bytes (+{enh_bytes - cur_bytes:,})")

        # ══════════════════════════════════════════════════════════════════════
        #  Summary
        # ══════════════════════════════════════════════════════════════════════
        print("\n" + "=" * 80)
        print("  EXTRACTION RESULTS SUMMARY")
        print("=" * 80)

        for product, alts, url in all_results:
            n = max(len(alts), 1)
            has = lambda f: sum(1 for a in alts if f(a))

            print(f"\n  {product}: {len(alts)} alternatives extracted")
            print(f"  ┌────────────────────┬────────┬────────┐")
            print(f"  │ Field              │ Found  │ Rate   │")
            print(f"  ├────────────────────┼────────┼────────┤")
            print(f"  │ name               │ {len(alts):>4}/{len(alts):<2} │ {'100%':>6} │")
            print(f"  │ license            │ {has(lambda a: a.license_model):>4}/{len(alts):<2} │ {has(lambda a: a.license_model)/n*100:>5.0f}% │")
            print(f"  │ platforms          │ {has(lambda a: a.platforms):>4}/{len(alts):<2} │ {has(lambda a: a.platforms)/n*100:>5.0f}% │")
            print(f"  │ comments_count     │ {has(lambda a: a.comments_count > 0):>4}/{len(alts):<2} │ {has(lambda a: a.comments_count > 0)/n*100:>5.0f}% │")
            print(f"  │ comparison_notes   │ {has(lambda a: a.comparison_notes):>4}/{len(alts):<2} │ {has(lambda a: a.comparison_notes)/n*100:>5.0f}% │")
            print(f"  │ url                │ {has(lambda a: a.url):>4}/{len(alts):<2} │ {has(lambda a: a.url)/n*100:>5.0f}% │")
            print(f"  └────────────────────┴────────┴────────┘")

        if not any(alts for _, alts, _ in all_results):
            print("\n  ⚠️  No alternatives were extracted.")
            print("  Likely cause: Cloudflare CAPTCHA blocking Jina on some pages.")
            print("  The Slack page worked earlier — this is intermittent.")
            print("  For production, we should:")
            print("    1. Retry with exponential backoff")
            print("    2. Use Jina with API key for higher priority")
            print("    3. Consider SaaSHub as supplementary source (less aggressive blocking)")

        print()


if __name__ == "__main__":
    asyncio.run(main())
