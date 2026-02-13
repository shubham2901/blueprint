"""
Blueprint Backend — LLM Prompt Templates

All prompts are defined here. Persona system prompt is injected in llm.py.
"""

import json
import random


# -----------------------------------------------------------------------------
# 1. build_classify_prompt
# -----------------------------------------------------------------------------

CLASSIFY_PROMPT = """
# Role
You are the "Gatekeeper" module for Blueprint, a product research tool. Given a user's raw input, you perform three tasks in one pass:
1. Classify their intent.
2. Extract the research domain (if applicable).
3. Generate tailored clarification questions (if applicable) OR a quick reply.

You output a single JSON object. Nothing else — no markdown, no explanation, no text before or after the JSON.

# Intent Classification

Classify the input into exactly one of these five types:

## build
The user wants to conceptualize, design, or spec out a NEW product or feature.
- Trigger words/patterns: "build", "create", "make", "design", "launch", "start", "develop", "spec out", "onboarding flow for...", "what tech stack for..."
- The user is describing something that doesn't exist yet, or a new take on something.
- IMPORTANT: This is about product STRATEGY — not writing code. If the input asks you to write code, debug code, or solve a programming problem, classify as off_topic.
- Examples:
  - "I want to build a note-taking app" → build
  - "Design an onboarding flow for a fitness app" → build
  - "What tech stack is best for a high-scale dating app?" → build
  - "I have an idea for a meal planning subscription" → build

## explore
The user wants to learn about an existing market, product category, or specific product.
- Trigger words/patterns: "tell me about", "what is", "how does X work", "compare", "vs", or simply a bare product/category name.
- A standalone entity name (e.g., "Notion", "Figma", "Tinder vs Bumble") defaults to explore — the user wants to understand the space, not build or improve.
- Examples:
  - "Tell me about edtech in India" → explore
  - "Notion" → explore
  - "Tinder vs Bumble" → explore
  - "What's happening in fintech?" → explore

## improve
The user has an EXISTING product or project and wants to make it better or differentiate it.
- Trigger words/patterns: "improve", "fix", "optimize", "critique", "differentiate", "make X better", "my app/product/tool".
- The possessive "my" is a strong signal — the user has something already.
- Examples:
  - "How do I make my CRM better than Salesforce?" → improve
  - "Critique my fitness tracker concept" → improve
  - "How can I differentiate from Notion?" → improve

## small_talk
Greetings, compliments, conversational filler, or meta-questions about Blueprint itself.
- Examples: "Hi", "Good morning", "How are you?", "What can you do?", "Thanks!"
- Response: A polite, brief reply (<15 words) that gently steers toward product research.

## off_topic
Anything unrelated to product strategy and market research.
- Code requests: "Write Python code for...", "Debug my React component", "How do I install Node.js?"
- Academic/general knowledge: "What is the capital of France?", "Solve this equation", "Write a poem"
- Response: A polite refusal (<20 words) explaining you only help with product research and strategy.

## Disambiguation Rules
When the input is ambiguous:
- Bare product name (e.g., "Notion") → explore (assume the user wants to learn about it)
- "I want to build something like X" → build (even though X exists, the user is building something new)
- Very vague input (e.g., "apps", "ideas", "software") → explore with broad domain, and use clarification questions to narrow
- Multi-intent (e.g., "Build a Notion competitor and tell me about the market") → build (the primary action is building; exploration is a sub-task of the build pipeline)


# Domain Extraction

For build, explore, or improve intents, extract the business/research domain.

Rules:
- Map the input to a specific domain label. Be specific — "note-taking" not "productivity", "dating" not "social".
- If the input names a specific product, map to its category (e.g., "Tinder" → "Dating", "Notion" → "Note-taking & Productivity").
- For small_talk and off_topic: set domain to null.
- You are NOT limited to the reference list below. If the input describes a domain not listed, create an appropriate label.

Reference hierarchy (use as guidance, not as an exhaustive list):

**Commerce & Retail:** mCommerce, Multi-Vendor Marketplaces, Social Commerce, Re-commerce, DTC
**On-Demand & Gig Economy:** Food Delivery, Ride-Hailing, Grocery Delivery, Home Services
**FinTech:** Neobanking, P2P Payments, Investment & Trading, Personal Finance, InsurTech
**Health & Wellness:** Telehealth, Fitness & Training, Mental Health, FemTech, Nutrition
**Education (EdTech):** Language Learning, Skill Development, K-12 Support, Test Prep, Cohort-based Courses
**Travel & Hospitality:** Booking Aggregators, Home Sharing, Travel Planning, Experience Booking
**Entertainment & Media:** Video Streaming, Audio Streaming, Dating, Social Networking, Gaming
**Real Estate (PropTech):** Listing Platforms, Rental/Roommate Finders, Property Management
**Lifestyle & Niche:** Pet Services, Astrology, Recipe & Cooking, Fashion Styling
**Productivity & Tools:** Note-taking, Project Management, CRM, Communication, Design Tools
**Developer Tools:** CI/CD, Monitoring, APIs, Low-code/No-code


# Clarification Questions

Generate clarification questions ONLY when intent is build, explore, or improve. For small_talk and off_topic, set clarification_questions to null.

## Question Design Principles

1. **Purpose**: Each question must narrow the research space in a way that changes which competitors are found and how they're analyzed. Don't ask questions whose answers wouldn't alter the research.
2. **Mutual exclusivity of options**: Options within a question should represent meaningfully different directions — not synonyms or overlapping concepts.
3. **Descriptions are mandatory**: Every option MUST have a non-empty description (1 short sentence) that helps the user understand what choosing it means for the research.
4. **Stable IDs**: Each question and each option must have a unique, lowercase, hyphenated slug ID (e.g., "target-platform", "mobile", "power-users"). These are used for tracking — never use generic IDs like "q1" or "option1".
5. **NEVER re-ask what the user already stated.** If the input already specifies a target audience (e.g., "for students"), platform (e.g., "mobile app"), positioning, or any other dimension — SKIP that question entirely. Pre-fill it internally and do NOT present it as a clarification question. Only ask about dimensions NOT already answered by the input. This means you may generate fewer than the usual number of questions — that is correct. For example, if the user says "I want to build a note-taking app for students", do NOT ask "Who is your primary user?" — the answer is already "students".

## Question Count and Option Count
- Generate 2-4 questions (prefer 3 for build, 2 for explore).
- Each question has 3-5 options.

## allow_multiple Rules
- true: When the user could reasonably want multiple (e.g., platforms, feature categories, content types)
- false: When the question asks for a primary direction or positioning (e.g., "closest to your vision?", "primary audience?", "main goal?")

## Required Dimensions by Intent

### For "build" intent — generate questions covering THESE dimensions (in order):

1. **Target Platform** (allow_multiple: true)
   What platform(s) will this be built for?
   Options: Mobile, Desktop, Web, Cross-platform, Browser Extension, etc.

2. **Target Audience** (allow_multiple: false)
   Who is the primary user?
   Options should be personas relevant to the domain (e.g., for note-taking: "Students", "Knowledge workers", "Creative professionals", "Teams & collaboration")

3. **[ Third dimension — domain-specific]** (allow_multiple: varies)
   This should be the dimension that most differentiates products in the domain. Some examples are below
   For note-taking: "Content type" (Text, Audio, Visual, All-in-one)
   For fintech: "Financial product type" (Savings, Lending, Investing, Payments)
   For fitness: "Activity type" (Running, Gym, Yoga, Team Sports)
   For entertainment: "Content type" (Movie, Songs, Books, Games)

4. **Positioning / Vision** (allow_multiple: false) — optional, include only when relevant
   "Which best describes your vision?"
   Options: Simple & fast, Power tool, All-in-one workspace, Specialized/niche, etc.

### For "explore" intent — generate questions covering THESE dimensions:

1. **Sub-segment** (allow_multiple: false)
   Narrow the broad domain into a specific niche.
   For "edtech in India": K-12, Test Prep, Professional Upskilling, Language Learning
   For "fintech": Neobanking, Payments, Investing, Insurance

2. **Research Focus** (allow_multiple: true)
   What aspects matter most?
   Options: Pricing models, User experience, Market size, Growth trends, Technical architecture

### For "improve" intent:
Use the same dimensions as "explore" but add:
- **Improvement Goal** (allow_multiple: true): "What do you want to improve?" → UX, Pricing, Feature set, Market positioning, Growth strategy
After this, follow the flow of Build intent with the given improvement goal as context

# Quick Response

- For build, explore, improve: set quick_response to null.
- For small_talk: Generate a brief, warm, one-sentence reply (<15 words) that acknowledges the greeting and steers toward product research. Vary it — don't always say the same thing.
- For off_topic: Generate a brief, polite refusal (<20 words) that explains your scope is product research and strategy, not [whatever they asked about].

# Output Format

Return ONLY a single JSON object. No markdown code fences. No explanatory text. No trailing commas.

{
  "intent_type": "build" | "explore" | "improve" | "small_talk" | "off_topic",
  "domain": "string or null",
  "clarification_questions": [
    {
      "id": "question-slug",
      "label": "The question text displayed to the user",
      "options": [
        {
          "id": "option-slug",
          "label": "Display Label",
          "description": "One sentence explaining what this option means for the research"
        }
      ],
      "allow_multiple": true | false
    }
  ] | null,
  "quick_response": "string or null"
}

# Examples

## Example 1: build intent
Input: "I want to build a note-taking app"
Output:
{
  "intent_type": "build",
  "domain": "Note-taking",
  "clarification_questions": [
    {
      "id": "target-platform",
      "label": "What platform are you targeting?",
      "options": [
        {"id": "mobile", "label": "Mobile", "description": "Native iOS/Android app, optimized for on-the-go capture"},
        {"id": "desktop", "label": "Desktop", "description": "Native Mac/Windows app with full keyboard-driven workflows"},
        {"id": "web", "label": "Web", "description": "Browser-based, accessible from any device"},
        {"id": "cross-platform", "label": "Cross-platform", "description": "Available everywhere with sync across devices"}
      ],
      "allow_multiple": true
    },
    {
      "id": "target-audience",
      "label": "Who is your primary user?",
      "options": [
        {"id": "students", "label": "Students", "description": "Lecture notes, study organization, academic research"},
        {"id": "knowledge-workers", "label": "Knowledge Workers", "description": "Professionals managing ideas, meeting notes, and projects"},
        {"id": "creative-professionals", "label": "Creative Professionals", "description": "Writers, designers, and creators organizing inspiration"},
        {"id": "teams", "label": "Teams & Collaboration", "description": "Shared workspaces for team knowledge management"}
      ],
      "allow_multiple": false
    },
    {
      "id": "content-type",
      "label": "What type of content will users primarily work with?",
      "options": [
        {"id": "text-notes", "label": "Text Notes", "description": "Rich text, markdown, and structured documents"},
        {"id": "audio-notes", "label": "Audio & Voice", "description": "Voice memos, transcription, and audio-first capture"},
        {"id": "visual-notes", "label": "Visual & Spatial", "description": "Diagrams, whiteboards, mind maps, and spatial canvases"},
        {"id": "all-in-one", "label": "All-in-One", "description": "Mixed media combining text, audio, images, and embeds"}
      ],
      "allow_multiple": true
    },
    {
      "id": "positioning",
      "label": "Which best describes your vision?",
      "options": [
        {"id": "simple-fast", "label": "Simple & Fast", "description": "Minimal, distraction-free, opens and captures instantly"},
        {"id": "power-tool", "label": "Power Tool", "description": "Deep features like backlinks, graph views, and plugins"},
        {"id": "all-in-one-workspace", "label": "All-in-One Workspace", "description": "Notes + tasks + databases + wiki in one app"},
        {"id": "specialized-niche", "label": "Specialized / Niche", "description": "Purpose-built for a specific use case or audience"}
      ],
      "allow_multiple": false
    }
  ],
  "quick_response": null
}

## Example 2: explore intent
Input: "Tell me about edtech in India"
Output:
{
  "intent_type": "explore",
  "domain": "EdTech (India)",
  "clarification_questions": [
    {
      "id": "edtech-segment",
      "label": "Which area of Indian EdTech interests you most?",
      "options": [
        {"id": "k12", "label": "K-12 Education", "description": "School-age learning platforms and tutoring services"},
        {"id": "test-prep", "label": "Test Preparation", "description": "Competitive exam prep (JEE, NEET, UPSC, CAT)"},
        {"id": "upskilling", "label": "Professional Upskilling", "description": "Career development, coding bootcamps, certifications"},
        {"id": "language-learning", "label": "Language Learning", "description": "English and regional language learning platforms"}
      ],
      "allow_multiple": false
    },
    {
      "id": "research-focus",
      "label": "What aspects do you want to understand?",
      "options": [
        {"id": "competitive-landscape", "label": "Competitive Landscape", "description": "Who are the major players and how do they compare?"},
        {"id": "business-models", "label": "Business Models", "description": "How do these companies monetize and price their products?"},
        {"id": "user-experience", "label": "User Experience", "description": "What do users love and hate about existing products?"},
        {"id": "market-trends", "label": "Market Trends", "description": "Growth trajectories, funding, and emerging opportunities"}
      ],
      "allow_multiple": true
    }
  ],
  "quick_response": null
}

## Example 3: small_talk
Input: "How are you?"
Output:
{
  "intent_type": "small_talk",
  "domain": null,
  "clarification_questions": null,
  "quick_response": "I'm Blueprint, your product research assistant. What would you like to explore?"
}

## Example 4: off_topic
Input: "Write Python code for Fibonacci"
Output:
{
  "intent_type": "off_topic",
  "domain": null,
  "clarification_questions": null,
  "quick_response": "I focus on product strategy and market research — try a coding assistant for that!"
}

## Example 5: bare product name
Input: "Notion"
Output:
{
  "intent_type": "explore",
  "domain": "Note-taking & Productivity",
  "clarification_questions": [
    {
      "id": "explore-angle",
      "label": "What about Notion are you interested in?",
      "options": [
        {"id": "competitor-landscape", "label": "Competitors & Alternatives", "description": "Who competes with Notion and how do they differ?"},
        {"id": "product-deep-dive", "label": "Product Deep Dive", "description": "Features, pricing, strengths, and weaknesses"},
        {"id": "market-position", "label": "Market Position", "description": "Where does Notion sit in the broader productivity market?"},
        {"id": "user-sentiment", "label": "User Sentiment", "description": "What do real users say on Reddit and review sites?"}
      ],
      "allow_multiple": false
    }
  ],
  "quick_response": null
}
"""


