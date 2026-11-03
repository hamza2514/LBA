"""HTML for each landing-page section. Every function returns one compact HTML
string (see `compact`) ready for st.markdown(unsafe_allow_html=True)."""
from __future__ import annotations

from html import escape

from core import landing_art as art
from core.landing_art import P
from core.ui import BRAND, TAGLINE

SIGNIN_ANCHOR = "lp-signin"

# (operation, machine, SAM, employee code, employee name, basis, row colour) — illustrative sample only.
_SAMPLE_ROWS = (
    ("Back Pocket Attach-2 (Mitered SN)", "SNLS", "0.72", "E-10431", "Aamir Shah", "Skill", "#D9EAD3"),
    ("Back Pocket Top Stitch-(Even Gauge)", "SNLS", "0.50", "E-10431", "Aamir Shah", "Skill", "#D9EAD3"),
    ("Inseam Safety", "5T O/L", "0.34", "E-10877", "Nadia Khan", "Skill", "#CFE2F3"),
    ("Outseam Safety (2 joints)", "5T O/L", "0.42", "E-10877", "Nadia Khan", "Partial skill", "#CFE2F3"),
    ("Waist Band Attach-1Pc (Straight)", "W/B", "0.45", "E-11204", "Kamran Ali", "Skill", "#FFF2CC"),
    ("Bartack Loops (10)", "Bartack m/c", "0.66", "E-10952", "Sobia Iqbal", "Related skill", "#FFFFFF"),
    ("Press Flap 2", "Press", "0.47", "E-11390", "Hira Malik", "Manual", "#FFFFFF"),
)
_PILL = {"Manual": ("#FEF3C7", "#B45309")}
_PILL_DEFAULT = ("#DBEAFE", "#1D4ED8")

_CAPABILITIES = (
    ("file", "Reads files as they come", "Excel, CSV and ERP-style PDF bulletins, with section headings and totals handled."),
    ("users", "Staffs by evidence", "Proven skill first, then partial and related skill, then machine experience. Each row shows its basis."),
    ("lines", "One line or many", "Run different styles per line, with their own targets, and share operators across lines where it makes sense."),
    ("absent", "Absentee ready", "Re-balance in minutes using only the people present today."),
    ("brain", "Gets sharper with use", "Manual assignments and operation sequences become knowledge the next layout builds on."),
    ("download", "Straight to Excel", "Colour-coded layouts that share one operator per colour, ready for the floor."),
)

_NAV_LINKS = (("Why balancing", "lp-why"), ("How it works", "lp-how"), ("Capabilities", "lp-feat"))


def compact(html: str) -> str:
    """Strips indentation and blank lines: Markdown treats 4-space-indented or
    blank-line-separated HTML as code, which would break the layout."""
    return " ".join(line.strip() for line in html.splitlines() if line.strip())


def _wrap(css_class: str, body: str) -> str:
    return compact(f'<div class="lp {css_class}">{body}</div>')


def _nav_links() -> str:
    return "".join(f'<a href="#{anchor}">{label}</a>' for label, anchor in _NAV_LINKS)


# ------------------------------------------------------------------------ hero
def nav() -> str:
    return _wrap("lp-dark", f"""
        <div class="lp-nav"><div class="lp-brand">{art.logo_mark()}{BRAND}</div>
        <div class="lp-links">{_nav_links()}<a href="#lp-contact">Contact</a></div>
        <a class="lp-nav-btn" href="#{SIGNIN_ANCHOR}">Sign in</a></div>""")


def hero_copy() -> str:
    ticks = ("Works with the OB and skill files you already have",
             "Single line, multiple lines, or today's attendance only",
             "Learns from every correction your team makes")
    items = "".join(f'<li><i>{art.icon("check", P["teal"], 14)}</i>{t}</li>' for t in ticks)
    return _wrap("lp-dark lp-hero-copy", f"""
        <h1>Put the right operator on every operation.</h1>
        <p class="lp-lead">{BRAND} reads your Operation Breakdown and skill matrix, balances the line against takt time,
        and staffs every station with someone who can actually run it.</p><ul class="lp-ticks">{items}</ul>""")


def scene() -> str:
    return _wrap("lp-scene", art.factory_scene())


# ------------------------------------------------------------------- explainer
def why() -> str:
    before, after = art.SAMPLE_BEFORE, art.SAMPLE_AFTER
    return _wrap("", f"""
        <div id="lp-why" class="lp-why-grid"><div>
          <h2>A line is only as fast as its busiest station.</h2>
          <p class="lp-body">When one operation holds 118 minutes of work and the next holds 41, bundles pile up in front of
          the first and the second waits for them. Line balancing spreads the work so every station carries a load close to
          takt time, and the whole line runs at the pace you planned.</p>
          <p class="lp-body">The hard part is people. Moving work only helps if the person at that station can run that machine,
          so every move has to respect who is skilled, who is present and which section of the line they belong to.</p>
          <div class="lp-formula">Manpower = (Target × SAM) ÷ (Available minutes × Efficiency)
          <small>The same arithmetic your industrial engineers use, applied to every operation automatically.</small></div></div>
        <div class="lp-compare"><div class="lp-cmp-row">
          <div class="lp-cmp"><h3>Before <em class="a">{art.line_balance(before)}%</em></h3>
            <small>Four stations over takt, four badly under-loaded</small>
            {art.bar_chart(before, art.SAMPLE_TAKT, width=270, height=250)}</div>
          <div class="lp-cmp"><h3>After <em class="b">{art.line_balance(after)}%</em></h3>
            <small>Work redistributed, every station near takt</small>
            {art.bar_chart(after, art.SAMPLE_TAKT, width=270, height=250, balanced=True)}</div></div>
          <p class="lp-note">Illustrative 10-station line. Balance = average station load ÷ busiest station load.</p></div></div>""")


