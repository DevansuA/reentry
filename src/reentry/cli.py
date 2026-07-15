"""ReEntry CLI."""

from __future__ import annotations

import os

import click
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from . import actions as actions_mod
from . import capsule as capsule_mod
from . import contradictions as contradictions_mod
from . import db, gitsource, ledger, state

console = Console()

CONF_ICON = {"observed": "●", "inferred": "○", "user_corrected": "◆"}


def _conn():
    return db.connect()


def _project_or_die(conn, path="."):
    p = state.get_project(conn, path)
    if not p:
        console.print("[red]No ReEntry project here. Run [bold]reentry init[/bold] first.[/red]")
        raise SystemExit(1)
    return p


@click.group()
def cli():
    """ReEntry: return to momentum. A temporal operating system for interrupted work."""


@cli.command()
@click.option("--name", default=None, help="Project name (defaults to folder name).")
def init(name):
    """Register the current directory as a ReEntry project."""
    conn = _conn()
    p = state.register_project(conn, ".", name)
    console.print(f"[green]✓[/green] Project [bold]{p['name']}[/bold] registered "
                  f"({p['root_path']}).")
    if gitsource.is_repo(p["root_path"]):
        n = gitsource.sync_commits(conn, p)
        console.print(f"[green]✓[/green] Git detected, ingested {n} commit(s).")


@cli.command()
@click.option("--objective", "-o", default=None, help="What you intend to accomplish.")
def start(objective):
    """Start a work session."""
    conn = _conn()
    p = _project_or_die(conn)
    s = state.start_session(conn, p["id"], objective)
    console.print(f"[green]✓[/green] Session started ({s['id']})."
                  + (f" Objective: {objective}" if objective else ""))


def _claim_cmd(kind, help_text):
    @click.argument("text")
    @click.option("--rationale", "-r", default=None)
    def cmd(text, rationale):
        conn = _conn()
        p = _project_or_die(conn)
        s = state.current_session(conn, p["id"])
        c = state.add_claim(conn, p["id"], kind, text, rationale=rationale,
                            session_id=s["id"] if s else None)
        console.print(f"[green]✓[/green] {kind.capitalize()} recorded ({c['id']}).")
    cmd.__doc__ = help_text
    return cmd


cli.command("note")(_claim_cmd("note", "Record a note."))
cli.command("decide")(_claim_cmd("decision", "Record a decision (use -r for rationale)."))
cli.command("block")(_claim_cmd("blocker", "Record a blocker."))
cli.command("question")(_claim_cmd("question", "Record an open question."))


@cli.command()
def checkpoint():
    """End the session with a checkpoint."""
    conn = _conn()
    p = _project_or_die(conn)
    gitsource.sync_commits(conn, p)
    ck = state.create_checkpoint(conn, p["id"])
    console.print(f"[green]✓[/green] Checkpoint {ck['id']} created; session closed.")


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Emit the capsule as JSON.")
def resume(as_json):
    """Generate the Re-entry Capsule for this project."""
    conn = _conn()
    p = _project_or_die(conn)
    cap = capsule_mod.generate(conn, p)
    if as_json:
        console.print_json(db.jdumps(cap))
        return
    render_capsule(cap)


def _ev(item):
    ids = item.get("evidence_ids") or []
    tag = f" [dim]‹ev:{','.join(ids[:3])}{'…' if len(ids) > 3 else ''}›[/dim]" if ids else ""
    icon = CONF_ICON.get(item.get("inference", "observed"), "●")
    return f"{icon} {escape(item['text'])}{tag}"


