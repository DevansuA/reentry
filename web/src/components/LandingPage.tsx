export function LandingPage() {
  return (
    <div className="landing">
      <div className="landing-logo">
        <span className="brand">ReEntry /</span> Mission Control
      </div>
      <p className="landing-tagline">
        Return to momentum. A temporal operating system for interrupted
        knowledge work.
      </p>

      <div className="landing-command">
        <div className="comment"># set up the demo (takes under a minute)</div>
        <div>pip install -e .</div>
        <div>reentry demo</div>
        <div style={{ marginTop: 8 }} className="comment">
          # then start the server
        </div>
        <div>make server</div>
      </div>

      <ul className="landing-features">
        <li>Append-only event ledger with secret redaction before write</li>
        <li>
          Contradiction Radar: detects stale notes, superseded decisions, and
          resolved blockers deterministically
        </li>
        <li>
          Context entropy score with per-factor breakdown and &ldquo;how to
          reduce&rdquo; hints
        </li>
        <li>
          Safe action loop: allow-listed commands only, double-validated,
          human approval required
        </li>
        <li>
          Evidence chips link every capsule claim to raw ledger events
        </li>
      </ul>

      <p
        className="dim"
        style={{ fontSize: 13, marginTop: 32, maxWidth: 480 }}
      >
        No project is registered for this server. Start the API server from
        your project directory after running{" "}
        <code>reentry init</code>.
      </p>
    </div>
  );
}
