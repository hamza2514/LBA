"""Stylesheet for the landing page. Scoped to `.lp*` classes and the
`st-key-lp_*` containers so it never leaks into the signed-in app."""
from __future__ import annotations

from core.landing_art import PALETTE

_FONTS = ("@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800"
          "&family=IBM+Plex+Sans:wght@400;500;600&display=swap');")

_VARS = ":root{" + "".join(f"--lp-{k}:{v};" for k, v in PALETTE.items()) + "}"

_PAGE = """
[data-testid="stMainBlockContainer"], .block-container { max-width:none !important; padding:0 !important; }
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] { gap:0 !important; }
[data-testid="stHeader"] { background:transparent; }
.st-key-lp_hero, .st-key-lp_why, .st-key-lp_how, .st-key-lp_feat, .st-key-lp_band, .st-key-lp_footer {
  --lp-pad:max(24px, calc((100vw - 1200px) / 2)); padding-left:var(--lp-pad); padding-right:var(--lp-pad); }
.st-key-lp_hero [data-testid="stVerticalBlock"] { gap:0; }
.st-key-lp_hero { background:radial-gradient(1100px 520px at 85% -10%, #26357F 0%, transparent 60%), var(--lp-d9); padding-top:0; padding-bottom:0; }
.st-key-lp_why { background:var(--lp-bg); padding-top:170px; padding-bottom:104px; }
.st-key-lp_how { background:#fff; border-top:1px solid var(--lp-line); border-bottom:1px solid var(--lp-line); padding-top:104px; padding-bottom:104px; }
.st-key-lp_feat { background:var(--lp-bg); padding-top:104px; padding-bottom:104px; }
.st-key-lp_band { background:var(--lp-d9); }
.st-key-lp_footer { background:#070A22; padding-top:44px; padding-bottom:36px; }
"""

_TYPE = """
div.lp, div.lp * { font-family:"IBM Plex Sans", sans-serif; }
div.lp h1, div.lp h2, div.lp h3, div.lp .lp-brand, div.lp .lp-display { font-family:"Bricolage Grotesque", sans-serif; letter-spacing:-.025em; line-height:1.08; }
div.lp h1, div.lp h2, div.lp h3, div.lp p, div.lp ul, div.lp li { margin:0 !important; padding:0 !important; color:inherit; }
div.lp ul { list-style:none; }
div.lp a { color:inherit !important; text-decoration:none !important; }
div.lp { color:var(--lp-ink); font-size:16px; line-height:1.6; }
div.lp.lp-dark { color:#fff; }
div.lp h1 { font-size:4.1rem; font-weight:800; }
div.lp h2 { font-size:2.9rem; font-weight:700; }
div.lp h3 { font-size:1.3rem; font-weight:700; }
"""

_NAV_HERO = """
.lp-nav { display:flex; align-items:center; justify-content:space-between; height:78px; }
.lp-brand { display:flex; align-items:center; gap:11px; font-weight:700; font-size:1.45rem; }
.lp-links { display:flex; gap:34px; color:#B8C1EA; font-size:.96rem; }
.lp-nav-btn { border:1.5px solid #4A58B8; padding:9px 22px; border-radius:10px; font-weight:500; font-size:.95rem; }
.lp-hero-copy { padding:46px 0 24px; }
div.lp .lp-lead { margin-top:26px !important; font-size:1.2rem; color:#C3CBF0; max-width:540px; line-height:1.55; }
div.lp .lp-ticks { margin-top:30px !important; display:grid; gap:12px; color:#E4E8FB; font-size:1.02rem; }
.lp-ticks li { display:flex; gap:12px; align-items:center; }
.lp-ticks i { width:22px; height:22px; border-radius:50%; background:rgba(20,184,166,.18); display:inline-flex; align-items:center; justify-content:center; flex:none; }
.lp-scene { margin-top:40px; transform:translateY(96px); position:relative; z-index:5; box-shadow:0 30px 60px -28px rgba(0,0,0,.7); border-radius:22px; overflow:hidden; line-height:0; }
.lp-scene svg { width:100%; height:auto; }
"""