def render_capsule(cap):
    ent = cap["entropy"]
    color = {"low": "green", "moderate": "yellow", "high": "red"}[ent["label"]]
    console.print(Panel(
        f"[bold]{cap['project']}[/bold]   "
        f"context entropy: [{color}]{ent['score']}/100 ({ent['label']})[/{color}]",
        title="RE-ENTRY CAPSULE", subtitle=cap["generated_at"]))

    if cap["objective"]:
        console.print("[bold]1. Last known objective[/bold]")
        console.print("   " + _ev(cap["objective"]))
    sections = [
        ("2. Where things stand", cap["where_things_stand"]),
        ("3. What changed", cap["what_changed"]),
        ("4. Decisions", cap["decisions"]),
        ("5. Blockers", cap["blockers"]),
        ("6. Contradictions & stale assumptions", cap["contradictions"]),
        ("7. Deadlines & commitments", cap["deadlines"]),
    ]
    for title, items in sections:
        if not items:
            continue
        console.print(f"[bold]{title}[/bold]")
        for it in items:
            console.print("   " + _ev(it))
            if it.get("rationale"):
                console.print(f"     [dim]why: {it['rationale']}[/dim]")
            if it.get("classification"):
                console.print(f"     [dim]classification: {it['classification']}[/dim]")
            if it.get("due_at"):
                console.print(f"     [dim]due: {it['due_at'][:16]}[/dim]")

    if cap["next_action"]:
        a = cap["next_action"]
        console.print("[bold]8. Recommended next action[/bold]")
        console.print(f"   → {a['text']}")
        console.print(f"     [dim]{a['command']}  ·  risk: {a['risk']}  ·  "
                      f"approve with: reentry approve {a['action_id']}[/dim]")
    console.print("[dim]● observed  ○ inferred  ◆ user-corrected   "
                  "‹ev:…› = ledger evidence ids (reentry evidence <id>)[/dim]")


@cli.command()
@click.argument("event_id")
def evidence(event_id):
    """Show the raw ledger event behind a claim."""
    conn = _conn()
    e = ledger.get_event(conn, event_id)
    if not e:
        # maybe it's a checkpoint id
        row = conn.execute("SELECT * FROM checkpoints WHERE id = ?", (event_id,)).fetchone()
        if row:
            console.print_json(db.jdumps(dict(row)))
            return
        console.print("[red]No such evidence id.[/red]")
        raise SystemExit(1)
    console.print_json(db.jdumps(e))


@cli.command()
def status():
    """Quick project status."""
    conn = _conn()
    p = _project_or_die(conn)
    s = state.current_session(conn, p["id"])
    git = gitsource.live_status(p["root_path"])
    console.print(f"Project: [bold]{p['name']}[/bold]")
    console.print(f"Session: {'open since ' + s['started_at'] if s else 'none'}")
    if git.get("is_repo"):
        console.print(f"Git: {git['branch']} @ {git['head']} "
                      f"({git['uncommitted_count']} uncommitted)")
    blockers = state.claims_for_project(conn, p["id"], "blocker", "active")
    console.print(f"Active blockers: {len(blockers)}")


@cli.command()
def replay():
    """Chronological replay of the project's event history."""
    conn = _conn()
    p = _project_or_die(conn)
    table = Table(title=f"Timeline: {p['name']}")
    for col in ("when", "source", "type", "what", "id"):
        table.add_column(col)
    for e in ledger.events_for_project(conn, p["id"]):
        payload = db.jloads(e["payload"]) or {}
        what = payload.get("subject") or payload.get("text") or \
            payload.get("name") or payload.get("command") or ""
        table.add_row(e["occurred_at"][:16], e["source"], e["event_type"],
                      str(what)[:60], e["id"])
    console.print(table)


@cli.command("actions")
def list_actions():
    """List proposed/pending actions."""
    conn = _conn()
    p = _project_or_die(conn)
    rows = actions_mod.pending(conn, p["id"])
    if not rows:
        console.print("No pending actions.")
        return
    for a in rows:
        console.print(f"[bold]{a['id']}[/bold]  {a['title']}")
        console.print(f"   {a['command']}  ·  risk: {a['risk']}")


@cli.command()
@click.argument("action_id")
@click.option("--run/--no-run", default=True, help="Execute immediately after approval.")
def approve(action_id, run):
    """Approve (and by default execute + verify) a proposed action."""
    conn = _conn()
    p = _project_or_die(conn)
    a = actions_mod.approve(conn, action_id)
    if not a:
        console.print("[red]No such action.[/red]")
        raise SystemExit(1)
    console.print(f"[green]✓[/green] Approved: {a['title']}")
    if run:
        a = actions_mod.execute(conn, action_id, cwd=p["root_path"])
        res = db.jloads(a["result"]) or {}
        ok = a["status"] == "verified"
        console.print(("[green]✓ verified[/green]" if ok else "[red]✗ failed[/red]")
                      + f"  exit={res.get('exit_code')}")
        tail = (res.get("stdout") or res.get("stderr") or "").strip().splitlines()[-5:]
        for line in tail:
            console.print(f"   [dim]{line}[/dim]")
        if ok and a["resolves_claim"]:
            console.print("[green]✓[/green] Linked blocker marked resolved; state updated.")


