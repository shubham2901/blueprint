# Blueprint — Design Guide: "Cozy Sand" Theme

---

## 1. Core Aesthetic

- **Direction**: Minimal, scholarly, and cozy. A blend of modern web utility with editorial, library-inspired warmth.
- **Mood**: Focused, human, and professional. "Library-esque."
- **Reference feel**: A well-designed academic journal meets a modern SaaS tool.

---

## 2. Color Palette

| Token | Value | Usage |
|-------|-------|-------|
| **Page Background** | Soft Cream/Sand `#F9F7F2` | Sidebar background, outer page, dashboard |
| **Workspace Background** | Pure White `#FFFFFF` | Left panel cards, input fields, modal backgrounds |
| **Primary Text** | Charcoal Brown `#1F1F1F` | Headings, button labels, strong text |
| **Secondary Text** | Muted Warm Gray `#737373` | Labels, body text, descriptions, metadata |
| **Placeholder Text** | Light Warm Gray `#A3A3A3` | Input placeholders, hints, disabled text |
| **Accent (Active/Selection)** | Terracotta / Clay Red `#A65D47` | Active tab underline, selected chips, primary action buttons, links |
| **Accent Light** | Light Terracotta `#A65D4715` (or ~8% opacity) | Selected chip fill, hover backgrounds |
| **Borders** | Hairline Warm Gray `#E5E5E5` | Card borders, dividers, input borders |
| **Success** | Muted Green `#5C8A5E` | Completed step checkmarks |
| **Error/Destructive** | Muted Red `#C45C5C` | Delete actions, error states |

---

## 3. Typography

| Role | Font | Style | Usage |
|------|------|-------|-------|
| **Headings / "The Voice"** | `Newsreader` (Serif) | Medium or italic, generous size | Page titles, empty state headings, Blueprint document title, section headings |
| **UI / System Text** | `Inter` (Sans-Serif) | Regular 400, Medium 500 | Tabs, buttons, labels, chat messages, body paragraphs, metadata |

- Headings use the Serif font to feel like a high-end publication.
- All interactive and system-level text uses the Sans-Serif for legibility.
- Fallback serif: `Fraunces`, `EB Garamond`, `Georgia`.
- Fallback sans: `Geist`, `Public Sans`, `system-ui`.

### Type Scale

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page/document title | Newsreader | 28-32px | Medium / Italic |
| Section heading | Newsreader | 20-24px | Medium |
| Card title | Inter | 16-18px | Semibold (600) |
| Body text | Inter | 14-15px | Regular (400) |
| Labels / secondary | Inter | 13px | Regular (400) |
| Metadata / captions | Inter | 12px | Regular (400), small-caps for technical metadata |

---

## 4. Layout Structure

### Two-Panel Desktop Layout (Main App)

- **Left Panel (Workspace)**: ~70% width. Pure white background (`#FFFFFF`) with large soft rounded corners (24px radius). Contains top-aligned navigation tabs ("Research", "Blueprint").
- **Right Sidebar**: ~30% width. Sand-colored background (`#F9F7F2`). Contains the chat/interaction panel inside its own white rounded-corner container.
- **Outer page**: Sand background (`#F9F7F2`) visible as padding around and between panels.

### Single-Panel Layout (Dashboard)

- Sand background, centered content area (max-width ~900px) with white cards.

---

## 5. UI Components

### Tabs

- Minimal text links in `Inter` sans-serif.
- Active state: Charcoal Brown text with a bold 2px terracotta (`#A65D47`) underline.
- Inactive state: Muted Warm Gray text, no underline.

### Selection Chips

- Rounded pills with hairline border (`#E5E5E5`), white fill.
- Selected state: Terracotta border (`#A65D47`) + light terracotta fill (`#A65D4715`).
- Hover state: Very subtle warm gray fill.

### Action Buttons

- **Primary (e.g., "Start Research")**: Terracotta background (`#A65D47`), white text, rounded (8px radius).
- **Secondary (e.g., "RUN")**: Charcoal Brown background (`#1F1F1F`), white text, rounded.
- **Tertiary / Ghost (e.g., "Edit", "Remove")**: No background, muted warm gray text. Hover: subtle background.
- **Destructive (e.g., "Delete")**: No background, muted red text (`#C45C5C`).

### Cards / Blocks

- White background (`#FFFFFF`).
- Hairline warm gray border (`#E5E5E5`).
- Large rounded corners (16px radius for workspace cards, 24px for main panels).
- No heavy box shadows. If shadows are used: `0 1px 3px rgba(0,0,0,0.04)`.
- Block actions appear on hover (edit, delete, add to Blueprint).

### Input Field

- Floating white card at the bottom of the sidebar.
- Rounded corners (12-16px radius), hairline border.
- Left side: optional vertical toolbar (attachment icon, image icon) — muted gray icons.
- Right side: text area with placeholder text.
- Far right inside the field: "RUN" button (charcoal brown, rounded, compact).

### Sidebar Header

- Left-aligned: "B" logo (white letter in a black circle, small).
- Center/right: "1 SESSION LEFT" status pill (small, muted, warm gray border + text).
- Far right: "Sign up" text button and a history icon (clock icon).

### Progress Indicator