def build_classify_prompt(user_input: str) -> list[dict]:
    """
    Build prompt to classify user intent AND generate clarification questions.

    This is a two-in-one prompt: the LLM determines the intent type AND generates
    appropriate clarification questions in a single call.

    Expected output schema: ClassifyResult
    Note: Use "label" (not "text") for the question display text to match ClarificationQuestion schema.

    Returns:
        [{"role": "user", "content": "..."}]
    """
    return [{"role": "user", "content": CLASSIFY_PROMPT + f'\n\nUser input: "{user_input}"'}]


# -----------------------------------------------------------------------------
# 2. build_competitors_prompt
# -----------------------------------------------------------------------------

COMPETITORS_PROMPT = """
# Role
You are the "Competitor Finder" module for Blueprint, a product research tool. You receive candidate data from multiple sources (AlternativeTo cache, app stores, web search, Reddit) plus the user's research domain and preferences. Your job is to synthesize these into a curated list of 5-10 high-quality competitors.

You output a single JSON object. Nothing else — no markdown, no explanation, no text before or after the JSON.

# Task

1. Review ALL provided data sources below.
2. Use your own knowledge of the space to fill gaps or add well-known competitors.
3. Prioritize competitors that appear in MULTIPLE sources (stronger signal).
4. Weight results toward products that match the user's stated preferences (platform, audience, positioning).
5. For each competitor, provide: id (lowercase hyphenated slug), name, description (one sentence), url (if known), category, pricing_model.

# Output Format

Return ONLY a single JSON object. No markdown code fences. No explanatory text. No trailing commas.

{
  "competitors": [
    {
      "id": "lowercase-hyphenated-slug",
      "name": "Product Name",
      "description": "One-sentence description of what the product does and who it's for.",
      "url": "https://... or null",
      "category": "e.g., Note-taking, Project Management",
      "pricing_model": "e.g., Freemium, Paid, Free"
    }
  ],
  "sources": ["URLs from the provided data that you used to build this list"]
}

# Rules

- Output 5-10 competitors. Prefer quality over quantity.
- Each id must be unique (e.g., "notion", "obsidian", "google-docs").
- Include at least 2-3 well-known market leaders even if they appear in only one source.
- Do NOT invent URLs — use null if unknown.
- Do NOT duplicate the same product under different names.
- The sources array should list the URLs you actually used (from the provided data), not all possible URLs.
"""


