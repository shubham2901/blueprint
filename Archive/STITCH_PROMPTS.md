# Blueprint — Google Stitch Prompts (Per Screen)

Style direction for all screens: "Cozy Sand" theme — minimal, scholarly, and cozy. Library-inspired warmth. Soft cream/sand background (#F9F7F2) for the page and sidebar. Pure white (#FFFFFF) for workspace cards and inputs. Terracotta/clay red (#A65D47) as the accent color for active states, selected chips, and primary buttons. Charcoal brown (#1F1F1F) for headings and strong text. Muted warm gray (#737373) for secondary text. Newsreader (elegant Serif) for headings and display text. Inter (Sans-Serif) for UI elements and body text. Large soft rounded corners (24px on main panels, 16px on cards). No heavy shadows. Hairline warm gray borders (#E5E5E5).

---

## Screen 1: Landing / Empty State

```
Design a web application called "Blueprint" — a product research tool with a scholarly, cozy aesthetic.

Layout: Two-panel desktop layout on a soft cream/sand background (#F9F7F2). Left workspace takes ~70% width, right sidebar takes ~30% width. Both panels have large soft rounded corners (24px radius). Generous padding between panels and the page edges.

LEFT PANEL (Workspace):
- Pure white background (#FFFFFF), large rounded corners (24px).
- Two tabs at the top inside the panel: "Research" (active — charcoal brown text with a bold 2px terracotta underline) and "Blueprint" (inactive — muted warm gray text, no underline). Tabs use Inter sans-serif font, 14px.
- Below the tabs, the panel is empty with a centered empty state:
  - A soft-toned abstract line-art icon (minimal, not colorful — something suggesting exploration or a compass).
  - Below the icon: an elegant serif heading in Newsreader font, italic or medium weight, charcoal brown: "Begin your inquiry."
  - Below that: a description in Inter sans-serif, muted warm gray (#737373): "Your research notes and discovered insights will be collected here."

RIGHT SIDEBAR:
- Sand/cream background (#F9F7F2).
- At the very top: a horizontal header row containing:
  - Left: A small "B" logo (white letter in a black circle).
  - Center: A small status pill with hairline border: "1 SESSION LEFT" in muted gray, small caps.
  - Right: A "Sign up" text button in terracotta (#A65D47) and a small history icon (clock) in muted gray.
- Below the header: a large serif heading in Newsreader font, charcoal brown: "What are you exploring today?"
- Below the heading: a short description in Inter, muted warm gray: "Describe a product, market, or idea to research."
- Below the description: a row of suggested research pills — small rounded chips with hairline borders: "Market Analysis", "Competitor Research", "User Personas", "Pricing Intel". White fill, warm gray border, Inter font, 13px.
- At the very bottom of the sidebar: a floating white card (rounded corners, 16px radius, hairline border) containing:
  - Left side: Two small muted gray icons stacked vertically (attachment icon, image icon).
  - Right side: A text input area with placeholder text in light warm gray italic: "I want to compete with Notion..."
  - Far right inside the card: A compact "RUN" button in charcoal brown (#1F1F1F) background with white text, rounded.
- Very bottom below the input card: small-caps metadata text in muted gray, 11px: "MODEL: BLUEPRINT V2.0" and "Cmd+Enter to send".

Style: Minimal, scholarly, cozy. Think library meets modern SaaS. Newsreader serif for headings gives it an editorial quality. Cream/sand tones feel warm and approachable. No heavy shadows — depth comes from color contrast between sand background and white cards. Hairline borders only.

Desktop viewport (1440px wide).
```

---

## Screen 2: Clarification Questions

```
Design a web application screen for "Blueprint" — a product research tool with a scholarly, cozy "Cozy Sand" theme.

Layout: Two-panel layout on soft cream/sand background (#F9F7F2). Left workspace (~70%, white, 24px corners), right sidebar (~30%, sand background).

LEFT PANEL (Workspace):
- Same empty state as the landing screen. Tabs at top: "Research" (active, terracotta underline) and "Blueprint" (inactive, gray).
- Centered empty state with line-art icon, serif heading "Begin your inquiry." and sans-serif description.

RIGHT SIDEBAR:
- Top header: "B" logo, "1 SESSION LEFT" pill, "Sign up" button, history icon.
- Conversation history inside a white rounded container:
  1. A user message (right-aligned, subtle warm background — very light sand/beige): "I want to build a personal finance app" in Inter, charcoal brown.
  2. A system response (left-aligned, no background):
     Text in Inter, charcoal brown: "I have a few questions before I start researching."

     Below the text, two question groups with clear spacing:

     QUESTION 1:
     Label in Inter, 13px, muted warm gray (#737373): "Which segment are you interested in?"
     Below: Four clickable chips in a horizontal wrap layout. Each chip is a rounded pill (20px radius) with a hairline warm gray border (#E5E5E5) and white fill. Text in Inter, 13px, charcoal brown.
     Chips: "Budgeting", "Investment tracking", "Expense splitting", "All-in-one".
     One chip ("Budgeting") is selected — it has a terracotta border (#A65D47) and a very light terracotta fill.

     QUESTION 2:
     Label: "Target market?"
     Below: Four chips: "US", "India", "Global", "Other...". None selected yet (all white with gray borders).

     Below both question groups: A primary button — terracotta background (#A65D47), white text, rounded (8px), Inter font: "Start Research". Currently in a slightly muted/disabled state since not all questions are answered.

- At the bottom: the floating white input card with "RUN" button (same as landing).

Style: Cozy Sand theme. Chips should feel tactile — rounded pills that are easy to click. Selected state is clearly marked with terracotta. The conversation area has generous line spacing. Serif font NOT used here — this is all UI text in Inter.

Desktop viewport (1440px wide).
```

---

## Screen 3: Research In Progress

```
Design a web application screen for "Blueprint" — a product research tool with the "Cozy Sand" theme.

Layout: Two-panel layout on soft cream/sand background (#F9F7F2). Left workspace (~70%, white, 24px corners), right sidebar (~30%, sand background).

LEFT PANEL (Workspace):
- Tabs at top: "Research" (active, terracotta underline) and "Blueprint" (inactive, gray).
- The main area shows a loading/skeleton state:
  - 3-4 skeleton block placeholders stacked vertically with 16px spacing.
  - Each skeleton block is a rounded rectangle (16px corners) with a very light warm gray fill (#F5F5F0 — warmer than standard gray) and animated shimmer lines inside representing text.
  - The shimmer should be subtle and warm-toned — not the typical cold gray shimmer. A gentle warm gradient sweep.

RIGHT SIDEBAR:
- Top header: "B" logo, "1 SESSION LEFT" pill, "Sign up", history icon.
- Conversation history in white rounded container:
  1. User message: "I want to build a personal finance app"
  2. System clarification questions with answered chips (selected chips have terracotta borders and light terracotta fill, non-selected are grayed out).
  3. System message in Inter, charcoal brown: "Researching the personal finance app space in the budgeting segment."

  Below that, a step-based progress indicator (vertical list, left-aligned):
  - "Scanning the market" — muted green (#5C8A5E) checkmark icon, muted warm gray text, done.
  - "Finding competitors" — terracotta (#A65D47) pulsing dot or small spinner, charcoal brown text (slightly bold), current step.
  - "Analyzing profiles" — light warm gray (#A3A3A3) circle outline, light gray text, pending.

  Each step is a single line with an icon on the left and text on the right. Compact, Inter font, 13-14px.

- At the bottom: the floating white input card, dimmed/disabled during research. Placeholder text: "Research in progress..." in light warm gray.

Style: Cozy Sand theme. The skeleton loading should feel warm, not clinical. The progress steps should be understated but readable. Terracotta spinner/indicator for the active step matches the overall accent color.

Desktop viewport (1440px wide).
```

---

## Screen 4: Research Results

```
Design a web application screen for "Blueprint" — a product research tool with the "Cozy Sand" theme.

Layout: Two-panel layout on soft cream/sand background (#F9F7F2). Left workspace (~70%, white, 24px corners), right sidebar (~30%, sand background).

LEFT PANEL (Workspace):
- Tabs at top: "Research" (active, terracotta underline) and "Blueprint" (inactive, gray). A small count badge on the Blueprint tab: "0" in muted gray or empty.
- Below the tabs: a scrollable list of research output blocks, stacked vertically with 16px spacing.

  BLOCK 1 — Market Overview:
  - White background, hairline warm gray border (#E5E5E5), rounded corners (16px).
  - Internal padding: 20-24px.
  - Title in Inter, 16-18px, semibold, charcoal brown (#1F1F1F): "Market Overview: Personal Finance Apps"
  - Body: 2-3 lines of paragraph text in Inter, 14px, muted warm gray (#737373). Use realistic placeholder text about the personal finance app market — size, growth, key trends.
  - Bottom bar: three actions aligned right, shown as small text buttons in Inter, 13px:
    - "Edit" (pencil icon, muted warm gray)
    - "Add to Blueprint" (terracotta text #A65D47, slightly bolder — this is the primary action)
    - "Delete" (trash icon, muted warm gray, subtle)

  BLOCK 2 — Competitors List:
  - Same card style.
  - Title: "Competitors (6)"
  - Body: A compact list in Inter, 14px:
    - "Mint — Free budgeting and expense tracking by Intuit"
    - "YNAB — Envelope-style budgeting with subscription model"
    - "Monarch Money — Modern finance dashboard for couples and families"
    - "Goodbudget — Envelope budgeting based on the cash system"
    - "PocketGuard — Simplified spending tracker with bill negotiation"
    - "Copilot Money — Premium finance app for iOS"
  - Each competitor name in charcoal brown (semibold), description in muted warm gray.
  - Same bottom action bar.

  BLOCK 3 — Competitor Detail (Mint):
  - Same card style.
  - Title: "Mint" in Inter semibold, charcoal brown. Small subtitle below in muted warm gray, 13px: "by Intuit — mint.com"
  - Body sections with subtle spacing:
    - "Overview": 2-3 sentences in muted warm gray.
    - "Key Features": bullet list (3-4 items).
    - "Pricing": one line.
    - "Target Audience": one line.
    - Section labels in Inter, 13px, charcoal brown, medium weight.
  - Sources at the bottom in Inter, 12px, light warm gray (#A3A3A3): "Sources: mint.com, g2.com/mint"
  - Same bottom action bar.

  Show 3 blocks fully visible, with a 4th partially visible below the fold to suggest scrolling.

RIGHT SIDEBAR:
- Top header: "B" logo, "1 SESSION LEFT" pill, "Sign up", history icon.
- Conversation history in white rounded container.
- At the bottom of the conversation: system message in Inter: "Research complete. I found 6 competitors in the budgeting space. Review the results and add what's useful to your Blueprint."
- All progress steps show muted green checkmarks.
- Input card at the bottom is active again with placeholder: "Ask a follow-up question..."

Style: Cozy Sand theme. Cards should be clean with hairline borders — not boxy or heavy. Hover state on cards: very subtle warm shadow lift (0 2px 8px rgba(0,0,0,0.06)). The "Add to Blueprint" action in terracotta stands out against the gray edit/delete actions. The overall feel should be like reading a well-typeset research report.

Desktop viewport (1440px wide).
```

---

## Screen 5: Research Results — Block in Edit Mode

```
Design a web application screen for "Blueprint" showing a research block in edit mode. Uses the "Cozy Sand" theme.

Layout: Same two-panel layout as Screen 4. Cream/sand page background, white workspace, sand sidebar.

LEFT PANEL:
- Same tabs (Research active), same blocks visible.
- BLOCK 3 (Competitor Detail for Mint) is now in edit mode:
  - The card now has a terracotta border (#A65D47, 2px) instead of the default hairline gray border. This clearly signals "you are editing."
  - The text content inside is now editable — show a text cursor blinking in the body text.
  - The body text looks like a minimal inline editor — no toolbar, just the text is directly editable. The user has made a visible edit: they deleted one bullet point and typed a note at the bottom in a slightly different treatment (italic or muted warm gray, suggesting user-added content).
  - The bottom action bar changes to: "Done" (terracotta background button, white text, rounded), "Add to Blueprint" (terracotta text), "Cancel" (muted warm gray text).
- Other blocks remain in their normal read-only state with hairline gray borders.

RIGHT SIDEBAR: Same as Screen 4.

Style: Cozy Sand theme. Edit mode should feel inline and lightweight. The terracotta border is the only strong visual change — the card stays in place, content becomes editable. No modal, no separate editor view.

Desktop viewport (1440px wide).
```

---

## Screen 6: Blueprint Tab (Curated Document)

```
Design a web application screen for "Blueprint" showing the Blueprint tab — the user's curated output document. Uses the "Cozy Sand" theme.

Layout: Two-panel layout on soft cream/sand background (#F9F7F2). Left workspace (~70%, white, 24px corners), right sidebar (~30%, sand background).

LEFT PANEL (Workspace):
- Tabs at top: "Research" (inactive, muted gray) and "Blueprint" (active, terracotta underline). Small badge on Blueprint tab: "3".
- Below the tabs:

  TOP SECTION:
  - An editable title in Newsreader serif font, 28-32px, medium/italic weight, charcoal brown (#1F1F1F): "Personal Finance App — Research Brief". A subtle pencil icon appears on hover to indicate the title is editable.
  - Below the title: a small action in Inter, 13px, muted warm gray: "Copy as Markdown" with a small copy icon. Underlined on hover.

  ENTRIES:
  - Three entries stacked vertically with 16px spacing. Each entry is a card with:
    - White background, hairline warm gray border, 16px rounded corners.
    - A thin left accent border (3px, terracotta #A65D47) on the left edge to distinguish Blueprint entries from research blocks.
    - A small source tag at the top-right inside the card in Inter, 12px, light warm gray (#A3A3A3): "From: Market Overview" or "From: Mint".

  ENTRY 1:
  - Content: Market overview text in Inter, 14px, muted warm gray.
  - Bottom: "Edit" (pencil icon, muted gray) and "Remove" (X icon, muted gray).

  ENTRY 2:
  - Content: Competitors list.
  - Same bottom actions.

  ENTRY 3:
  - Content: Mint competitor detail. The user has edited this entry — they added a personal note at the bottom in italic Inter, slightly different from the original text to suggest user additions.
  - Same bottom actions.

  Below the last entry: a hint in Inter, 13px, light warm gray (#A3A3A3), centered: "Add more from the Research tab."

RIGHT SIDEBAR:
- Same structure as before. Chat is still available.
- A contextual system message near the top of the conversation: "Your Blueprint has 3 entries. Keep researching or export when ready." in Inter, muted warm gray.

Style: Cozy Sand theme. The Blueprint tab should feel like reading a curated document or brief — the Newsreader serif title gives it an editorial, publication quality. The left terracotta accent border on entries provides a visual thread tying the document together. It should feel more like a drafted report than a list of cards.

Desktop viewport (1440px wide).
```

---

## Screen 7: Dashboard (Returning User)

```
Design a web application screen for "Blueprint" — the dashboard for returning users. Uses the "Cozy Sand" theme.

Layout: Full-width single panel. Soft cream/sand background (#F9F7F2) covering the entire page. Centered content area with max-width ~900px.

TOP NAVBAR:
- A clean horizontal bar (transparent or sand-colored, no hard border at bottom — maybe a very subtle hairline):
  - Left: "Blueprint" in Newsreader serif font, 20px, medium weight, charcoal brown. Or the "B" circle logo next to the word "Blueprint."
  - Right: User avatar (small circle with initials, charcoal brown background, white text) and a "New Session" button (terracotta background #A65D47, white text, rounded 8px, Inter font).

MAIN CONTENT:
- Heading in Newsreader serif, 24-28px, medium/italic, charcoal brown: "Your Sessions"
- Below: a list of session cards stacked vertically with 16px spacing.

  SESSION CARD 1:
  - White background (#FFFFFF), hairline warm gray border (#E5E5E5), rounded corners (16px).
  - Internal padding: 20px.
  - Left side:
    - Session title in Inter, 16px, semibold, charcoal brown: "Personal Finance App Research"
    - Below: subtitle in Inter, 13px, muted warm gray: "Started 2 days ago — 3 items in Blueprint"
  - Right side: A "Resume" button (outlined, hairline warm gray border, charcoal brown text, rounded 8px) and a small "..." menu icon in muted gray for additional actions.

  SESSION CARD 2:
  - Title: "Food Delivery Market — India"
  - Subtitle: "Started 5 days ago — 7 items in Blueprint"
  - Same layout and actions.

  SESSION CARD 3:
  - Title: "Untitled Session"
  - Subtitle: "Started 1 week ago — 0 items in Blueprint"
  - Same layout and actions.

- Empty state (if no sessions): centered content with a soft line-art icon, Newsreader serif heading "No sessions yet," and Inter description: "Start your first research to build a Blueprint." with a "New Session" button (terracotta).

Style: Cozy Sand theme. The dashboard should feel calm and organized — like a personal research library. Session cards are clean and scannable. The serif heading and warm tones keep the editorial feel consistent with the main app.

Desktop viewport (1440px wide).
```

---

## Screen 8: Signup / Auth Modal

```
Design a modal overlay for "Blueprint" — a product research tool. Uses the "Cozy Sand" theme.

BACKGROUND: The main app (workspace + sidebar) is visible but dimmed with a warm semi-transparent overlay (not cold gray — use a warm beige/brown tint at ~40% opacity).

MODAL:
- Centered on screen. White background (#FFFFFF), rounded corners (24px — matching the main panel style), very subtle warm shadow.
- Width: ~400px.

CONTENT:
- Top: The "B" circle logo centered, then below it "Blueprint" in Newsreader serif, 24px, medium weight, charcoal brown, centered.
- Below: A message in Inter, 14px, muted warm gray (#737373), centered: "Sign up to save your research, create multiple sessions, and export your Blueprints."
- Below the message (with 24px spacing):
  - "Continue with Google" button: Full width, white background, hairline warm gray border, 12px rounded corners. Google "G" icon on left, "Continue with Google" text in charcoal brown Inter font. Hover: subtle warm gray fill.
  - A subtle divider: thin hairline with "or" text in the middle in muted warm gray, 12px.
  - Email input field: Full width, hairline warm gray border, 12px rounded corners. Placeholder in light warm gray: "Email address". Inter font.
  - "Continue with Email" button: Full width, terracotta background (#A65D47), white text, 12px rounded corners. Inter font, medium weight.
- Bottom: Small text in Inter, 13px, muted warm gray: "Already have an account?" followed by "Log in" as a terracotta text link.

Style: Cozy Sand theme. The modal should feel warm and inviting, not clinical. Rounded corners match the app's overall soft aesthetic. The warm overlay behind the modal keeps the scholarly mood.

Desktop viewport.
```

---

## Screen 9: Sidebar Collapsed State

```
Design a web application screen for "Blueprint" showing the sidebar in collapsed state. Uses the "Cozy Sand" theme.

Layout: Soft cream/sand background (#F9F7F2). The workspace now takes nearly the full width (~93%). The sidebar is collapsed to a thin vertical strip (~48px wide) on the right edge.

COLLAPSED SIDEBAR:
- A thin vertical strip with the sand/cream background (#F9F7F2).
- At the top: the "B" circle logo (white letter in black circle, small — 28px).
- Below the logo: a small expand icon (chevron-left) in muted warm gray.
- Optionally: a small terracotta dot indicator if there are unread messages or if research has completed.

LEFT PANEL (Workspace):
- Now takes nearly the full width, inside a white card with 24px rounded corners.
- Shows the Research tab with blocks as in Screen 4, but wider — blocks have more horizontal breathing room.
- Same tabs, same card styles, same actions.

Style: Cozy Sand theme. The collapsed sidebar should be very thin and unobtrusive — just enough to show the logo and expand icon. The workspace expands gracefully to fill the space.

Desktop viewport (1440px wide).
```

---

## Theme Reference (for all screens)

Copy this as context/prefix when generating any screen:

```
Theme: "Cozy Sand" — minimal, scholarly, cozy, library-inspired warmth.

Colors:
- Page/sidebar background: Soft Cream #F9F7F2
- Workspace/cards: Pure White #FFFFFF
- Primary text: Charcoal Brown #1F1F1F
- Secondary text: Muted Warm Gray #737373
- Placeholder text: Light Warm Gray #A3A3A3
- Accent (active/selected): Terracotta #A65D47
- Accent light fill: #A65D4715
- Borders: Hairline Warm Gray #E5E5E5
- Success: Muted Green #5C8A5E

Typography:
- Headings/display: Newsreader (Serif), medium or italic
- UI/body: Inter (Sans-Serif), regular/medium

Layout:
- Main panels: 24px border radius
- Cards: 16px border radius
- Buttons/inputs: 8-12px border radius
- Chips/pills: 20px border radius
- Shadows: Extremely subtle (0 1px 3px rgba(0,0,0,0.04)) or none
- Spacing: 16-24px between elements
```