def how() -> str:
    pill = lambda text, bg, fg: f'<span class="lp-pill" style="background:{bg};color:{fg};font-size:.82rem">{text}</span>'
    steps = (
        ("Upload", "Drop in an Operation Breakdown as Excel, CSV or PDF. Line sections are detected for you.", art.jeans(92), ""),
        ("Match skills", "Operations are matched to skill groups and to what each operator has proven they can do.", art.skill_grid(), "padding:12px"),
        ("Balance", "Under-used and overloaded work is pooled into full days, within the same section only.",
         art.bar_chart(art.SAMPLE_AFTER, art.SAMPLE_TAKT, width=250, height=150, balanced=True), "padding:8px 10px"),
        ("Review and learn", "Change any assignment by hand. Save the layout and the next run starts from your decisions.",
         f'{pill("Skill", *_PILL_DEFAULT)}{pill("Manual, learned", *_PILL["Manual"])}'
         f'<span style="color:{P["muted"]};font-size:.82rem">Used automatically from the next run</span>',
         "flex-direction:column;gap:8px"),
    )
    cells = "".join(
        f'<div class="lp-step"><div class="lp-num">{i}</div><h3>{title}</h3><p>{text}</p>'
        f'<div class="lp-visual" style="{style}">{visual}</div></div>'
        for i, (title, text, visual, style) in enumerate(steps, start=1))
    return _wrap("", f'<h2 id="lp-how" style="max-width:640px">From raw files to a staffed line in four steps.</h2><div class="lp-steps">{cells}</div>')


def _sample_table() -> str:
    rows = ""
    for op, machine, sam, code, name, basis, colour in _SAMPLE_ROWS:
        bg, fg = _PILL.get(basis, _PILL_DEFAULT)
        rows += (f'<tr style="background:{colour}"><td>{escape(op)}</td><td class="m">{machine}</td><td class="n">{sam}</td>'
                 f'<td class="c">{code}</td><td>{escape(name)}</td><td><span class="lp-pill" style="background:{bg};color:{fg}">{basis}</span></td></tr>')
    return ('<table class="lp-mock"><thead><tr><th>Operation</th><th>Machine</th><th class="n">SAM</th><th>Code</th>'
            f'<th>Employee</th><th>Assigned by</th></tr></thead><tbody>{rows}</tbody></table>')


def features() -> str:
    caps = "".join(
        f'<div class="lp-cap"><div class="ic">{art.icon(name)}</div><div><h3>{title}</h3><p>{text}</p></div></div>'
        for name, title, text in _CAPABILITIES)
    stats = "".join(f"<div>{k}<b{extra}>{v}</b></div>" for k, v, extra in
                    (("Operations", "56", ""), ("Operators used", "41", ""), ("On 2+ rows", "9", ""),
                     ("Unassigned", "0", ' style="color:#B91C1C"')))
    return _wrap("", f"""
        <h2 id="lp-feat">Built for the way a sewing floor really works.</h2>
        <div class="lp-feat-grid"><div class="lp-shot">
          <div class="lp-shot-bar"><i></i><i></i><i></i><span>Layout balancing · Style 5-Pocket Basic (sample)</span></div>
          <div class="lp-shot-stats">{stats}</div>{_sample_table()}</div><div>{caps}</div></div>""")


# ----------------------------------------------------------------- closing area
def band(contact_email: str | None) -> str:
    request = f'<a class="lp-cta p" href="mailto:{escape(contact_email)}">Request access</a>' if contact_email else ""
    primary = "s" if request else "p"
    return _wrap("lp-dark lp-band", f"""
        <div id="lp-contact" class="lp-band-grid"><div class="lp-jeans">{art.jeans(250)}</div><div>
        <h2>Spend your shift running the line, not rearranging it.</h2>
        <p>Bring one style, one skill file and one list of employees. You will see a staffed layout before your next meeting.</p>
        <div class="lp-cta-row">{request}<a class="lp-cta {primary}" href="#{SIGNIN_ANCHOR}">Sign in</a></div></div></div>""")


def footer() -> str:
    return _wrap("", f"""
        <div class="lp-foot"><div class="lp-brand">{art.logo_mark()}{BRAND}</div>
        <nav>{_nav_links()}</nav><span>© 2026 {BRAND}. {TAGLINE}</span></div>""")