_CARD = """
.st-key-lp_card { background:#fff; border-radius:20px; padding:36px 36px 26px; box-shadow:0 30px 60px -20px rgba(0,0,0,.55); position:relative; margin-top:46px; }
.st-key-lp_card::before { content:""; position:absolute; inset:8px; border:1.5px dashed rgba(242,164,58,.7); border-radius:14px; pointer-events:none; }
.st-key-lp_card [data-testid="stVerticalBlock"] { gap:.25rem; }
.st-key-lp_card .lp-card-title { font-family:"Bricolage Grotesque", sans-serif; font-size:1.9rem !important; line-height:1.15; font-weight:700; letter-spacing:-.025em; color:var(--lp-ink); margin:0; }
.st-key-lp_card .lp-card-sub { color:var(--lp-muted); margin:6px 0 14px; font-size:.96rem; }
.st-key-lp_card label p { font-weight:600 !important; font-size:.88rem !important; color:var(--lp-ink) !important; }
.st-key-lp_card [data-baseweb="input"] { border-radius:11px; border:1.5px solid var(--lp-line); background:#FAFBFE; min-height:50px; }
.st-key-lp_card [data-baseweb="input"]:focus-within { border-color:var(--lp-indigo); box-shadow:0 0 0 4px rgba(79,70,229,.12); background:#fff; }
.st-key-lp_card [data-baseweb="input"] > div { background:transparent; }
.st-key-lp_card input { font-size:1rem; }
.st-key-lp_card [data-testid="stFormSubmitButton"] button { height:52px; width:100%; border-radius:12px; font-weight:600; font-size:1.03rem; margin-top:10px;
  background:linear-gradient(135deg, var(--lp-indigo), #6A63F5); color:#fff; border:0; box-shadow:0 10px 22px -8px rgba(79,70,229,.7); }
.st-key-lp_card .lp-card-foot { margin-top:14px; font-size:.88rem; color:var(--lp-muted); text-align:center; }
"""

