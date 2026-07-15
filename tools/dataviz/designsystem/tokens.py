"""sup computer dataviz design system — tokens.

The chart visual language matches the studio website's refined "Prof. Dr." style
(see docs/adr/0017 and docs/adr/0018), NOT a third-party design system:

  - system fonts only (no embedded webfont): a serif for titles, monospace for
    axes / ticks / data labels — the website's serif-for-reading,
    mono-for-data split.
  - stark frame: no corner radius, hairline rules, charts sit on the page's own
    surface color (white / near-black) so figures read as native to the document.
  - one sparing green accent; ink + grays carry the rest. The link-blue is a UI
    color, not a data color, so the default data hue is ink (mono). Red is kept,
    muted, for regression/error semantics.
  - the STRUCTURAL tokens (surface, text, grid, accent green) mirror the
    website's --color-* values exactly, so charts follow the reader's color
    scheme via the reports' <picture> embeds. The categorical data hues
    (amber/teal/purple/pink, ink-blue, muted red) are chart-specific — the
    website has no chart palette to mirror. When globals.css changes a
    mirrored value, change it here too (the comments name each source token).
"""

# --- Typography (system fonts; serif for titles, mono for data) -------------
FONT_SERIF = '"Charter", "Bitstream Charter", "Sitka Text", Cambria, Georgia, "Times New Roman", serif'
FONT_MONO = 'ui-monospace, "SF Mono", "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace'

# Role -> {size(px), weight, tracking(px), line(px), font, italic?}
TYPE = {
    "title":     {"size": 22, "weight": 700, "tracking": -0.3, "line": 28, "font": "serif"},
    "subtitle":  {"size": 15, "weight": 400, "tracking":  0.0, "line": 22, "font": "serif", "italic": True},
    "axisTitle": {"size": 12, "weight": 600, "tracking":  0.4, "line": 16, "font": "mono"},
    "tick":      {"size": 12, "weight": 400, "tracking":  0.0, "line": 16, "font": "mono"},
    "dataLabel": {"size": 11, "weight": 600, "tracking":  0.0, "line": 14, "font": "mono"},
    "legend":    {"size": 12, "weight": 400, "tracking":  0.0, "line": 16, "font": "mono"},
    "caption":   {"size": 12, "weight": 400, "tracking":  0.0, "line": 17, "font": "mono"},
}

# Cap-height factor (cap height to em) for tight vertical spacing.
CAP_H = 0.70

# --- Spacing ----------------------------------------------------------------
SPACE = {"XS": 8, "S": 16, "M": 24, "L": 40}

# --- Radius (stark frame — no rounding, like the website) -------------------
RADIUS = 0

# --- Themes (mirror website app/globals.css --color-* tokens) ---------------
# Hue roles:
#   blue    -> ink (the default/primary data series; mono, not literal blue)
#   green   -> the studio accent (highlight / positive)
#   red     -> muted regression/error
#   neutral -> de-emphasized gray
#   amber/teal/purple/pink -> muted extras for the rare multi-series chart
#
# The colored data hues (green, red, amber, teal, purple, pink) are matched in
# OKLCH so no series reads brighter or more vivid than its neighbors: per mode
# they share one lightness and one chroma-percentage-of-max-sRGB-chroma, both
# anchored to the green accent (which is fixed — it mirrors the website).
# Light: L 0.476, 72% of each hue's max chroma. Dark: L 0.711, 67%.
# Hue angles are shared across modes. Designed in OKLCH, emitted as hex.
LIGHT = {
    "surface":     "#ffffff",  # --color-bg
    "surfaceAlt":  "#f5f5f3",  # --color-surface
    "primary":     "#161616",  # --color-text  (titles, axis lines)
    "secondary":   "#565656",  # --color-text-muted (labels)
    "muted":       "#767676",  # --color-text-faint (captions)
    "grid":        "#e6e6e3",  # --color-border (gridlines — recede)
    "tooltipBg":   "#161616",
    "tooltipText": "#ffffff",
    "blue":    "#2b2b2b",  # ink — primary data
    "green":   "#2f6b3f",  # --color-accent — oklch(0.476 0.094 150)
    "red":     "#9c3429",  # muted regression — oklch(0.476 0.141 29)
    "neutral": "#9a9a9a",  # --color-rule-strong
    "amber":   "#6e5a2a",  # oklch(0.476 0.071 87)
    "teal":    "#2f6767",  # oklch(0.476 0.059 195)
    "purple":  "#7537aa",  # oklch(0.476 0.178 305)
    "pink":    "#953264",  # oklch(0.476 0.142 353)
}

DARK = {
    "surface":     "#0e0f10",  # --color-bg (dark)
    "surfaceAlt":  "#17181a",  # --color-surface (dark)
    "primary":     "#e9e8e4",  # --color-text (dark)
    "secondary":   "#a6a6a2",  # --color-text-muted (dark)
    "muted":       "#858582",  # --color-text-faint (dark)
    "grid":        "#2b2c2f",  # --color-border (dark)
    "tooltipBg":   "#e9e8e4",
    "tooltipText": "#0e0f10",
    "blue":    "#d0d0cb",  # ink — primary data (dark)
    "green":   "#5fb87a",  # --color-accent (dark) — oklch(0.711 0.125 152)
    "red":     "#e48375",  # muted regression (dark) — oklch(0.712 0.122 29)
    "neutral": "#494a4e",  # --color-rule-strong (dark)
    "amber":   "#bc9e57",  # oklch(0.711 0.097 87)
    "teal":    "#5fb2b2",  # oklch(0.712 0.081 195)
    "purple":  "#b58ce1",  # oklch(0.711 0.128 306)
    "pink":    "#e47aaa",  # oklch(0.712 0.141 353)
}

# Default categorical hue order (red kept last — reserved for semantic regression)
HUE_ORDER = ["blue", "green", "neutral", "amber", "teal", "purple", "pink", "red"]


def theme(mode: str = "light") -> dict:
    """Return the resolved token set for 'light' or 'dark'."""
    return DARK if mode == "dark" else LIGHT