@cli.command()
@click.argument("action_id")
def reject(action_id):
    """Reject a proposed action."""
    conn = _conn()
    actions_mod.reject(conn, action_id)
    console.print("Rejected.")


@cli.command()
@click.option("--out", default="reentry_dashboard.html", help="Output HTML path.")
def dashboard(out):
    """Write a static HTML dashboard for this project."""
    from . import report
    conn = _conn()
    p = _project_or_die(conn)
    cap = capsule_mod.generate(conn, p)
    path = report.write_html(conn, p, cap, out)
    console.print(f"[green]✓[/green] Dashboard written to {path}")


@cli.command()
def doctor():
    """Check the local ReEntry installation and all optional surfaces."""
    import shutil
    from pathlib import Path as _Path

    conn = _conn()
    ok = True

    def _check(label, value, hint=""):
        nonlocal ok
        if value:
            console.print(f"  [green]✓[/green] {label}")
        else:
            ok = False
            console.print(f"  [red]✗[/red] {label}"
                          + (f"\n      {hint}" if hint else ""))

    console.print(f"[bold]ReEntry doctor[/bold]\n")

    # --- core ----------------------------------------------------------------
    console.print("[dim]Core[/dim]")
    db_p = db.db_path()
    console.print(f"  DB: {db_p}")
    _check("DB is writable", os.access(db_p.parent, os.W_OK),
           f"Run `mkdir -p {db_p.parent}` to create the data directory.")
    n = conn.execute("SELECT COUNT(*) c FROM projects").fetchone()["c"]
    console.print(f"  Projects: {n}")
    _check("Git available", bool(shutil.which("git")),
           "Install git: https://git-scm.com/")

    # --- optional: web app ---------------------------------------------------
    console.print("\n[dim]Web app (optional)[/dim]")
    node_ok = bool(shutil.which("node"))
    _check("Node.js available", node_ok,
           "Install Node.js 18+: https://nodejs.org/")
    web_dir = _Path(__file__).parent.parent.parent / "web"
    web_built = (web_dir / ".next").is_dir()
    _check("Next.js built (.next/ present)", web_built,
           "Run `make web-build` to build the web app.")

    # --- optional: server ----------------------------------------------------
    console.print("\n[dim]FastAPI server (optional)[/dim]")
    fastapi_ok = False
    try:
        import fastapi  # noqa: F401
        fastapi_ok = True
    except ImportError:
        pass
    _check("fastapi installed", fastapi_ok,
           "Run `pip install fastapi uvicorn` to enable the web UI.")
    uvicorn_ok = bool(shutil.which("uvicorn"))
    _check("uvicorn on PATH", uvicorn_ok,
           "Run `pip install uvicorn`.")

    # --- optional: connectors ------------------------------------------------
    console.print("\n[dim]Connectors (optional)[/dim]")
    watchdog_ok = False
    try:
        import watchdog  # noqa: F401
        watchdog_ok = True
    except ImportError:
        pass
    _check("watchdog installed (file watcher)", watchdog_ok,
           "Run `pip install watchdog` to enable `reentry watch`.")

    icalendar_ok = False
    try:
        import icalendar  # noqa: F401
        icalendar_ok = True
    except ImportError:
        pass
    _check("icalendar installed (calendar connector)", icalendar_ok,
           "Run `pip install icalendar` to enable `reentry sync-calendar`.")

    mcp_ok = False
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
        mcp_ok = True
    except ImportError:
        pass
    _check("mcp installed (MCP server)", mcp_ok,
           "Run `pip install mcp` to enable the MCP server.")

    spool_dir = db.db_path().parent / "spool"
    if spool_dir.exists():
        spool_file = spool_dir / "events.jsonl"
        n_spool = 0
        if spool_file.exists():
            n_spool = sum(1 for _ in spool_file.open())
        console.print(f"  spool: {spool_dir} ({n_spool} lines pending)")
    else:
        console.print("  [dim]spool: not present (no hook activity yet)[/dim]")

    # --- LLM -----------------------------------------------------------------
    console.print("\n[dim]LLM (optional)[/dim]")
    provider = os.environ.get("REENTRY_LLM_PROVIDER", "none")
    console.print(f"  provider: {provider} "
                  f"({'configured' if provider != 'none' else 'deterministic mode (default)'})")

    console.print()
    if ok:
        console.print("[green]✓ all checks passed[/green]")
    else:
        console.print("[yellow]some optional components are missing (see hints above)[/yellow]")


