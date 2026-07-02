# Handoff: Vortex Digital — MCP Agent Console (Light)

## Overview
A full-screen web console for **Vera**, an internal "knowledge agent" for Vortex Digital. The screen is the agent's landing/empty state: it introduces Vera, shows which internal data sources are connected, offers a set of one-click "Try asking" prompt suggestions, and provides a message composer at the bottom. Clicking a suggestion pre-fills the composer.

This handoff documents the **light workspace** variant only (the dark "console" variant in the same source file is out of scope).

## About the Design Files
The files in this bundle are **design references created in HTML** — a prototype showing the intended look and behavior, **not production code to copy directly**. The `.dc.html` file is a self-contained design component that renders via the bundled `support.js` runtime; it is a visual spec, not a shippable component.

Your task is to **recreate this design in the target codebase's existing environment** (React, Vue, Svelte, SwiftUI, etc.) using its established components, styling system, and conventions. If no front-end environment exists yet, choose the most appropriate framework for the project and implement it there. Match the layout, tokens, and interactions documented below; source your primitives (buttons, inputs, pills) from the app's existing design system where they exist.

## Fidelity
**High-fidelity.** Colors, typography, spacing, and interactions are final. Recreate the UI to match the exact values in the Design Tokens section. Only substitute values where your codebase's design system provides an established equivalent (e.g. an existing pill/chip component).

## Layout (single screen)

Fixed application shell — **header / body**, body split into a fixed-width **sidebar** and a flexible **main** column. In the mock the frame is 1360×840 with an 18px radius and drop shadow; in production treat it as a **full-viewport app** (the frame is only for presentation). Nothing scrolls except the main content region.

```
┌───────────────────────────────────────────────────────────┐
│ HEADER  [logo] Vortex Digital / MCP AGENT CONSOLE   date · status pill │
├───────────────┬───────────────────────────────────────────┤
│ SIDEBAR 320px │ MAIN (flex:1)                             │
│  agent avatar │   scroll region (padding 44px)            │
│  + name       │     "Hi, I'm Vera."                        │
│  description  │     subtext                                │
│  ── divider   │     TRY ASKING                             │
│  CONNECTED    │     [chip] [chip] [chip] …                 │
│   SOURCES     │                                            │
│  · 5 rows     │   ── input bar (pinned bottom) ──          │
│  model label  │     [ message composer …          ↑ ]     │
└───────────────┴───────────────────────────────────────────┘
```

- **Body:** `display:flex; flex:1; min-height:0`.
- **Sidebar:** `width:320px; flex:none; display:flex; flex-direction:column; padding:22px 20px; border-right:1px solid #e9ebf2; background:#ffffff`. A `flex:1` spacer pushes the "model · vortex-mcp-1" label to the bottom.
- **Main:** `flex:1; display:flex; flex-direction:column; min-width:0; background:#f6f7fb`. Two children: a scrollable content area (`flex:1; overflow:auto; padding:44px 44px 8px`) and a pinned input bar (`flex:none`).
- **Content max-width:** inner content and the input row are both capped at `max-width:780px; margin:0 auto`.

## Components

