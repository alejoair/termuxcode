# UI Color Specification — OLED Optimized

## Principle

> **Pixel off = pixel perfect.** Color lives in minimal accents (side borders, labels), never in large fills. This maximizes battery life and minimizes nighttime eye strain.

## Chromatic Palette by Message Type

Each type gets a color from a **distinct zone of the spectrum** for instant identification via peripheral scanning:

| Type | Color | Hex | Name | Personality |
|------|-------|-----|------|-------------|
| User | ![#5b93f5](https://via.placeholder.com/15/5b93f5/5b93f5) | `#5b93f5` | Sapphire Blue | "My voice", outward communication |
| Assistant | neutral | — | None | Distinguished by layout (left-aligned, no border) |
| Thinking | ![#9b8ec4](https://via.placeholder.com/15/9b8ec4/9b8ec4) | `#9b8ec4` | Lavender | Ethereal, internal, dreamy |
| Tool-call | ![#2cc5c5](https://via.placeholder.com/15/2cc5c5/2cc5c5) | `#2cc5c5` | Teal | Technical, active, mechanical |
| Tool-result | ![#4ade80](https://via.placeholder.com/15/4ade80/4ade80) | `#4ade80` | Emerald | Output, result, confirmation |
| System | ![#e8b931](https://via.placeholder.com/15/e8b931/e8b931) | `#e8b931` | Gold | Meta, status, informational |

## Application Rule: Side Border + Tinted Text

Instead of colored backgrounds (which illuminate pixels), each type uses:

| Element | Treatment | Pixel cost |
|---------|-----------|------------|
| **Left border** | 2px solid with type color at ~40% opacity | Minimal |
| **Bubble background** | `transparent` or `rgba(X, X, X, 0.03)` — barely perceptible | Zero |
| **Label** ("Tu", "Claude") | Type color at 50% opacity | Minimal |
| **Content text** | `#d4d4d8` neutral for all types (reading) | Efficient |
| **Tool headers/names** | Type color at 70% opacity | Minimal |

### Before vs After

| Type | Before (colored fill) | After (border + tint) |
|------|----------------------|------------------------|
| **User** | Transparent + blue glow (box-shadow illuminates large area) | 1.5px blue border, no glow, no shadow |
| **Assistant** | `rgba(255,255,255,0.08)` — diffuse white fill | Transparent, no border — distinguished by position |
| **Thinking** | Transparent + gray 55% text (nearly invisible) | Lavender left border + lavender-tinted text at 60% |
| **Tool-call** | `rgba(139,92,246,0.12)` purple fill + purple border | Teal left border + teal-tinted header, bg at 0.03 |
| **Tool-result** | Only green left border at 25% (very subtle) | Emerald left border at 35% + emerald label |
| **System** | `rgba(251,191,36,0.08)` amber fill | Centered, no background, pure gold text |

## Text Hierarchy

```css
--text-primary:    #d4d4d8                       /* Main content — comfortable reading, no fatigue */
--text-secondary:  rgba(212, 212, 216, 0.70)     /* Descriptions, metadata */
--text-muted:      rgba(212, 212, 216, 0.45)     /* Timestamps, hints */
--text-faint:      rgba(212, 212, 216, 0.25)     /* Secondary labels */
```

`#d4d4d8` (zinc-300) has a contrast ratio of **11.4:1** on black — well above AA minimum (4.5:1) without the harshness of pure white (`#fff` = 21:1, too bright at night).

## Background Layers

```css
--bg-body:       #000000       /* Pixels completely OFF */
--bg-surface:    #0a0a0a       /* Subtle elevation (nearly off on OLED) */
--bg-bubble:     transparent   /* Side border does the work */
--bg-toolbar:    #000000       /* No rgba(0,0,0,0.9), direct black */
--bg-code:       #0a0a0a       /* Code block, subtle lift */
```

## Visual Preview (ASCII)

```
#000000 pure black background

                        ┌─────────────────────┐
          "Tu" · #5b93f5 │ Haz esto y aquello   │  ← User: blue border
                        └─────────────────────┘

   "Claude" · zinc     │
                        │ Aqui va la respuesta del
                        │ asistente con markdown...    ← Assistant: no border

┃ #9b8ec4 lavender     │ *pienso que la mejor forma*  ← Thinking: lavender left border
                        │ *seria iterar sobre los...*

┃ #2cc5c5 teal         │ > Bash                       ← Tool-call: teal left border
  ┃ #4ade80 green      │   resultado del comando...    ← Tool-result: green left border

               ─── · "Conectado al servidor" · ───     ← System: gold text, centered
```

## Advantages

1. **Battery**: Eliminating `box-shadow` (glow) from user messages and reducing rgba fills saves illuminated pixels
2. **Quick scanning**: Each type = a distinct spectrum color, recognizable peripherally
3. **Night comfort**: `#d4d4d8` text + desaturated accents = less fatigue than whites/neons
4. **Consistency**: One mechanism (left border + tint) for all types

## Message Type Catalog

### Inline Messages (in chat)

| # | Type | Alignment | Accent Color | Relative Size | Content |
|---|------|-----------|-------------|---------------|---------|
| 1 | **User** | Right | Sapphire `#5b93f5` | Base (`0.9rem`) | Plain text |
| 2 | **Assistant** | Left | Neutral (none) | Base + markdown | Rich text |
| 3 | **Thinking** | Left | Lavender `#9b8ec4` | Smaller (`0.85rem`) + italic | Internal reasoning |
| 4 | **Tool-call** | Left (indented) | Teal `#2cc5c5` | Small (`0.75rem`) mono | Accordion: name + input |
| 5 | **Tool-result** | Left (more indented) | Emerald `#4ade80` | Small (`0.75rem`) mono | Tool output |
| 6 | **System** | Centered | Gold `#e8b931` | Small (`0.75rem`) | Status/errors |

### Special Inline Messages

| # | Type | Rendered As | Note |
|---|------|-------------|------|
| 7 | **AskUserQuestion** | Assistant bubble + `.chat-question` inner div | Blue 18% bg, 3px blue left border, option list |
| 8 | **Typing Indicator** | 3 bouncing dots + "Claude" label | Transient, appears/disappears |

### Modals (overlays, not in chat)

| # | Type | Purpose | Button Colors |
|---|------|---------|---------------|
| 9 | **Tool Approval** | Approve/deny tool execution | Red (deny) / Green (allow) |
| 10 | **File View / Plan** | Review and approve a plan | Red (reject) / Green (approve) |
| 11 | **AskUserQuestion (modal)** | User option selection | Gray (cancel) / Gradient (respond) |

### Meta Messages (invisible, state control)

`result`, `session_id`, `cwd` — not rendered, control internal state.

## Font Scaling

Base font size is controlled by a single value in `variables.css`:

```css
:root {
    font-size: 24px;  /* 16px = original, 20px = 1.25x, 24px = 1.5x */
}
```

All font sizes use `rem` units so changing this value scales the entire UI proportionally.