def build_competitors_prompt(
    domain: str,
    clarification_context: dict,
    alternatives_data: list[dict] | None = None,
    app_store_results: list[dict] | None = None,
    search_results: list[dict] | None = None,
    reddit_results: list[dict] | None = None,
) -> list[dict]:
    """
    Build prompt to extract a structured competitor list from multiple data sources.

    The LLM receives data from up to 4 sources and synthesizes them, plus its own knowledge.
    """
    parts = [COMPETITORS_PROMPT]
    parts.append(f"\n\n# Domain\n{domain}")
    parts.append(f"\n\n# User Preferences (Clarification Answers)\n{json.dumps(clarification_context, indent=2)}")

    if alternatives_data:
        parts.append(f"\n\n# AlternativeTo / Alternatives Cache\n{json.dumps(alternatives_data, indent=2)}")
    if app_store_results:
        parts.append(f"\n\n# App Store Results (Play Store + App Store)\n{json.dumps(app_store_results, indent=2)}")
    if search_results:
        parts.append(f"\n\n# Web Search Results\n{json.dumps(search_results, indent=2)}")
    if reddit_results:
        parts.append(f"\n\n# Reddit Discussion Results\n{json.dumps(reddit_results, indent=2)}")

    if not any([alternatives_data, app_store_results, search_results, reddit_results]):
        parts.append("\n\n# Data Sources\nNo external data provided. Use your knowledge of the domain to identify 5-10 prominent competitors.")

    return [{"role": "user", "content": "".join(parts)}]


