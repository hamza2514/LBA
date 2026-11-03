"""Landing-page artwork: palette plus pure functions that return SVG markup.

No Streamlit imports and no I/O, so every function is trivially testable.
"""
from __future__ import annotations

from html import escape

PALETTE = {
    "ink": "#0F172A",
    "muted": "#5B6478",
    "d9": "#0B1030",       # deepest denim (hero / footer)
    "d8": "#141C47",
    "d6": "#2B3A8C",
    "indigo": "#4F46E5",
    "teal": "#14B8A6",     # balanced
    "amber": "#F2A43A",    # takt line / topstitch / overloaded
    "bg": "#F3F5FA",
    "line": "#DCE1EE",
}
P = PALETTE
_SKINS = ("#E8B48F", "#C58C63", "#8D5A3B", "#D9A47A")
_OPERATORS = (("#4F46E5", "#1B1B1B"), ("#1FA89A", "#3B2A20"), ("#E0674F", "#1B1B1B"), ("#2B3A8C", "#5B3A29"))

# Illustrative line used in the explainer chart (10 stations, minutes of work per unit-batch).
SAMPLE_BEFORE = (62, 96, 48, 118, 71, 89, 41, 104, 57, 83)
SAMPLE_AFTER = (84, 83, 85, 82, 84, 85, 83, 84, 82, 85)
SAMPLE_TAKT = 85


def line_balance(loads: tuple | list) -> int:
    """Line balance % = average station load / busiest station load."""
    return round(sum(loads) / (len(loads) * max(loads)) * 100)


# ----------------------------------------------------------------------- icons
ICONS = {
    "check": '<path d="M5 12l5 5 9-10"/>',
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    "users": '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><path d="M16 5.5a3 3 0 0 1 0 5M18 14.5c2 .7 3 2.5 3 5.5"/>',
    "lines": '<path d="M3 6h18M3 12h18M3 18h18"/><circle cx="8" cy="6" r="1.6"/><circle cx="15" cy="12" r="1.6"/><circle cx="10" cy="18" r="1.6"/>',
    "absent": '<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6 1.4 0 2.6.4 3.6 1.1M16 16l5 5M21 16l-5 5"/>',
    "brain": '<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V4a3 3 0 0 0-3 0zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1"/>',
    "download": '<path d="M12 3v12M7 10l5 5 5-5M4 20h16"/>',
}


def icon(name: str, color: str = P["indigo"], size: int = 22) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')


def logo_mark(size: int = 34) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 44 44" xmlns="http://www.w3.org/2000/svg">'
            '<defs><linearGradient id="lpg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#818CF8"/>'
            '<stop offset="1" stop-color="#2DD4BF"/></linearGradient></defs>'
            '<rect x="2" y="2" width="40" height="40" rx="11" fill="url(#lpg)"/>'
            '<path d="M12 15h20M12 22h13M12 29h20" stroke="#0B1020" stroke-width="3.4" stroke-linecap="round"/>'
            '<circle cx="31" cy="22" r="3.6" fill="#0B1020"/></svg>')


# ---------------------------------------------------------------------- charts
def bar_chart(loads, takt: float, *, width=520, height=260, balanced=False) -> str:
    """Station load bars against a dashed takt line (overloaded bars in amber)."""
    n, pad_l, pad_b, pad_t = len(loads), 36, 34, 26
    plot_h, plot_w = height - pad_b - pad_t, width - pad_l - 12
    top = max(max(loads), takt) * 1.12
    y = lambda v: pad_t + plot_h * (1 - v / top)
    gap = plot_w / n
    bar_w = gap * 0.62
    out = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans, sans-serif">']
    for g in range(5):
        gy = pad_t + plot_h * g / 4
        out.append(f'<line x1="{pad_l}" x2="{width - 8}" y1="{gy:.1f}" y2="{gy:.1f}" stroke="{P["line"]}"/>')
    for i, v in enumerate(loads):
        x = pad_l + gap * i + (gap - bar_w) / 2
        fill = P["teal"] if balanced else (P["amber"] if v > takt * 1.02 else "#9AA7E8")
        out.append(f'<rect x="{x:.1f}" y="{y(v):.1f}" width="{bar_w:.1f}" height="{pad_t + plot_h - y(v):.1f}" rx="4" fill="{fill}"/>')
        out.append(f'<text x="{x + bar_w / 2:.1f}" y="{height - 14}" font-size="11" text-anchor="middle" fill="{P["muted"]}">S{i + 1}</text>')
    ty = y(takt)
    out.append(f'<line x1="{pad_l}" x2="{width - 8}" y1="{ty:.1f}" y2="{ty:.1f}" stroke="{P["amber"]}" stroke-width="2" stroke-dasharray="7 5"/>')
    out.append(f'<text x="{width - 10}" y="{ty - 7:.1f}" font-size="11.5" font-weight="600" text-anchor="end" fill="{P["amber"]}">takt time</text>')
    out.append("</svg>")
    return "".join(out)


