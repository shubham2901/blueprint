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