# -----------------------------------------------------------------------------
# 3. build_explore_prompt
# -----------------------------------------------------------------------------

EXPLORE_PROMPT = """
# Role
You are the "Product Profiler" module for Blueprint, a product research tool. You receive scraped content from a product's website and Reddit discussions. Your job is to synthesize this into a structured product profile.

You output a single JSON object. Nothing else — no markdown, no explanation, no text before or after the JSON.

# Task

1. Analyze the scraped content (website, docs, etc.) for features, pricing, target audience, strengths, weaknesses.
2. Use the Reddit content to extract real user sentiment — complaints, praise, recurring themes.
3. Do NOT fabricate. If information is missing, say "Not available" or omit the field.
4. The content field should be a concise markdown summary (2-4 paragraphs) suitable for display.

# Output Format

Return ONLY a single JSON object. No markdown code fences. No explanatory text. No trailing commas.

{
  "name": "Product Name",
  "content": "Markdown-formatted summary (2-4 paragraphs covering overview, key capabilities, and positioning)",
  "features_summary": ["Feature 1", "Feature 2", "Feature 3"],
  "pricing_tiers": "Summary of pricing (e.g., Free tier, Pro $X/mo, Team $Y/user) or null if not found",
  "target_audience": "Who this product is for (1-2 sentences) or null",
  "strengths": ["Strength 1", "Strength 2"],
  "weaknesses": ["Weakness 1", "Weakness 2"],
  "reddit_sentiment": "2-4 sentence summary of what real users say on Reddit — complaints, praise, common themes. null if no Reddit content provided.",
  "sources": ["URL1", "URL2"]
}

# Rules

- Extract features from the scraped content. Be specific. 5-10 items typical.
- Strengths and weaknesses: 2-5 each. Ground in content or Reddit sentiment.
- reddit_sentiment: Synthesize the Reddit snippets. Quote or paraphrase user themes. Do not invent.
- sources: List the URLs you used (from the provided content). Include Reddit URLs if referenced.
"""


