"""Static HTML dashboard for a project capsule.

Self-contained (no CDN, works offline), respects prefers-reduced-motion,
and follows an "instrument panel" visual direction: deep slate ground,
avionics-amber signal color reserved for the entropy tape and blockers,
phosphor-cyan reserved for evidence chips. Evidence chips are the
signature element — every material line wears its ledger ids.
"""

from __future__ import annotations

import html
from pathlib import Path

from . import db, ledger

CSS = """
:root{
  --ground:#11151c; --panel:#171d27; --line:#2a3342;
  --ink:#dde3ec; --ink-dim:#8b95a7;
  --amber:#e8a33d; --cyan:#5fd3c4; --ok:#7fb069; --bad:#d1604f;
  --display:'Avenir Next','Segoe UI',system-ui,sans-serif;
  --mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace;
}
*{box-sizing:border-box;margin:0}
body{background:var(--ground);color:var(--ink);font:15px/1.55 var(--display);
     max-width:960px;margin:0 auto;padding:40px 24px 80px}
header{display:flex;justify-content:space-between;align-items:baseline;
       border-bottom:1px solid var(--line);padding-bottom:16px;margin-bottom:28px}
h1{font-size:22px;font-weight:600;letter-spacing:.04em}
h1 .brand{color:var(--ink-dim);font-weight:400}
.stamp{font:12px var(--mono);color:var(--ink-dim)}
.demo-banner{background:#3a2f14;border:1px solid var(--amber);color:var(--amber);
  padding:8px 14px;border-radius:4px;font:12px var(--mono);margin-bottom:24px}
section{background:var(--panel);border:1px solid var(--line);border-radius:6px;
        padding:18px 20px;margin-bottom:16px}
section h2{font-size:11px;letter-spacing:.18em;text-transform:uppercase;
           color:var(--ink-dim);margin-bottom:12px}
li{list-style:none;padding:6px 0;border-top:1px dotted var(--line)}
li:first-of-type{border-top:none}
.ev{font:11px var(--mono);color:var(--cyan);border:1px solid var(--cyan);
    border-radius:3px;padding:0 5px;margin-left:6px;opacity:.85;cursor:default}
.badge{font:11px var(--mono);color:var(--ink-dim);margin-left:6px}
.rationale{color:var(--ink-dim);font-size:13px;padding-left:14px}
.blocker{color:var(--amber)}
.next{border-left:3px solid var(--ok);padding-left:14px}
.next code{font:13px var(--mono);color:var(--cyan)}
/* entropy tape — the instrument */
.tape{position:relative;height:14px;border:1px solid var(--line);border-radius:3px;
      background:repeating-linear-gradient(90deg,transparent 0 24px,var(--line) 24px 25px)}
.tape-fill{height:100%;background:linear-gradient(90deg,var(--ok),var(--amber) 60%,var(--bad));
           border-radius:2px;transition:width .8s ease}
@media (prefers-reduced-motion: reduce){.tape-fill{transition:none}}
.factors{font:12px var(--mono);color:var(--ink-dim);margin-top:10px;width:100%}
.factors td{padding:2px 12px 2px 0}
details.raw{margin-top:24px}
details.raw pre{font:11px var(--mono);color:var(--ink-dim);overflow-x:auto;
  background:var(--panel);border:1px solid var(--line);padding:12px;border-radius:6px}
"""


def _e(s) -> str:
    return html.escape(str(s or ""))


def _item_li(it, cls=""):
    icon = {"observed": "●", "inferred": "○", "user_corrected": "◆"}.get(
        it.get("inference", "observed"), "●")
    evs = "".join(f'<span class="ev" title="ledger evidence id">{_e(i)}</span>'
                  for i in (it.get("evidence_ids") or [])[:4])
    extra = ""
    if it.get("rationale"):
        extra += f'<div class="rationale">why: {_e(it["rationale"])}</div>'
    if it.get("classification"):
        extra += f'<span class="badge">{_e(it["classification"])}</span>'
    if it.get("due_at"):
        extra += f'<span class="badge">due {_e(it["due_at"][:10])}</span>'
    conf = it.get("confidence", 1.0)
    conf_badge = "" if conf >= 1.0 else f'<span class="badge">conf {conf:.1f}</span>'
    return (f'<li class="{cls}">{icon} {_e(it["text"])}{evs}{conf_badge}'
            f'{extra}</li>')


def _section(title, items, cls=""):
    if not items:
        return ""
    lis = "".join(_item_li(i, cls) for i in items)
    return f"<section><h2>{_e(title)}</h2><ul>{lis}</ul></section>"


def write_html(conn, project, cap, out_path: str) -> str:
    ent = cap["entropy"]
    frows = "".join(
        f"<tr><td>{_e(f['factor'])}</td><td>{f['value']}</td>"
        f"<td>+{f['points']}</td><td>{_e(f['how_to_reduce'])}</td></tr>"
        for f in ent["breakdown"] if f["points"] > 0)

    next_html = ""
    if cap["next_action"]:
        a = cap["next_action"]
        next_html = (
            f'<section><h2>Recommended next action</h2><div class="next">'
            f'<div>{_e(a["text"])}</div>'
            f'<div><code>{_e(a["command"])}</code> · risk {_e(a["risk"])} · '
            f'approve with <code>reentry approve {_e(a["action_id"])}</code>'
            f'</div></div></section>')

    timeline = "".join(
        f'<li><span class="badge">{_e(e["occurred_at"][:16])}</span> '
        f'[{_e(e["source"])}/{_e(e["event_type"])}] '
        f'{_e((db.jloads(e["payload"]) or {}).get("subject") or (db.jloads(e["payload"]) or {}).get("text") or (db.jloads(e["payload"]) or {}).get("name") or "")}'
        f'<span class="ev">{_e(e["id"])}</span></li>'
        for e in ledger.events_for_project(conn, project["id"]))

    is_demo = "demo" in project["name"].lower()
    banner = ('<div class="demo-banner">SYNTHETIC DEMO DATA — seeded events, '
              'not real usage</div>' if is_demo else "")

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ReEntry — {_e(project['name'])}</title><style>{CSS}</style></head><body>
<header><h1><span class="brand">ReEntry /</span> {_e(project['name'])}</h1>
<span class="stamp">capsule generated {_e(cap['generated_at'])}</span></header>
{banner}
<section><h2>Context entropy — {ent['score']}/100 ({_e(ent['label'])})</h2>
<div class="tape"><div class="tape-fill" style="width:{ent['score']}%"></div></div>
<table class="factors">{frows}</table></section>
{_section('Last known objective', [cap['objective']] if cap['objective'] else [])}
{_section('Where things stand', cap['where_things_stand'])}
{_section('What changed', cap['what_changed'])}
{_section('Decisions', cap['decisions'])}
{_section('Blockers', cap['blockers'], cls='blocker')}
{_section('Contradictions & stale assumptions', cap['contradictions'])}
{_section('Deadlines & commitments', cap['deadlines'])}
{next_html}
<section><h2>Timeline (event ledger)</h2><ul>{timeline}</ul></section>
<details class="raw"><summary class="stamp">raw capsule JSON (proof mode)</summary>
<pre>{_e(db.jdumps(cap))}</pre></details>
</body></html>"""
    p = Path(out_path).resolve()
    p.write_text(doc)
    return str(p)
