import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import VerificationReadout from '../components/VerificationReadout'
import { SCORE_HIST, OPERATING_POINTS } from '../data/demo'

/** Static score-distribution chart (no entrance animation — data is the design). */
function ScoreChart() {
  const W = 400, B = 20, bw = W / B, maxH = 138, base = 156
  const bar = (v: number, i: number, fill: string) => (
    <rect key={`${fill}-${i}`} x={i * bw + 2} y={base - v * maxH} width={bw - 4} height={v * maxH} rx={1.5} fill={fill} fillOpacity={0.85} />
  )
  return (
    <div>
      <div className="font-mono text-[11px] tracking-[0.12em] uppercase text-muted mb-3">Verifier support score · distribution</div>
      <svg viewBox="0 0 400 172" className="w-full h-auto block" role="img" aria-label="Hallucinated sentences cluster at low scores; grounded sentences at high scores.">
        <line x1="0" y1="156" x2="400" y2="156" stroke="var(--color-border)" />
        {SCORE_HIST.hallucinated.map((v, i) => bar(v, i, 'var(--color-unsupported-fg)'))}
        {SCORE_HIST.grounded.map((v, i) => bar(v, i, 'var(--color-supported-fg)'))}
      </svg>
      <div className="flex justify-between font-mono text-[11px] text-muted mt-2">
        <span>0.0 · not in context</span><span>1.0 · grounded</span>
      </div>
      <div className="flex gap-5 mt-3 font-mono text-[11px] text-muted">
        <span className="flex items-center gap-1.5"><i className="w-2 h-2 rounded-sm" style={{ background: 'var(--color-supported-fg)' }} />grounded</span>
        <span className="flex items-center gap-1.5"><i className="w-2 h-2 rounded-sm" style={{ background: 'var(--color-unsupported-fg)' }} />hallucinated</span>
      </div>
    </div>
  )
}

function Header() {
  return (
    <header className="border-b border-border">
      <div className="max-w-[1100px] mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="font-display font-bold text-[19px] tracking-tight no-underline text-text">Grounded<span className="text-accent">.</span></Link>
        <div className="flex items-center gap-8">
          <span className="font-mono text-[12px] text-muted tnum hidden sm:inline">
            RAGTRUTH <span className="text-unsupported-fg">34.9%</span> <span className="text-accent">→</span> <span className="text-supported-fg">13.1%</span>
          </span>
          <Link to="/app" className="font-mono text-[12px] tracking-[0.04em] uppercase text-accent no-underline hover:text-text">Live demo →</Link>
        </div>
      </div>
    </header>
  )
}