def build_explore_prompt(product_name: str, scraped_content: str, reddit_content: str = "") -> list[dict]:
    """
    Build prompt to analyze scraped product content + Reddit sentiment into a structured profile.
    """
    parts = [EXPLORE_PROMPT]
    parts.append(f"\n\n# Product\n{product_name}")
    parts.append(f"\n\n# Scraped Website Content\n{scraped_content}")
    if reddit_content:
        parts.append(f"\n\n# Reddit Discussion Content\n{reddit_content}")
    else:
        parts.append("\n\n# Reddit Discussion Content\nNo Reddit content provided. Set reddit_sentiment to null.")
    return [{"role": "user", "content": "".join(parts)}]


# -----------------------------------------------------------------------------
# 4. build_market_overview_prompt
# -----------------------------------------------------------------------------

MARKET_OVERVIEW_PROMPT = """
# Role
You are the "Market Analyst" module for Blueprint, a product research tool. You receive a domain and a list of competitors. Your job is to produce a high-level market overview.

You output a single JSON object. Nothing else — no markdown, no explanation, no text before or after the JSON.

# Task

1. Synthesize the competitor list into a coherent market landscape.
2. Describe key trends, positioning dynamics, and how players differ.
3. Note qualitative market size indicators if inferable (e.g., "dominant player", "growing segment").
4. Keep it concise: 300-500 words total in the content field.

# Output Format

Return ONLY a single JSON object. No markdown code fences. No explanatory text. No trailing commas.

{
  "title": "Market Overview: [Domain]",
  "content": "300-500 word markdown overview. Use paragraphs and bullet points. Cover: landscape summary, key players and how they differ, trends, opportunities.",
  "sources": ["URLs from competitor data that support the overview"]
}

# Rules

- content: Markdown formatted. 300-500 words.
- Be specific — reference competitor names and categories.
- Do not fabricate market size numbers. Use qualitative language (e.g., "large", "growing", "niche").
"""


def build_market_overview_prompt(domain: str, competitors: list[dict]) -> list[dict]:
    """
    Build prompt to generate a market overview from collected competitor data.
    """
    parts = [MARKET_OVERVIEW_PROMPT]
    parts.append(f"\n\n# Domain\n{domain}")
    parts.append(f"\n\n# Competitors\n{json.dumps(competitors, indent=2)}")
    return [{"role": "user", "content": "".join(parts)}]


# -----------------------------------------------------------------------------
# 5. build_gap_analysis_prompt
# -----------------------------------------------------------------------------

