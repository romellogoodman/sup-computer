"""Vercel Geist dataviz design system — tokens.

Our own chart design system, derived from Vercel Geist (Vercel's design system):
  https://vercel.com/design.md       (light)
  https://vercel.com/design.dark.md  (dark)

This is NOT Anthropic's dataviz system. We borrow the *engineering* approach
(self-contained HTML + inline SVG, nice-axis ticks, a vertical layout stack)
but every visual token here — color, type, spacing, radius — comes from
Vercel Geist.

Distinguishing marks vs. the Anthropic system:
  - Geist Sans, not Anthropic Sans
  - headings at weight 600 with negative tracking, not 700
  - 6px corner radius (Vercel Geist `small`), not 4px
  - Vercel Geist accent ramps (blue #006bff, green, red #fc0035, amber, …)
  - semantic color: success = green, regression/error = red
"""

# --- Typography -------------------------------------------------------------
# Vercel Geist (Geist Sans) variable font, embedded as base64 at render time.
FONT_FAMILY = '"Geist", "Geist Sans", system-ui, -apple-system, sans-serif'

# Role -> {size(px), weight, tracking(px letter-spacing), line(px)}
# Mapped from Vercel Geist's Heading / Copy / Label / Button scales.
TYPE = {
    "title":     {"size": 24, "weight": 600, "tracking": -0.96, "line": 32},  # Heading-24
    "subtitle":  {"size": 16, "weight": 400, "tracking": -0.32, "line": 24},  # Copy-16
    "axisTitle": {"size": 13, "weight": 500, "tracking":  0.0,  "line": 16},  # Button-13
    "tick":      {"size": 13, "weight": 400, "tracking":  0.0,  "line": 16},  # Label-13
    "dataLabel": {"size": 12, "weight": 500, "tracking":  0.0,  "line": 16},  # Button-12
    "legend":    {"size": 13, "weight": 400, "tracking":  0.0,  "line": 16},  # Label-13
    "caption":   {"size": 13, "weight": 400, "tracking":  0.0,  "line": 18},  # Copy-13
}

# Cap-height factor for Geist Sans (cap height to em). Used for tight vertical spacing.
CAP_H = 0.70

# --- Spacing (Vercel Geist scale: 4 8 12 16 24 32 40 64 96) -----------------
SPACE = {"XS": 8, "S": 16, "M": 24, "L": 40}

# --- Radius (Vercel Geist `small`) ------------------------------------------
RADIUS = 6

# --- Themes -----------------------------------------------------------------
# Grayscale + accent roles resolved per mode.
LIGHT = {
    "surface":    "#ffffff",  # background-100
    "surfaceAlt": "#fafafa",  # background-200
    "primary":    "#171717",  # gray-1000  (titles, axis lines)
    "secondary":  "#666666",  # labels (between gray-700/900)
    "muted":      "#8f8f8f",  # gray-700   (captions)
    "grid":       "#ebebeb",  # gray-200   (gridlines)
    "tooltipBg":  "#171717",
    "tooltipText": "#ffffff",
    # accent hues — Vercel Geist 700-level
    "blue":   "#006bff",
    "amber":  "#ffae00",
    "teal":   "#00ac96",
    "purple": "#a000f8",
    "pink":   "#f22782",
    "green":  "#28a948",  # success
    "red":    "#fc0035",  # regression / error
    "neutral": "#c9c9c9", # gray-500 — de-emphasized bars
}

DARK = {
    "surface":    "#000000",  # background-100
    "surfaceAlt": "#1a1a1a",  # gray-100
    "primary":    "#ededed",  # gray-1000
    "secondary":  "#a0a0a0",  # gray-900
    "muted":      "#8f8f8f",  # gray-700
    "grid":       "#2e2e2e",  # gray-400
    "tooltipBg":  "#ededed",
    "tooltipText": "#000000",
    "blue":   "#0090ff",
    "amber":  "#ffae00",
    "teal":   "#00ac96",
    "purple": "#bd5fff",
    "pink":   "#f97ea7",
    "green":  "#4ce15e",  # success
    "red":    "#f32e40",  # regression / error
    "neutral": "#454545", # gray-500 dark
}

# Default categorical hue order (red kept last — reserved for semantic regression)
HUE_ORDER = ["blue", "amber", "teal", "purple", "pink", "green", "red"]


def theme(mode: str = "light") -> dict:
    """Return the resolved token set for 'light' or 'dark'."""
    return DARK if mode == "dark" else LIGHT