export default function Landing() {
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const flow = ['Retrieve', 'Generate', 'Verify', 'Correct']

  return (
    <div className="bg-bg min-h-screen">
      <Header />

      {/* ── HERO ─────────────────────────────────────────────────────── */}
      <section className="max-w-[1100px] mx-auto px-6 pt-16 md:pt-24 pb-12">
        <div className="font-mono text-[12px] tracking-[0.12em] uppercase text-muted mb-6">
          Self-correcting RAG · verifying live <span className="text-supported-fg">●</span>
        </div>
        <h1 className="font-display font-bold tracking-tight leading-[1.04] text-[clamp(2.5rem,6vw,4.5rem)] max-w-[16ch]">
          Watch it catch a hallucination.
        </h1>
        <p className="text-muted text-[18px] leading-relaxed max-w-[46ch] mt-6">
          Grounded checks every claim in an answer against the retrieved evidence, and drops the ones the context can&rsquo;t support. Here&rsquo;s a real one, live.
        </p>

        {/* live verification — no card box, sits on --bg */}
        <div className="mt-12 max-w-[760px]">
          <VerificationReadout />
        </div>

        {/* signature stat */}
        <div className="mt-14">
          <div className="font-mono text-[11px] tracking-[0.14em] uppercase text-muted mb-3">Measured on RAGTruth · N=2,700</div>
          <div className="font-mono tnum text-[clamp(2.25rem,6vw,3.25rem)] flex items-baseline gap-4 leading-none">
            <span className="text-unsupported-fg">34.9%</span>
            <span className="text-accent text-[0.7em]">→</span>
            <span className="text-supported-fg">13.1%</span>
            <span className="font-body text-muted text-[14px] self-end mb-1 hidden sm:inline">&minus;62.6% hallucination</span>
          </div>
        </div>
      </section>

      {/* ── STATS — borderless row ───────────────────────────────────── */}
      <section className="max-w-[1100px] mx-auto px-6 py-12">
        <div className="border-t border-border pt-10 grid grid-cols-2 md:grid-cols-4 gap-8">
          {[
            { n: '−62.6%', l: 'hallucination reduction\n95% CI 59.4–65.8' },
            { n: '0.85', l: 'verifier AUROC\nMiniCheck > NLI 0.78' },
            { n: '78.5%', l: 'correct content retained\nat the balanced point' },
            { n: '2', l: 'benchmarks\nRAGTruth & HaluEval' },
          ].map((s) => (
            <div key={s.n}>
              <div className="font-mono tnum text-accent text-[clamp(1.6rem,3.5vw,2.4rem)] leading-none">{s.n}</div>
              <div className="text-muted text-[13px] mt-3 leading-snug whitespace-pre-line">{s.l}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── HOW IT WORKS — minimal flow, no step cards ───────────────── */}
      <section className="max-w-[1100px] mx-auto px-6 py-12">
        <div className="font-mono text-[11px] tracking-[0.14em] uppercase text-muted mb-4">How it works</div>
        <p className="text-text text-[20px] max-w-[60ch] leading-relaxed">
          Retrieve the context, generate strictly from it, verify every claim against it, and drop whatever the evidence doesn&rsquo;t support.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-x-4 gap-y-3 font-mono text-[13px] tracking-[0.04em] uppercase text-muted">
          {flow.map((s, i) => (
            <span key={s} className="flex items-center gap-4">
              {s}{i < flow.length - 1 && <span className="text-border">→</span>}
            </span>
          ))}
        </div>
      </section>

      {/* ── WHY IT WORKS ─────────────────────────────────────────────── */}
      <section className="max-w-[1100px] mx-auto px-6 py-12">
        <div className="grid md:grid-cols-2 gap-12 items-start">
          <div>
            <div className="font-mono text-[11px] tracking-[0.14em] uppercase text-muted mb-4">Why it works</div>
            <h2 className="font-body font-medium text-[clamp(1.5rem,3vw,2rem)] leading-snug max-w-[20ch]">The verifier separates grounded from invented.</h2>
            <p className="text-muted text-[15px] leading-relaxed max-w-[52ch] mt-4">
              Hallucinated sentences score low; grounded ones score high. That separation — across 17,213 sentences — is what the threshold cuts.
            </p>
            <table className="w-full mt-8 text-[14px]">
              <thead>
                <tr className="border-b border-border">
                  {['Operating point', 'Hallucination', 'Reduction', 'Kept'].map((h) => (
                    <th key={h} className="font-mono text-[11px] uppercase tracking-[0.06em] text-muted font-normal text-left py-3 first:pl-0">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {OPERATING_POINTS.map((o) => (
                  <tr key={o.label} className="border-b border-border">
                    <td className="py-3 text-text">{o.label}</td>
                    <td className="py-3 font-mono tnum text-muted">{o.rate}</td>
                    <td className="py-3 font-mono tnum text-accent">{o.reduction}</td>
                    <td className="py-3 font-mono tnum text-muted">{o.kept}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <ScoreChart />
        </div>
      </section>

      {/* ── CTA — no card box ────────────────────────────────────────── */}
      <section className="max-w-[1100px] mx-auto px-6 py-16">
        <div className="border-t border-border pt-12">
          <h2 className="font-body font-medium text-[clamp(1.5rem,3vw,2rem)] leading-snug max-w-[18ch]">See it on your own question.</h2>
          <p className="text-muted text-[15px] leading-relaxed max-w-[50ch] mt-4">
            Open the live instrument, then drag the threshold and watch claims flip supported and unsupported in real time.
          </p>
          <form className="flex gap-3 max-w-[34rem] mt-8" onSubmit={(e) => { e.preventDefault(); navigate(`/app?q=${encodeURIComponent(q)}`) }}>
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Verify your own question…" aria-label="Verify your own question"
              className="flex-1 px-4 py-3 bg-surface border border-border text-text placeholder:text-muted outline-none focus:outline-2 focus:outline-accent rounded-[4px]" />
            <button type="submit" className="font-medium px-6 py-3 bg-accent text-bg rounded-[4px]">Verify →</button>
          </form>
        </div>
      </section>

      <footer className="max-w-[1100px] mx-auto px-6 py-10 border-t border-border">
        <p className="font-mono text-[11px] text-muted">A faithfulness instrument — it measures grounding in the retrieved evidence, not world-truth.</p>
      </footer>
    </div>
  )
}