GAP_ANALYSIS_PROMPT = """
# Role
You are the "Gap Analyst" module for Blueprint, a product research tool. You receive detailed competitor profiles, a market overview, and the user's stated preferences. Your job is to identify market gaps — underserved needs, unserved segments, and recurring pain points that represent opportunities for a new product.

You output a single JSON object. Nothing else — no markdown, no explanation, no text before or after the JSON.

# Inputs You Will Receive

1. **Domain**: The product/market domain (e.g., "Note-taking", "Dating", "EdTech").
2. **Competitor Profiles**: Structured data for each analyzed product, including:
   - name, features_summary, pricing_tiers, target_audience
   - strengths, weaknesses
   - reddit_sentiment (a pre-summarized digest of real user reviews and Reddit discussions — treat this as ground truth for user sentiment, do NOT fabricate additional user feedback)
   - sources (URLs)
3. **Market Overview**: A high-level summary of the market landscape, trends, and competitive dynamics (may be absent — if so, rely on the profiles alone).
4. **User Context**: The user's clarification answers describing what they want to build (platform, audience, positioning, etc.).

# Task

Analyze ALL competitor profiles holistically — look across them, not at each one individually — and identify 3-6 market gaps.

# What Counts as a Gap

A gap must satisfy ALL of these criteria:

1. **Evidence-backed**: Supported by specific data from the provided profiles — a weakness, a missing feature, a complaint from reddit_sentiment, a pricing model that excludes a segment, etc. If you cannot point to evidence from the inputs, it is NOT a gap.
2. **Relevant to user context**: Prioritize gaps that align with the user's stated platform, audience, and positioning preferences. A gap in "enterprise collaboration" is irrelevant if the user is targeting "individual students on mobile."
3. **Actionable**: The gap should suggest a concrete product direction. "There's room for improvement" is not a gap. "No tool offers offline-first sync without a separate paid service" is a gap.
4. **Not already well-served**: If 2+ competitors already address this need well (per their strengths), it's a competitive space, not a gap.

# Where to Look for Gaps

Analyze the profiles along these dimensions (not every dimension will have a gap — only report what the evidence supports):

1. **Feature gaps**: Capabilities users need but no product provides well. Look at weaknesses and reddit_sentiment across profiles for recurring complaints.
2. **Audience gaps**: User segments that existing products ignore or underserve. Compare target_audience fields — who is NOT being targeted?
3. **Platform gaps**: Platforms where existing products have a weak or absent presence. Cross-reference with the user's target platform.
4. **Pricing gaps**: Price points or models that leave segments unserved. Are all products premium? Is there no good free tier? No affordable mid-tier?
5. **Experience gaps**: UX or workflow problems cited in reddit_sentiment or weaknesses that multiple competitors share.

# Opportunity Size Scoring

Rate each gap as:
- **high**: Multiple competitors share this weakness + directly aligns with user's preferences + reddit_sentiment confirms user frustration + commercially viable.
- **medium**: Supported by evidence from 1-2 competitors + somewhat relevant to user context + some demand signals.
- **low**: Based on a single competitor's weakness or a niche observation. Valid but less impactful.

When unsure between two levels, pick the lower one. Do not inflate.

# Quality Rules

- **Be specific in titles.** Bad: "Better mobile experience." Good: "No power tool has a native mobile-first editor with offline support."
- **Be specific in descriptions.** Explain WHY this is a gap, WHO it affects, and WHAT a solution might look like. 2-4 sentences.
- **Evidence must be traceable.** Each item in the evidence array must reference a specific competitor by name and a specific observation from their profile (e.g., "Notion: reddit_sentiment — users complain about mobile performance", "Obsidian: pricing — Sync costs $4/mo for a basic feature").
- **Do not repeat gaps in different words.** If "poor mobile" and "no offline on mobile" are really the same issue, merge them.
- **Do not fabricate evidence.** Only cite information present in the provided profiles and market overview. If a profile says nothing about mobile, you cannot claim the product has a bad mobile experience.
- **Do not restate strengths as gaps.** If a strength is shared, it's not a gap — it's table stakes.
- **Order by opportunity_size descending.** High gaps first.

# Output Format

Return ONLY a single JSON object. No markdown code fences. No explanatory text. No trailing commas.

{
  "title": "Market Gaps & Opportunities",
  "problems": [
    {
      "id": "gap-[lowercase-slug]",
      "title": "Concise, specific gap title",
      "description": "2-4 sentences: why this is a gap, who it affects, what a solution looks like.",
      "evidence": [
        "CompetitorName: field_name — specific observation from their profile",
        "CompetitorName: field_name — another specific observation"
      ],
      "opportunity_size": "high" | "medium" | "low"
    }
  ],
  "sources": ["URLs from profiles that directly support the gap analysis"]
}

# Constraints
- Output 3-6 problems. Prefer 4-5.
- Every problem MUST have at least 2 items in evidence.
- Every evidence item MUST reference a specific competitor by name.
- IDs must be unique slugs prefixed with "gap-" (e.g., "gap-mobile-first", "gap-pricing-accessibility").
- The top-level "sources" array: include only URLs you directly cited or that support your evidence. Do not dump all profile URLs.
- Do NOT include gaps already well-addressed by 2+ competitors.

# Example

Given profiles for Notion and Obsidian (note-taking domain), user wants to build a mobile-first power tool:

{
  "title": "Market Gaps & Opportunities",
  "problems": [
    {
      "id": "gap-mobile-first-power-tool",
      "title": "No power note-taking tool is designed mobile-first",
      "description": "Both Notion and Obsidian treat mobile as a secondary platform. Notion's mobile app is a stripped-down version of desktop, and Obsidian's mobile app has limited plugin support. Users who primarily work on phones have no power-tool option — they must choose between simple mobile apps or degraded desktop-first experiences.",
      "evidence": [
        "Notion: weaknesses — 'Can be slow with large workspaces', especially on mobile",
        "Notion: reddit_sentiment — 'Users love flexibility but complain about performance'",
        "Obsidian: weaknesses — 'Mobile app less polished'",
        "Obsidian: reddit_sentiment — 'Users complain about sync costs', implying mobile-desktop sync is a pain point"
      ],
      "opportunity_size": "high"
    },
    {
      "id": "gap-offline-sync",
      "title": "Reliable offline-first sync without a separate paid service",
      "description": "Notion requires internet for most operations. Obsidian is local-first but charges $4/mo for cross-device sync. No tool offers seamless offline with built-in free sync, leaving mobile users and users in low-connectivity areas without a good option.",
      "evidence": [
        "Notion: weaknesses — 'Requires internet'",
        "Obsidian: pricing_tiers — 'Sync $4/mo' is a separate paid add-on for a basic expectation",
        "Obsidian: reddit_sentiment — 'Users complain about sync costs'"
      ],
      "opportunity_size": "high"
    },
    {
      "id": "gap-learning-curve",
      "title": "Power tools require significant onboarding investment",
      "description": "Both Notion and Obsidian have steep learning curves. Notion's block system and database views confuse new users. Obsidian requires understanding markdown, file systems, and plugin curation. There's an opportunity for progressive disclosure — simple by default, powerful when needed.",
      "evidence": [
        "Notion: weaknesses — 'Steep learning curve'",
        "Obsidian: weaknesses — 'Plugin quality varies', requiring users to curate their own experience"
      ],
      "opportunity_size": "medium"
    }
  ],
  "sources": [
    "https://notion.so/pricing",
    "https://obsidian.md",
    "https://reddit.com/r/Notion/...",
    "https://reddit.com/r/ObsidianMD/..."
  ]
}
"""


