"use client";

import Image from "next/image";
import Link from "next/link";
import { ScrollReveal } from "@/components/ui/ScrollReveal";
import { CountUp } from "@/components/ui/CountUp";
import { CopyButton } from "@/components/ui/CopyButton";

const QUICK_START = `pip install -e .
reentry demo        # seeded project, no credentials
make demo-full      # starts web app and CLI demo`;

// ---------------------------------------------------------------------------
// Nav
// ---------------------------------------------------------------------------

function Nav() {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <Link href="/" className="nav-wordmark">
          Re<span className="accent">Entry</span>
        </Link>
        <ul className="nav-links">
          <li><a href="#tour">How it works</a></li>
          <li><a href="#proof">Results</a></li>
          <li>
            <a
              href="https://github.com/DevansuA/reentry"
              target="_blank"
              rel="noopener noreferrer"
            >
              GitHub
            </a>
          </li>
          <li>
            <Link href="/app" className="btn btn-sm btn-cyan">
              Open demo
            </Link>
          </li>
        </ul>
      </div>
    </nav>
  );
}

// ---------------------------------------------------------------------------
// Hero
// ---------------------------------------------------------------------------

function Hero() {
  return (
    <section className="hero section">
      <div className="container">
        <div className="hero-grid">
          <div className="hero-copy">
            <ScrollReveal>
              <p className="section-tag">Temporal operating system</p>
              <h1 className="display" style={{ marginTop: "var(--s3)" }}>
                You left off
                <br />
                <span style={{ color: "var(--cyan)" }}>here.</span>
              </h1>
            </ScrollReveal>

            <ScrollReveal delay={100}>
              <p className="subheadline" style={{ maxWidth: "42ch" }}>
                ReEntry reconstructs the real execution state of an interrupted
                project from commits, commands, decisions, notes, and test
                results. Every claim links to the evidence behind it.
              </p>
            </ScrollReveal>

            <ScrollReveal delay={200}>
              <div className="hero-actions">
                <Link href="/app" className="btn btn-solid">
                  Open live demo
                </Link>
                <a
                  href="https://github.com/DevansuA/reentry"
                  className="btn btn-outline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub
                </a>
              </div>
            </ScrollReveal>
          </div>

          <ScrollReveal delay={150} className="hero-screenshot">
            <Image
              src="/screenshots/capsule-view.png"
              alt="ReEntry capsule view showing objective, blockers, contradictions, and entropy score"
              width={1280}
              height={900}
              priority
              style={{ width: "100%", height: "auto" }}
            />
          </ScrollReveal>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Problem strip
// ---------------------------------------------------------------------------

function ProblemStrip() {
  return (
    <section className="section-sm">
      <div className="container">
        <ScrollReveal>
          <div className="problem-strip">
            <div className="problem-cell">
              <p className="headline" style={{ color: "var(--cyan)" }}>46h</p>
              <p style={{ color: "var(--ink-2)", fontSize: "0.9rem" }}>
                Typical gap between knowledge-work sessions.
              </p>
            </div>
            <div className="problem-cell">
              <p className="headline" style={{ color: "var(--cyan)" }}>8 min</p>
              <p style={{ color: "var(--ink-2)", fontSize: "0.9rem" }}>
                Average time to rebuild context after an interruption.
              </p>
            </div>
            <div className="problem-cell">
              <p className="headline" style={{ color: "var(--cyan)" }}>20/20</p>
              <p style={{ color: "var(--ink-2)", fontSize: "0.9rem" }}>
                Reconstruction accuracy vs 4/16 for recency and flat-note baselines.
              </p>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Product tour
// ---------------------------------------------------------------------------

const TOUR_ITEMS = [
  {
    tag: "Contradiction Radar",
    headline: "Catches what memory misses.",
    body:
      "Four deterministic rules detect stale notes, superseded decisions, blockers resolved by later passing tests, and moved deadlines. Nothing deleted. Every contradiction links to the two pieces of evidence it reconciles.",
    screenshot: "/screenshots/capsule-view.png",
    alt: "Capsule view showing stale note flagged as contradiction",
  },
  {
    tag: "Evidence chips",
    headline: "Every claim has a receipt.",
    body:
      "Click any cyan chip to open the raw ledger event behind it. Every sentence in the capsule traces to a real, timestamped record. Nothing is invented by the model.",
    screenshot: "/screenshots/evidence-modal.png",
    alt: "Evidence modal showing raw JSON ledger event",
    reverse: true,
  },
  {
    tag: "Safe action loop",
    headline: "Propose. Approve. Verified.",
    body:
      "The planner proposes the smallest useful next action. Only allow-listed commands run, checked at proposal and again at execution. Metacharacters rejected. 120 s timeout. A verified run resolves the linked blocker.",
    screenshot: "/screenshots/action-panel.png",
    alt: "Action panel with Approve and run button and risk class badge",
  },
];

function ProductTour() {
  return (
    <section id="tour" className="section">
      <div className="container">
        <ScrollReveal>
          <p className="section-tag">How it works</p>
          <h2
            className="headline"
            style={{ marginTop: "var(--s3)", maxWidth: "22ch" }}
          >
            Three layers that baselines skip.
          </h2>
        </ScrollReveal>

        {TOUR_ITEMS.map((item, i) => (
          <ScrollReveal key={i} delay={i * 80}>
            <div className={`tour-section ${item.reverse ? "reverse" : ""}`}>
              <div className="tour-copy">
                <p className="section-tag">{item.tag}</p>
                <h3
                  className="headline"
                  style={{ fontSize: "clamp(1.5rem, 2.5vw, 2.2rem)", marginTop: "var(--s2)" }}
                >
                  {item.headline}
                </h3>
                <p
                  style={{
                    color: "var(--ink-2)",
                    fontSize: "0.9375rem",
                    lineHeight: "1.6",
                    maxWidth: "48ch",
                  }}
                >
                  {item.body}
                </p>
              </div>
              <div className="tour-screenshot">
                <Image
                  src={item.screenshot}
                  alt={item.alt}
                  width={1280}
                  height={900}
                  style={{ width: "100%", height: "auto" }}
                />
              </div>
            </div>
          </ScrollReveal>
        ))}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Proof (eval stats)
// ---------------------------------------------------------------------------

function ProofSection() {
  return (
    <section id="proof" className="section" style={{ background: "var(--ground-1)" }}>
      <div className="container">
        <ScrollReveal>
          <p className="section-tag">Measured results</p>
          <h2
            className="headline"
            style={{ marginTop: "var(--s3)", marginBottom: "var(--s8)" }}
          >
            Not a claim. A benchmark.
          </h2>
        </ScrollReveal>

        <div className="proof-grid">
          <ScrollReveal delay={0}>
            <div className="proof-card highlight">
              <p className="label" style={{ color: "var(--cyan)" }}>ReEntry</p>
              <p className="stat-number">
                <CountUp to={20} />/20
              </p>
              <p className="stat-label">checks passed across 4 scenarios</p>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={80}>
            <div className="proof-card">
              <p className="label">Recency baseline</p>
              <p className="stat-number" style={{ color: "var(--ink-2)" }}>
                <CountUp to={4} />/16
              </p>
              <p className="stat-label">
                Latest events shown verbatim, no reconciliation
              </p>
            </div>
          </ScrollReveal>

          <ScrollReveal delay={160}>
            <div className="proof-card">
              <p className="label">Flat-notes baseline</p>
              <p className="stat-number" style={{ color: "var(--ink-2)" }}>
                <CountUp to={4} />/16
              </p>
              <p className="stat-label">
                All notes retrieved equally, no temporal ordering
              </p>
            </div>
          </ScrollReveal>
        </div>

        <ScrollReveal delay={240}>
          <p
            style={{
              marginTop: "var(--s6)",
              color: "var(--ink-3)",
              fontSize: "0.8125rem",
              maxWidth: "64ch",
            }}
          >
            Deterministic graders, synthetic scenarios, no LLM in any arm.
            Measures the temporal state architecture, not model quality.{" "}
            <a
              href="https://github.com/DevansuA/reentry/blob/main/docs/EVALUATION.md"
              style={{ color: "var(--ink-2)", textDecoration: "underline" }}
              target="_blank"
              rel="noopener noreferrer"
            >
              Full methodology
            </a>
          </p>
        </ScrollReveal>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Quick start
// ---------------------------------------------------------------------------

function QuickStartSection() {
  return (
    <section className="section">
      <div className="container">
        <ScrollReveal>
          <p className="section-tag">Quick start</p>
          <h2
            className="headline"
            style={{ marginTop: "var(--s3)", marginBottom: "var(--s8)", maxWidth: "24ch" }}
          >
            Three commands to a working demo.
          </h2>
        </ScrollReveal>

        <ScrollReveal delay={100}>
          <div className="code-block">
            <div className="code-header">
              <div className="code-dots">
                <span className="code-dot" />
                <span className="code-dot" />
                <span className="code-dot" />
              </div>
              <CopyButton text={QUICK_START} />
            </div>
            <div className="code-body">
              <div>
                <span className="comment"># Python 3.10+, Node 18+, git</span>
              </div>
              <div>
                <span className="cmd">pip install -e .</span>
              </div>
              <div>
                <span className="cmd">reentry demo</span>
                <span className="comment">   # seeded project, no credentials</span>
              </div>
              <div>
                <span className="cmd">make demo-full</span>
                <span className="comment">  # starts web app + CLI demo</span>
              </div>
            </div>
          </div>
        </ScrollReveal>

        <ScrollReveal delay={200}>
          <div style={{ marginTop: "var(--s8)", display: "flex", gap: "var(--s3)", flexWrap: "wrap" }}>
            <Link href="/app" className="btn btn-solid">
              Open live demo
            </Link>
            <a
              href="https://github.com/DevansuA/reentry"
              className="btn btn-outline"
              target="_blank"
              rel="noopener noreferrer"
            >
              View on GitHub
            </a>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Footer
// ---------------------------------------------------------------------------

function Footer() {
  return (
    <footer className="footer">
      <div className="container">
        <div className="footer-inner">
          <span style={{ fontSize: "0.875rem", color: "var(--ink-3)" }}>
            Built by{" "}
            <a
              href="https://github.com/DevansuA"
              style={{ color: "var(--ink-2)" }}
              target="_blank"
              rel="noopener noreferrer"
            >
              Devansu Agarwal
            </a>
          </span>
          <ul className="footer-links">
            <li>
              <a
                href="https://github.com/DevansuA/reentry"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub
              </a>
            </li>
            <li>
              <a
                href="https://github.com/DevansuA/reentry/blob/main/LICENSE"
                target="_blank"
                rel="noopener noreferrer"
              >
                MIT License
              </a>
            </li>
            <li>
              <Link href="/app">Demo</Link>
            </li>
          </ul>
        </div>
      </div>
    </footer>
  );
}

// ---------------------------------------------------------------------------
// Page composition
// ---------------------------------------------------------------------------

export function MarketingPage() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <ProblemStrip />
        <ProductTour />
        <ProofSection />
        <QuickStartSection />
      </main>
      <Footer />
    </>
  );
}