_SECTIONS = """
.lp-why-grid { display:grid; grid-template-columns:1fr 1.05fr; gap:80px; align-items:center; }
div.lp .lp-body { color:#3B4458; margin-top:20px !important; font-size:1.08rem; max-width:520px; }
.lp-formula { margin-top:28px; border-left:4px solid var(--lp-amber); padding:6px 0 6px 20px; font-weight:500; font-size:1.05rem; }
.lp-formula small { display:block; color:var(--lp-muted); font-weight:400; font-size:.9rem; margin-top:4px; }
.lp-compare { background:#fff; border:1px solid var(--lp-line); border-radius:20px; padding:28px 30px 22px; }
.lp-cmp-row { display:grid; grid-template-columns:1fr 1fr; gap:26px; }
div.lp .lp-cmp h3 { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px !important; font-size:1.15rem; }
.lp-cmp h3 em { font-style:normal; font-size:1.7rem; }
.lp-cmp .a { color:#C77A12; } .lp-cmp .b { color:#0F9488; }
.lp-cmp small { display:block; color:var(--lp-muted); font-size:.84rem; line-height:1.4; min-height:2.4em; }
div.lp .lp-note { margin-top:14px !important; color:var(--lp-muted); font-size:.84rem; border-top:2px dashed #E7DCC6; padding-top:12px !important; }

.lp-steps { display:grid; grid-template-columns:repeat(4,1fr); margin-top:56px; position:relative; }
.lp-steps::before { content:""; position:absolute; left:5%; right:5%; top:19px; border-top:2px dashed var(--lp-amber); }
.lp-step { padding-right:30px; }
.lp-num { width:40px; height:40px; border-radius:50%; background:var(--lp-d9); color:#fff; font-family:"Bricolage Grotesque", sans-serif; font-weight:700;
  display:flex; align-items:center; justify-content:center; position:relative; z-index:1; box-shadow:0 0 0 7px #fff; }
div.lp .lp-step h3 { margin-top:22px !important; }
div.lp .lp-step p { color:#4A5368; margin-top:9px !important; font-size:.98rem; }
.lp-visual { margin-top:22px; height:160px; border-radius:14px; background:var(--lp-bg); border:1px solid var(--lp-line); display:flex; align-items:center; justify-content:center; overflow:hidden; }
.lp-visual svg { max-width:100%; max-height:100%; }

.lp-feat-grid { display:grid; grid-template-columns:1.25fr 1fr; gap:64px; align-items:start; margin-top:52px; }
.lp-shot { background:#fff; border:1px solid var(--lp-line); border-radius:18px; overflow:hidden; box-shadow:0 24px 50px -30px rgba(20,28,71,.45); }
.lp-shot-bar { display:flex; align-items:center; gap:7px; padding:13px 16px; border-bottom:1px solid var(--lp-line); background:#F8F9FD; color:var(--lp-muted); font-size:.84rem; }
.lp-shot-bar i { width:10px; height:10px; border-radius:50%; background:#D3D9E8; }
.lp-shot-bar span { margin-left:12px; }
.lp-shot-stats { display:flex; gap:30px; padding:16px 22px; border-bottom:1px solid var(--lp-line); font-size:.85rem; color:var(--lp-muted); }
.lp-shot-stats b { display:block; color:var(--lp-ink); font-size:1.35rem; font-family:"Bricolage Grotesque", sans-serif; }
table.lp-mock { width:100%; border-collapse:collapse; font-size:.86rem; margin:0; border:0; }
.lp-mock th { background:var(--lp-d9); color:#fff; text-align:left; padding:10px 12px; font-weight:600; font-size:.8rem; border:0; }
.lp-mock td { padding:9px 12px; border:0; border-bottom:1px solid #E6EAF3; vertical-align:middle; }
.lp-mock td:nth-child(5) { white-space:nowrap; }
.lp-mock .m { color:var(--lp-muted); white-space:nowrap; } .lp-mock .n { text-align:right; } .lp-mock .c { font-weight:600; white-space:nowrap; }
.lp-pill { padding:2px 10px; border-radius:99px; font-size:.76rem; font-weight:600; white-space:nowrap; }
.lp-cap { display:grid; grid-template-columns:44px 1fr; gap:16px; padding:22px 0; border-bottom:2px dashed #E1D3B6; }
.lp-cap:first-child { padding-top:4px; } .lp-cap:last-child { border-bottom:0; }
.lp-cap .ic { width:44px; height:44px; border-radius:12px; background:#E9ECFC; display:flex; align-items:center; justify-content:center; }
.lp-cap h3 { font-size:1.2rem; }
div.lp .lp-cap p { color:#4A5368; margin-top:5px !important; font-size:.96rem; }

.lp-band-grid { display:grid; grid-template-columns:300px 1fr; gap:70px; align-items:center; padding:84px 0; }
div.lp.lp-band h2 { font-size:2.7rem; max-width:640px; }
div.lp.lp-band p { color:#BAC3EC; margin-top:18px !important; font-size:1.08rem; max-width:560px; }
.lp-cta-row { display:flex; gap:14px; margin-top:32px; flex-wrap:wrap; }
.lp-cta { height:52px; padding:0 30px; border-radius:12px; display:flex; align-items:center; font-weight:600; }
.lp-cta.p { background:#fff; color:var(--lp-d9) !important; } .lp-cta.s { border:1.5px solid #4A58B8; }
div.lp .lp-cta.p { color:var(--lp-d9) !important; }
.lp-jeans { display:flex; justify-content:center; position:relative; }
.lp-jeans::after { content:""; position:absolute; inset:-14px 22px; border:1.5px dashed rgba(242,164,58,.5); border-radius:150px 150px 24px 24px; }
.lp-foot { display:flex; justify-content:space-between; align-items:center; gap:24px; flex-wrap:wrap; color:#8F99CC; font-size:.92rem; }
.lp-foot .lp-brand { font-size:1.2rem; color:#fff; }
.lp-foot nav { display:flex; gap:28px; }
"""

_RESPONSIVE = """
@media (max-width:980px) {
  div.lp h1 { font-size:2.6rem; } div.lp h2 { font-size:2rem; }
  .lp-links { display:none; }
  .lp-why-grid, .lp-feat-grid, .lp-band-grid { grid-template-columns:1fr; gap:36px; }
  .lp-steps { grid-template-columns:1fr 1fr; row-gap:40px; } .lp-steps::before { display:none; }
  .lp-jeans { display:none; }
  .lp-scene { transform:translateY(40px); }
  .st-key-lp_why { padding-top:100px; }
  .st-key-lp_card { margin-top:8px; padding:28px 22px 20px; }
}
"""

CSS = _FONTS + _VARS + _PAGE + _TYPE + _NAV_HERO + _CARD + _SECTIONS + _RESPONSIVE