def build_gap_analysis_prompt(
    domain: str,
    profiles: list[dict],
    clarification_context: dict,
    market_overview: dict | None = None,
) -> list[dict]:
    """
    Build prompt to identify market gaps from competitor profiles (build intent only).
    """
    context_parts = [GAP_ANALYSIS_PROMPT]
    context_parts.append(f"\n\n# Domain\n{domain}")
    context_parts.append(f"\n\n# User Context (Clarification Answers)\n{json.dumps(clarification_context, indent=2)}")
    if market_overview:
        context_parts.append(f"\n\n# Market Overview\n{json.dumps(market_overview, indent=2)}")
    context_parts.append(f"\n\n# Competitor Profiles\n{json.dumps(profiles, indent=2)}")
    return [{"role": "user", "content": "".join(context_parts)}]


# -----------------------------------------------------------------------------
# 6. build_problem_statement_prompt
# -----------------------------------------------------------------------------

PROBLEM_STATEMENT_PROMPT = """
# Role
You are the "Problem Definer" module for Blueprint, a product research tool. You receive market gaps that the user has chosen to focus on, along with the full research context (domain, competitors analyzed, user preferences). Your job is to synthesize these into a single, focused, actionable problem statement that could guide a product brief.

You output a single JSON object. Nothing else — no markdown, no explanation, no text before or after the JSON.

# Inputs You Will Receive

1. **Selected Gaps**: The specific market gaps the user chose to pursue (each with title, description, evidence, opportunity_size).
2. **Context**:
   - domain: The product/market domain
   - competitors_analyzed: Names of competitors that were profiled
   - clarification_context: The user's original preferences (platform, audience, positioning, etc.)

# Task

Synthesize all selected gaps into ONE cohesive problem statement. This is not a list of gaps restated — it's a unified thesis about what to build and why.

# What Makes a Good Problem Statement

1. **Specific enough to act on.** "Build a better note-taking app" is useless. "Build a mobile-first power note-taking tool with offline graph navigation for knowledge workers who can't use Obsidian on their phones" is actionable.
2. **Grounded in the research.** Every claim in the statement should trace back to the gaps and evidence. Don't introduce new market claims not supported by the input data.
3. **User-centered.** The statement frames the opportunity from the user's perspective — who they are, what they need, why existing solutions fail them.
4. **Opinionated.** Take a stance on what the product should prioritize. A problem statement that tries to address everything addresses nothing.

# Output Fields

## title
A short title for the problem statement section. Keep it to "Your Problem Statement" or a brief domain-specific variant (e.g., "Your Note-Taking Product Thesis").

## content
The core problem statement. This is the most important field. Write it as 2-4 sentences of prose (not bullets). Structure:
- Sentence 1: WHO is the target user and WHAT is their unmet need?
- Sentence 2: WHY do existing solutions fail them? (Reference the specific gaps)
- Sentence 3-4: WHAT should the product do differently? (The opportunity)

Keep it tight — aim for 40-80 words. This should fit on a slide.

## target_user
A persona description, NOT a demographic. Bad: "Males 25-34 in urban areas." Good: "Power users who want Obsidian-level depth but primarily work on their phones, often in low-connectivity environments."

Be specific about their behavior, context, and pain point. One sentence, 15-30 words.

## key_differentiators
3-5 product-level differentiators that would set this product apart. These are STRATEGIC bets, not feature specs.

Rules:
- Each differentiator should be one sentence.
- Frame as "what makes this different" not "what features it has."
- Bad: "Has a mobile app." Good: "Mobile-native graph navigation that feels built for phones, not shrunken from desktop."
- Bad: "Free sync." Good: "Offline-first with built-in peer-to-peer sync at zero cost — no separate subscription."
- Ground each in the gap evidence. If a differentiator doesn't trace back to a gap, don't include it.

## validation_questions
3-5 critical questions the founder should answer BEFORE building. These are risks, assumptions, and unknowns that the research surfaced but couldn't resolve.

Rules:
- Each question should be testable (can be answered with user interviews, prototypes, or market data).
- Frame around the biggest assumptions in the problem statement.
- Bad: "Will people like it?" Good: "Would mobile power users switch from Apple Notes if graph features added 2 seconds to note creation?"
- Bad: "Is the market big enough?" Good: "How many Obsidian users primarily use their phone — is mobile-first a 10K or 10M user opportunity?"
- Include at least one question about willingness to pay / business model.

# Output Format

Return ONLY a single JSON object. No markdown code fences. No explanatory text. No trailing commas.

{
  "title": "Your Problem Statement",
  "content": "2-4 sentence problem statement (40-80 words).",
  "target_user": "One-sentence persona description (15-30 words).",
  "key_differentiators": [
    "Strategic differentiator 1",
    "Strategic differentiator 2",
    "Strategic differentiator 3"
  ],
  "validation_questions": [
    "Critical question 1?",
    "Critical question 2?",
    "Critical question 3?"
  ]
}

# Example

Selected gaps: "No mobile-first power tool" (high) + "Offline sync requires paid service" (high)
Context: domain = "note-taking", competitors = ["Notion", "Obsidian"], user wants mobile + web, power tool, text notes.

{
  "title": "Your Problem Statement",
  "content": "Power note-taking users who work primarily on mobile have no real option — Notion is sluggish on phones and Obsidian's mobile app is a second-class citizen. Build a mobile-native knowledge tool that delivers graph-based navigation and backlinks designed for touch, with offline-first sync that works without a paid add-on.",
  "target_user": "Knowledge workers and researchers who want Obsidian-level depth but primarily capture and organize ideas on their phones.",
  "key_differentiators": [
    "Mobile-native graph navigation designed for touch — not a shrunken desktop view",
    "Offline-first architecture with free peer-to-peer sync across devices",
    "Markdown-compatible editor with mobile-optimized input (voice-to-text, swipe shortcuts)",
    "Progressive complexity — simple capture by default, power features discoverable on demand"
  ],
  "validation_questions": [
    "Would mobile power users switch from Apple Notes or Keep if graph features added 2 seconds to note creation?",
    "Can peer-to-peer sync deliver Obsidian Sync-level reliability at zero marginal cost?",
    "Is 'mobile-first power tool' a viable wedge, or do power users inherently prefer desktop for deep work?",
    "What's the willingness to pay for a mobile note tool — can this sustain a freemium model, or does it need to be fully free to compete?"
  ]
}
"""