### Header
- Container: `display:flex; align-items:center; justify-content:space-between; padding:14px 22px; border-bottom:1px solid #e9ebf2; background:#ffffff`.
- **Logo tile:** 40×40, `border-radius:11px; background:#ffffff; overflow:hidden; box-shadow: inset 0 0 0 1px rgba(20,25,60,0.08)`. Contains `assets/vortex-logo.png` at `width:100%; height:100%; object-fit:cover`.
- **Brand block** (gap 2px): title "Vortex Digital" — Space Grotesk 700, 16px, letter-spacing -0.01em, #171a2b. Sub "MCP AGENT CONSOLE" — IBM Plex Sans, 10.5px, #8288a0, letter-spacing .14em.
- **Right cluster** (gap 16px): date text (12.5px, #6a6f85, e.g. "Thu, Jul 2"); a 1×24px divider `#e5e8f0`; **status pill**.
- **Status pill:** `padding:6px 12px; border-radius:999px; background:rgba(16,185,129,0.10); border:1px solid rgba(16,185,129,0.25)`. 7×7 green dot `#10b981` + text "All systems operational" (12.5px, #0f9d6b).

### Sidebar — Agent identity
- **Avatar:** 46×46 circle. Background `radial-gradient(125% 125% at 50% 8%, #1c2544 0%, #0c1223 100%)`, `box-shadow: inset 0 0 0 1px rgba(255,255,255,0.06)`. Contains the animated **robot-head SVG** (see Robot avatar section).
- **Name** "Vera": Space Grotesk 700, 17px, #171a2b. Label "KNOWLEDGE AGENT": IBM Plex Sans, 10.5px, #8288a0, letter-spacing .12em.
- **Description** paragraph: 13.5px, line-height 1.6, #565c72 — "I connect to Vortex's internal systems to answer questions about people, customers, documents, policies, and meeting notes — in plain language."
- **Divider:** 1px line `#eceef4`, margin 18px 0.

### Sidebar — Connected sources
- Section label "CONNECTED SOURCES": 10.5px, #8288a0, letter-spacing .14em, margin-bottom 12px.
- List: `display:flex; flex-direction:column; gap:11px`. Each row is `space-between`:
  - Left: 6×6 dot `#10b981` + label (13px, #3a4058).
  - Right: "live" (IBM Plex Sans, 11px, #10b981).
- Rows (exact copy, in order): **Employee & Dept Directory**, **Customer Records**, **Internal Documents**, **Company Policies**, **Meeting Notes**.
- **Footer** (pushed to bottom by a `flex:1` spacer): "model · vortex-mcp-1" — IBM Plex Sans, 11px, #9096ab.

### Main — Greeting
- Heading "Hi, I'm Vera.": Space Grotesk 700, 30px, letter-spacing -0.015em, #171a2b.
- Subtext (margin-top 9px): 16px, line-height 1.55, #6a6f85 — "Ask anything about Vortex Digital's people, customers, and knowledge base."

### Main — Try asking (suggestion chips)
- Wrapper margin-top 26px. Label "TRY ASKING": 10.5px, #8288a0, letter-spacing .14em.
- Chip row (margin-top 12px): `display:flex; flex-wrap:wrap; gap:10px`.
- **Chip button:** `padding:9px 14px; border-radius:999px; border:1px solid #dfe2ee; background:#ffffff; color:#3a4058; font-size:13.5px; cursor:pointer`. **Hover:** border-color → accent, text → #171a2b.
- Chips (exact copy, in order):
  1. Who manages the Design team?
  2. Show churned customers in fintech
  3. Find the latest all-hands notes
  4. Show the remote-work policy
  5. Which customers are up for renewal this quarter?
  6. Summarize the latest project brief

### Main — Message composer (pinned bottom)
- Bar container: `border-top:1px solid #e9ebf2; padding:16px 44px 14px; background:#ffffff`. Inner capped at 780px, centered.
- Field: `display:flex; align-items:center; gap:10px; border:1px solid #d8dced; border-radius:14px; padding:10px 12px 10px 16px; background:#f6f7fb`.
- Input: `flex:1`, transparent, no border/outline, 15px, #171a2b. Placeholder "Message Vera — ask about people, customers, or docs…" at ~55% opacity.
- Send button: 38×38, `border-radius:10px`, background = accent, white "↑" glyph at 17px.

## Robot avatar (animated SVG)
48×48 viewBox, rendered at 40×40 inside the 46px circle. `color: <accent>` drives the head fill via `currentColor`.
- Antenna: vertical line `x1=24 y1=9 x2=24 y2=4.6`, stroke currentColor width 2, round cap; tip circle `cx=24 cy=3.2 r=2` fill `#5eead4`.
- Ears: two rects `x=3.6` and `x=39`, `y=21 w=5.4 h=11 rx=2.6`, fill currentColor, opacity 0.85.
- Head: rect `x=8 y=8 w=32 h=33 rx=12`, fill currentColor.
- Sheen: ellipse `cx=24 cy=16 rx=13 ry=6.5`, fill #ffffff opacity 0.15.
- Visor: rect `x=12.5 y=19 w=23 h=17.5 rx=7.5`, fill `#081026`.
- Eyes: two rects `x=18` and `x=25.8`, `y=23.5 w=4.2 h=8.6 rx=2.1`, fill `#5eead4`.

**Animations (CSS keyframes):**
- Whole head — `bob`: `translateY(0 → -1.6px → 0)`, 3.4s ease-in-out infinite.
- Each eye — `blink`: `scaleY(1)` most of the cycle, dropping to `scaleY(0.1)` at ~43% of a 4.2s ease-in-out loop; `transform-origin:center; transform-box:fill-box`.
- Eyes group — `glow`: animate `filter: drop-shadow(0 0 1px → 0 0 3.6px rgba(94,234,212,·))`, 2.6s ease-in-out infinite.
- Antenna tip — `pulse`: `opacity 0.5→1`, `scale 0.8→1.15`, 2s ease-in-out infinite; `transform-origin:center; transform-box:fill-box`.

## Interactions & Behavior
- **Suggestion chip click:** sets the composer input's value to the chip's text. It does **not** submit — it just pre-fills so the user can edit and send. (In the mock, `data-q` on each chip carries the text; a `pick` handler writes it into the input state.)
- **Composer typing:** controlled input bound to state.
- **Send button:** no submit handler wired in the mock — wire it to your send/dispatch action.
- **Chip hover:** border switches to the accent color, text darkens to #171a2b. Add the standard focus-visible ring from your design system for keyboard users.
- **Header date:** rendered from `new Date()` formatted as `{weekday short}, {month short} {day}` (e.g. "Thu, Jul 2"). Replace with real server time as needed.
- **Status pill / "live" labels / "All systems operational":** static in the mock — bind to real health/connection state in production.

## State Management
Minimal for this screen:
- `message` (string) — composer contents; set by typing and by clicking a suggestion chip.
- (Production) connection/health status per source and overall system status; current model id; current date.
- No data fetching happens on this empty state beyond loading the source list and health status. Submitting the composer should route into the chat/conversation flow (not defined in this mock).

## Design Tokens

### Colors
| Token | Hex | Usage |
|---|---|---|
| Page background | `#eceef4` | canvas behind the app frame |
| Surface / main bg | `#f6f7fb` | main column, composer field bg |
| Surface raised | `#ffffff` | header, sidebar, logo tile, chips |
| Border subtle | `#e9ebf2` | header/sidebar dividers |
| Border hairline | `#eceef4` | in-sidebar divider |
| Border input | `#d8dced` | composer field |
| Border chip | `#dfe2ee` | suggestion chips |
| Divider vertical | `#e5e8f0` | header separator |
| Text primary | `#171a2b` | headings, brand, active text |
| Text body | `#3a4058` | chip/source labels |
| Text secondary | `#565c72` | agent description |
| Text muted | `#6a6f85` | subtext, date |
| Text faint / labels | `#8288a0` | section labels, sub-brand |
| Text faint alt | `#9096ab` / `#9297ae` | footer model label |
| Success | `#10b981` | source dots, "live", status dot |
| Success text | `#0f9d6b` | status pill text |
| Success tint bg | `rgba(16,185,129,0.10)` | status pill bg |
| Success tint border | `rgba(16,185,129,0.25)` | status pill border |
| Avatar gradient | `#1c2544 → #0c1223` | robot avatar background |
| Robot visor | `#081026` | avatar face plate |
| Robot glow (cyan) | `#5eead4` | avatar eyes + antenna |
| **Accent** | `#5b6cff` (default) | send button, chip hover, robot head |

**Accent is a brand variable.** The default is indigo `#5b6cff`; the light mock is shown with the **teal `#14b8a6`** option selected. Other provided options: `#8b5cf6` (violet), `#f97316` (orange), `#ec4899` (pink). Accent is applied to: the send button background, chip hover border, and the robot head fill. Expose it as a single theme token.

### Typography
- **Display / headings / brand:** `Space Grotesk`, weights 500/600/700.
- **Body / labels / UI:** `IBM Plex Sans`, weights 400/500/600.
- Both loaded from Google Fonts. Sizes (px): 30 (greeting), 17 (agent name), 16 (subtext), 16 (brand — 16), 15 (input), 13.5 (chips, description), 13 (source labels), 12.5 (date, status), 11 (live, model), 10.5 (section labels, sub-brand).
- Notable letter-spacing: greeting -0.015em; brand/name -0.01em; uppercase labels +.12em to +.14em.

### Spacing / radius / shadow
- Section paddings: header `14px 22px`; sidebar `22px 20px`; main scroll `44px 44px 8px`; composer bar `16px 44px 14px`.
- Content max-width: `780px`, centered.
- Radii: chips/status/dots `999px`; composer field `14px`; logo tile `11px`; send button `10px`; app frame `18px`.
- Gaps: source list `11px`; chip row `10px`; header right cluster `16px`.
- App-frame shadow (presentation only): `0 34px 90px rgba(20,25,60,0.14)`.

## Assets
- `assets/vortex-logo.png` — Vortex Digital swirl logo (blue vortex on white), 200×200 PNG, no transparency. Placed in the header tile with `object-fit:cover`. User-provided; re-export at the resolution your app needs (ideally a transparent SVG if available).
- No icon library used; the only iconography is the send "↑" glyph (a text arrow — swap for your icon set) and the inline robot-head SVG.

## Files
- `Vortex Agent.dc.html` — the design component. Contains **two** variants side by side: `2a` (dark console) and `2b` (**light workspace — the target of this handoff**). Reference the `2b` / `data-side="b"` markup.
- `support.js` — runtime needed to open the `.dc.html` in a browser (not for production use).
- `assets/vortex-logo.png` — logo asset.

To preview: open `Vortex Agent.dc.html` in a browser; scroll to the `2b LIGHT WORKSPACE` frame.