def skill_grid() -> str:
    """Small illustrative skill matrix (employee x skill, two proficiency levels)."""
    names = ("Rahim", "Ayesha", "Bilal", "Sana", "Imran", "Zoya")
    cols = ("Back pkt", "Inseam", "W/B", "Bartack", "Press", "Label")
    levels = ((2, 0, 1, 2, 0, 0), (0, 2, 2, 0, 1, 0), (1, 2, 0, 0, 0, 2),
              (2, 1, 0, 2, 0, 1), (0, 0, 0, 1, 2, 2), (0, 2, 1, 0, 2, 0))
    fills = ("#E9ECF7", "#B3F0E8", P["teal"])
    out = ['<svg viewBox="0 0 340 250" xmlns="http://www.w3.org/2000/svg" font-family="IBM Plex Sans, sans-serif">']
    out += [f'<text x="{82 + j * 42}" y="16" font-size="9.5" fill="{P["muted"]}" text-anchor="middle">{escape(c)}</text>' for j, c in enumerate(cols)]
    for i, name in enumerate(names):
        out.append(f'<text x="4" y="{47 + i * 35}" font-size="12" fill="{P["ink"]}" font-weight="500">{escape(name)}</text>')
        out += [f'<rect x="{64 + j * 42}" y="{28 + i * 35}" width="36" height="28" rx="7" fill="{fills[levels[i][j]]}"/>' for j in range(6)]
    out.append("</svg>")
    return "".join(out)


# --------------------------------------------------------------- illustrations
def _operator(skin: str, shirt: str, hair: str) -> str:
    return (f'<rect x="26" y="150" width="34" height="62" rx="10" fill="{shirt}"/>'
            f'<circle cx="43" cy="132" r="17" fill="{skin}"/>'
            f'<path d="M26 128c2-16 30-20 34-2-8-5-20-6-34 2z" fill="{hair}"/>'
            f'<path d="M58 166c22 4 36 16 44 30" stroke="{shirt}" stroke-width="12" stroke-linecap="round" fill="none"/>'
            f'<circle cx="104" cy="198" r="6.5" fill="{skin}"/>'
            '<rect x="20" y="206" width="46" height="9" rx="4" fill="#27304F"/><rect x="38" y="214" width="8" height="42" fill="#27304F"/>')


def _station(x: int, skin: str, shirt: str, hair: str) -> str:
    return (f'<g transform="translate({x},120)">'
            '<rect x="86" y="196" width="150" height="10" rx="3" fill="#C9D0F2"/>'
            '<rect x="96" y="206" width="8" height="60" fill="#8E9AD6"/><rect x="218" y="206" width="8" height="60" fill="#8E9AD6"/>'
            '<rect x="124" y="170" width="86" height="26" rx="5" fill="#E7EAFB"/>'
            '<path d="M130 170v-22h58a10 10 0 0 1 10 10v12" fill="none" stroke="#E7EAFB" stroke-width="12" stroke-linecap="round"/>'
            '<rect x="186" y="156" width="6" height="24" fill="#8E9AD6"/>'
            f'<rect x="204" y="176" width="26" height="20" rx="3" fill="{P["amber"]}"/><rect x="210" y="170" width="14" height="6" rx="2" fill="#F7C57C"/>'
            f'{_operator(skin, shirt, hair)}</g>')


def factory_scene() -> str:
    """Four sewing stations under pendant lamps."""
    stations = "".join(_station(i * 270, _SKINS[i], *_OPERATORS[i]) for i in range(4))
    lamps = "".join(
        f'<g transform="translate({90 + i * 270},0)"><line x1="85" y1="0" x2="85" y2="74" stroke="#3A4478"/>'
        '<path d="M45 108l40-34 40 34z" fill="#27325F"/><path d="M52 108h66l22 70h-110z" fill="#F7E7B0" opacity=".10"/></g>'
        for i in range(4))
    tags = "".join(f'<rect x="{x}" width="34" height="26" rx="4"/>' for x in (0, 170, 620, 900))
    return ('<svg viewBox="0 0 1100 420" xmlns="http://www.w3.org/2000/svg">'
            '<defs><linearGradient id="lpfl" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1A2358"/>'
            '<stop offset="1" stop-color="#0E1438"/></linearGradient></defs>'
            '<rect width="1100" height="420" rx="22" fill="url(#lpfl)"/><rect y="360" width="1100" height="60" fill="#0A0F2B"/>'
            f'<line x1="30" y1="86" x2="1070" y2="86" stroke="#3A4478" stroke-width="3"/>{lamps}'
            f'<g opacity=".9">{stations}</g><g transform="translate(70,40)" fill="{P["amber"]}">{tags}</g></svg>')


def jeans(width: int = 300) -> str:
    """Front view of a pair of jeans with amber topstitching."""
    dash = f'stroke="{P["amber"]}" stroke-width="2.4" stroke-dasharray="6 5" fill="none" stroke-linecap="round"'
    loops = "".join(f'<rect x="{x}" y="22" width="9" height="40" rx="3" fill="#1C2878"/>' for x in (62, 104, 187, 229))
    return (f'<svg viewBox="0 0 300 390" width="{width}" xmlns="http://www.w3.org/2000/svg">'
            '<path d="M40 40H260L246 376H158L150 196L142 376H54Z" fill="#2F40A0"/>'
            '<path d="M150 196L142 376H54L40 40H100Z" fill="#000" opacity=".06"/>'
            f'<rect x="38" y="28" width="224" height="30" rx="4" fill="#26358F"/>{loops}'
            f'<path d="M40 62H260" {dash}/><path d="M150 62V150Q150 168 134 168" {dash}/>'
            f'<path d="M48 62Q56 128 112 138" {dash}/><path d="M252 62Q244 128 188 138" {dash}/>'
            f'<path d="M60 364H147M162 364H242" {dash}/>'
            '<circle cx="150" cy="44" r="8.5" fill="#F7C57C"/><circle cx="150" cy="44" r="4" fill="#C98A2B"/>'
            '<circle cx="52" cy="70" r="3.6" fill="#F7C57C"/><circle cx="248" cy="70" r="3.6" fill="#F7C57C"/></svg>')