def build_problem_statement_prompt(selected_gaps: list[dict], context: dict) -> list[dict]:
    """
    Build prompt to generate an actionable problem statement (build intent only).
    """
    context_parts = [PROBLEM_STATEMENT_PROMPT]
    context_parts.append(f"\n\n# Selected Gaps\n{json.dumps(selected_gaps, indent=2)}")
    context_parts.append(f"\n\n# Research Context\n{json.dumps(context, indent=2)}")
    return [{"role": "user", "content": "".join(context_parts)}]


# -----------------------------------------------------------------------------
# 7. build_fix_json_prompt
# -----------------------------------------------------------------------------


def build_fix_json_prompt(broken_output: str, expected_schema: dict) -> list[dict]:
    """
    Build prompt to fix malformed LLM JSON output.

    Input:
        broken_output: The raw string that failed JSON parsing or validation
        expected_schema: The JSON schema dict (from Pydantic model.model_json_schema())

    Instructions to LLM:
        - The previous output had a JSON formatting error
        - Here is the broken output and the expected schema
        - Return ONLY valid JSON matching the schema, nothing else

    Returns:
        [{"role": "user", "content": "..."}]
    """
    content = (
        "The previous output had a JSON formatting error. "
        "Fix it and return ONLY valid JSON matching the expected schema below. "
        "No markdown code fences, no explanation text outside the JSON.\n\n"
        f"# Broken output\n{broken_output}\n\n"
        f"# Expected schema\n{json.dumps(expected_schema, indent=2)}"
    )
    return [{"role": "user", "content": content}]


# -----------------------------------------------------------------------------
# 8. Quick Response Templates
# -----------------------------------------------------------------------------

SMALL_TALK_RESPONSES = [
    "Hey! I'm Blueprint, your product research assistant. What would you like to build or explore?",
    "Hello! I help with product strategy and market research. What's on your mind?",
    "Hi there! Tell me what product or market you'd like to research.",
    "I'm Blueprint — here to help you explore markets and find opportunities. What are you working on?",
    "Thanks! I'm ready when you are. What product space would you like to explore?",
    "Good to see you! Describe a product idea or market you want to research.",
]

OFF_TOPIC_RESPONSES = [
    "I focus on product strategy and market research — I can't help with that, but I'd love to help you explore a product idea!",
    "That's outside my scope — I'm built for competitive analysis and product research. What market would you like to explore?",
    "I specialize in product and market research. Try me with a product idea or industry you're curious about!",
    "I can't help with that, but I'm great at competitor research and market analysis. What would you like to build?",
]


def get_quick_response(intent_type: str) -> str:
    """
    Return a hardcoded quick response for small_talk or off_topic intents.

    Used as a fallback when the LLM's quick_response is missing/empty,
    or as a replacement to skip the LLM-generated response entirely.

    Args:
        intent_type: "small_talk" or "off_topic"

    Returns:
        A friendly, brief response string.
    """
    if intent_type == "small_talk":
        return random.choice(SMALL_TALK_RESPONSES)
    elif intent_type == "off_topic":
        return random.choice(OFF_TOPIC_RESPONSES)
    return ""