@cli.command()
@click.option("--dir", "target", default=None,
              help="Where to create the demo project (default: temp dir).")
def demo(target):
    """Create the seeded synthetic demo project and print its capsule."""
    from . import demo as demo_mod
    conn = _conn()
    p = demo_mod.seed(conn, target)
    console.print(Panel(
        "[yellow]SYNTHETIC DEMO PROJECT[/yellow]: all events below are seeded, "
        "not real usage.", style="yellow"))
    cap = capsule_mod.generate(conn, p)
    render_capsule(cap)
    console.print(f"\nDemo project directory: {p['root_path']}")
    console.print("Try: cd into it, then `reentry replay`, `reentry actions`, "
                  "`reentry approve <id>`, `reentry dashboard`.")


@cli.command("ingest-spool")
def ingest_spool():
    """Read the terminal spool and append new events to the ledger."""
    from .connectors import terminal as term
    conn = _conn()
    p = _project_or_die(conn)
    n = term.ingest_spool(conn, p)
    console.print(f"[green]✓[/green] Ingested {n} new event(s) from spool.")


@cli.command("watch")
def watch_cmd():
    """Watch the project directory for file-save events (runs until Ctrl+C)."""
    from .connectors import fs_watcher
    conn = _conn()
    p = _project_or_die(conn)
    console.print(f"Watching {p['root_path']}. Ctrl+C to stop.")
    fs_watcher.watch(p)


@cli.command("sync-github")
@click.option("--repo", default=None,
              help="GitHub owner/repo slug. Detected from git remote if absent.")
def sync_github(repo):
    """Poll GitHub events for the current repository and ingest new ones."""
    from .connectors import github as gh
    conn = _conn()
    p = _project_or_die(conn)
    detected = repo or gh.detect_repo(p["root_path"])
    if not detected:
        console.print("[yellow]No GitHub remote detected. Pass --repo owner/repo.[/yellow]")
        raise SystemExit(1)
    n = gh.sync_github(conn, p, repo=detected)
    if n == 0:
        console.print("[dim]No new events (offline or already up to date).[/dim]")
    else:
        console.print(f"[green]✓[/green] Ingested {n} GitHub event(s) for {detected}.")


@cli.command("sync-calendar")
@click.argument("source")
def sync_calendar(source):
    """Ingest calendar events from a local .ics file or private ICS URL.

    SOURCE is a file path (~/calendar.ics) or an HTTPS URL to a private
    ICS feed. Events with deadline-like summaries become deadline claims;
    all text is redacted before ingestion.
    """
    from .connectors import calendar_ics as cal
    conn = _conn()
    p = _project_or_die(conn)
    try:
        n = cal.sync_calendar(conn, p, source)
    except FileNotFoundError:
        console.print(f"[red]File not found: {source}[/red]")
        console.print("Run with a valid .ics path or a private calendar URL.")
        raise SystemExit(1)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Could not read calendar: {exc}[/red]")
        console.print("Make sure the source is a valid .ics file or URL.")
        raise SystemExit(1)
    if n == 0:
        console.print("[dim]No new calendar events (already up to date or empty feed).[/dim]")
    else:
        console.print(f"[green]✓[/green] Ingested {n} calendar event(s).")


@cli.group("hook")
def hook_group():
    """Manage shell hooks for automatic terminal capture."""


@hook_group.command("install")
@click.option("--shell", default=None,
              help="Shell type: zsh or bash (auto-detected if absent).")
def hook_install(shell):
    """Print the line to add to your shell profile for opt-in capture."""
    import os
    from pathlib import Path
    hooks_dir = Path(__file__).parent.parent.parent.parent / "hooks"
    if not hooks_dir.exists():
        hooks_dir = Path(os.environ.get("REENTRY_HOOKS_DIR", "hooks"))

    if not shell:
        shell = os.environ.get("SHELL", "").split("/")[-1]

    if shell == "zsh":
        hook = hooks_dir / "reentry.zsh"
        rc = "~/.zshrc"
    else:
        hook = hooks_dir / "reentry.bash"
        rc = "~/.bashrc"

    console.print(f"Add this line to [bold]{rc}[/bold]:")
    console.print(f"\n    source {hook}\n")
    console.print("Then restart your shell or run:")
    console.print(f"    source {hook}")
    console.print("\nUse [bold]reentry ingest-spool[/bold] to import captured commands.")


def main():
    cli()


if __name__ == "__main__":
    main()