- Vertical step list inside the sidebar.
- Completed: Muted green checkmark icon + secondary gray text.
- Current: Terracotta spinning/pulsing indicator + charcoal text (slightly bold).
- Pending: Gray-300 circle outline + placeholder gray text.

### Empty States

- Centered in the workspace panel.
- A soft-toned abstract icon (line art, not colorful).
- Heading in Newsreader Serif (italic or medium): "Begin your inquiry."
- Description in Inter sans-serif, muted gray: "Your research notes and discovered insights will be collected here."

### Suggested Research Pills (Sidebar Welcome)

- Small rounded pills shown below the welcome message: "Market Analysis", "User Personas", "Competitor Research", etc.
- Same styling as selection chips (hairline border, rounded, clickable).

---

## 6. Spacing and Sizing

| Property | Value |
|----------|-------|
| Main panel corner radius | 24px |
| Card corner radius | 16px |
| Button / input corner radius | 8-12px |
| Chip / pill corner radius | 20px |
| Spacing between blocks/cards | 16px |
| Spacing between sections | 24px |
| Card internal padding | 20-24px |
| Sidebar width | ~30% of viewport (min 320px) |
| Workspace width | ~70% of viewport |

---

## 7. Shadows and Depth

- Extremely subtle or non-existent. Rely on background color contrast and borders for depth.
- If used: `0 1px 3px rgba(0,0,0,0.04)` — barely visible.
- Hover state on cards: `0 2px 8px rgba(0,0,0,0.06)` — a slight lift, nothing dramatic.

---

## 8. Sidebar Footer

- Small-caps technical metadata in muted gray, 11-12px: `MODEL: BLUEPRINT V2.0`
- Keyboard shortcut hints in the same style: `Cmd+Enter to send`

---

## 9. Error States and User-Facing Error Display

All errors shown to the user follow a strict pattern: a friendly human-readable message plus a reference code. **Never** show raw error strings, stack traces, HTTP status codes, provider names, or technical details.

### Error Reference Code

- Format: `Ref: BP-XXXXXX` (6 uppercase hex characters, e.g., `Ref: BP-3F8A2C`)
- Generated on the backend via `generate_error_code()` and included in every `block_error` and `error` SSE event
- Displayed in all error UI so users can quote it when reporting issues
- The same code appears in backend logs — the team greps for it to find the exact failure

### Block Error Card (inline, per-block failure)

- **Background**: `bg-amber-50` (soft amber/yellow)
- **Border**: `border-amber-200` (1px, left accent or full border)
- **Icon**: Warning triangle icon in `text-amber-600`
- **Block name**: Inter semibold 14px, `text-amber-800`
- **Error message**: Inter regular 14px, `text-amber-800` — friendly, never technical
- **Reference code**: Inter regular 12px, `text-amber-600` — displayed below the error message as `Ref: BP-XXXXXX`
- **Action**: "Try again" button (secondary style — charcoal background, white text, 8px radius)
- **Layout**: Same width as research block cards. Compact padding (16px).

### Toast Notification (recoverable error)

- Appears at the top of the Sidebar panel
- **Background**: White card with `border-error` left accent (4px, Muted Red `#C45C5C`)
- **Icon**: Alert circle icon in `text-error` (Muted Red)
- **Message**: Inter regular 14px, `text-charcoal` — friendly message
- **Reference code**: Inter regular 11px, `text-secondary` — `Ref: BP-XXXXXX`
- **Auto-dismiss**: 8 seconds. No manual close button needed (but nice to have).
- **Animation**: Fade in from top, fade out.

### Error Modal (non-recoverable error)

- Full modal overlay (same as AuthModal pattern — uses shadcn/ui Dialog)
- **Background**: White, `rounded-card` (16px)
- **Icon**: Large alert circle icon in `text-error`, centered above heading
- **Heading**: Newsreader serif, 20px, `text-charcoal` — "Something went wrong"
- **Message**: Inter regular 14px, `text-secondary` — friendly, 1-2 sentences
- **Reference code**: Inter mono/regular 13px, `text-secondary`, inside a `bg-sand rounded-lg px-3 py-2` pill — **clickable to copy**. On click, brief "Copied!" tooltip or text change.
- **Action**: "Start New Research" button (primary — terracotta background, white text)
- **Layout**: Centered content, 24px spacing between elements.

### REST Error (non-SSE, inline)

- When a REST fetch fails (e.g., loading journeys on dashboard), display an inline error message in place of the expected content.
- **Message**: Inter regular 14px, `text-secondary` — "Could not load data. (Ref: BP-XXXXXX)"
- The ref code here comes from the `X-Request-Id` header that was sent with the request.
- Optionally include a "Retry" text button (`text-terracotta`, underline on hover).

### What to NEVER show

- Raw exception messages (e.g., `"litellm.RateLimitError: ..."`)
- HTTP status codes (e.g., `"Error 500"`, `"Error 429"`)
- Provider names (e.g., `"Gemini failed"`, `"Tavily returned 403"`)
- Internal model names (e.g., `"gemini/gemini-2.0-flash"`)
- JSON parsing errors (e.g., `"Unexpected token < in JSON at position 0"`)
- Stack traces or file paths
- Database error messages
