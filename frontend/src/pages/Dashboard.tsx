import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ask, fetchExamples, cleanEvidence, type Verification } from '../lib/api'

type Status = 'empty' | 'loading' | 'error' | 'out'

function Header() {
  return (
    <header className="border-b border-border">
      <div className="max-w-[1100px] mx-auto px-6 h-16 flex items-center justify-between">
        <Link to="/" className="font-display font-bold text-[19px] tracking-tight no-underline text-text">Grounded<span className="text-accent">.</span></Link>
        <div className="flex items-center gap-8">
          <span className="font-mono text-[12px] text-muted tnum hidden sm:inline">
            RAGTRUTH <span className="text-unsupported-fg">34.9%</span> <span className="text-accent">→</span> <span className="text-supported-fg">13.1%</span>
          </span>
          <Link to="/" className="font-mono text-[12px] tracking-[0.04em] uppercase text-muted no-underline hover:text-text">← Overview</Link>
        </div>
      </div>
    </header>
  )
}

const Tile = ({ label, children, className = '' }: { label: string; children: React.ReactNode; className?: string }) => (
  <div className={`bg-surface border border-border rounded-[14px] p-5 ${className}`}>
    <div className="font-mono text-[11px] tracking-[0.12em] uppercase text-muted mb-4">{label}</div>
    {children}
  </div>
)

// Questions answerable from the live Wikipedia corpus (give a real grounded result).
const LIVE_QUESTIONS = ['What is photosynthesis?', 'Who was Albert Einstein?', 'What causes earthquakes?']

export default function Dashboard() {
  const [params] = useSearchParams()
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<Status>('empty')
  const [data, setData] = useState<Verification | null>(null)
  const [threshold, setThreshold] = useState(0.5)
  const [view, setView] = useState<'clean' | 'annotated'>('clean')
  const [error, setError] = useState('')
  const [examples, setExamples] = useState<Verification[]>([])
  const [open, setOpen] = useState<number | null>(null)
  const [step, setStep] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const didQ = useRef(false)

  function present(d: Verification) {
    setData(d); setThreshold(typeof d.threshold === 'number' ? d.threshold : 0.5)
    setView('clean'); setOpen(null); setStatus('out')
  }

  async function runAsk(qStr: string) {
    if (!qStr.trim()) return
    setStatus('loading'); setStep(0); setElapsed(0)
    const t = window.setInterval(() => setStep((s) => Math.min(2, s + 1)), 4500)
    const et = window.setInterval(() => setElapsed((e) => e + 1), 1000)
    try { present(await ask(qStr)) }
    catch (e) {
      setError(/fetch|network|failed/i.test(String(e)) ? "Couldn't reach the server. Make sure it's running, then try again." : `The model couldn't answer (is Ollama running?). ${e}`)
      setStatus('error')
    } finally { clearInterval(t); clearInterval(et) }
  }

  useEffect(() => { fetchExamples().then(setExamples).catch(() => setExamples([])) }, [])
  useEffect(() => {
    const q0 = params.get('q')
    if (q0 && !didQ.current) { didQ.current = true; setQuery(q0); runAsk(q0) }
  }, [params]) // eslint-disable-line react-hooks/exhaustive-deps

  const claims = data?.claims ?? []
  const supported = (s: number) => s >= threshold
  const nSup = claims.filter((c) => supported(c.support)).length
  const pct = claims.length ? Math.round((nSup / claims.length) * 100) : 0
  const kept = claims.filter((c) => supported(c.support)).map((c) => c.text)

  return (
    <div className="bg-bg min-h-screen">
      <Header />
      <div className="max-w-[1100px] mx-auto px-6 py-8">

        {/* query */}
        <form className="flex gap-3" onSubmit={(e) => { e.preventDefault(); runAsk(query) }}>
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask a question about the corpus…" aria-label="Ask a question"
            className="flex-1 px-4 py-3 bg-surface border border-border text-text placeholder:text-muted outline-none focus:outline-2 focus:outline-accent rounded-[4px]" />
          <button type="submit" disabled={status === 'loading'} className="font-medium px-6 py-3 bg-accent text-bg rounded-[4px] disabled:opacity-50">Ask</button>
        </form>
        <div className="flex flex-wrap items-center gap-2 mt-4 font-mono text-[12px]">
          <span className="text-muted tracking-[0.04em] uppercase shrink-0">Try live</span>
          {LIVE_QUESTIONS.map((q) => (
            <button key={q} type="button" disabled={status === 'loading'} onClick={() => { setQuery(q); runAsk(q) }}
              className="border border-border px-2.5 py-1 text-text hover:text-accent hover:border-accent rounded-[3px] transition-colors disabled:opacity-50">{q}</button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-2 font-mono text-[12px]">
          <span className="text-muted tracking-[0.04em] uppercase shrink-0">Caught hallucinations</span>
          {examples.map((ex, i) => (
            <button key={i} type="button" onClick={() => { setQuery(ex.query || ''); present(ex) }}
              className="border border-border px-2.5 py-1 text-muted hover:text-accent hover:border-accent rounded-[3px] transition-colors">{`example ${i + 1}`}</button>
          ))}
        </div>

        {/* EMPTY */}
        {status === 'empty' && (
          <div className="border-t border-border mt-8 pt-16 pb-8 text-center">
            <p className="text-text text-[17px]">Ask a question to verify an answer.</p>
            <p className="text-muted text-[14px] mt-2 max-w-[52ch] mx-auto">Each claim is checked against the retrieved context and marked <span className="text-supported-fg">supported</span> or <span className="text-unsupported-fg">unsupported</span> — then unsupported claims are dropped.</p>
          </div>
        )}

        {/* LOADING */}
        {status === 'loading' && (
          <div className="border-t border-border mt-8 pt-16 pb-8 text-center">
            <p className="text-text text-[17px]">Verifying…</p>
            <p className="text-muted text-[14px] mt-2">Generation runs locally on CPU — this can take a minute. The first request also loads the model.</p>
            <div className="flex justify-center gap-3 mt-6 font-mono text-[12px] uppercase tracking-[0.06em]">
              {['retrieve', 'generate', 'verify'].map((s, k) => (
                <span key={s} style={{ color: k < step ? 'var(--color-supported-fg)' : k === step ? 'var(--color-accent)' : 'var(--color-muted)' }}>{s}{k < 2 && <span className="text-border ml-3">→</span>}</span>
              ))}
            </div>
            <p className="font-mono text-[12px] text-muted mt-5 tnum" aria-live="polite">elapsed {elapsed}s</p>
          </div>
        )}

        {/* ERROR */}
        {status === 'error' && (
          <div className="border-t border-border mt-8 pt-16 pb-8 text-center">
            <p className="text-unsupported-fg text-[17px]">Couldn&rsquo;t complete the request.</p>
            <p className="text-muted text-[14px] mt-2 max-w-[52ch] mx-auto">{error}</p>
          </div>
        )}

        {/* RESULT — bento */}
        {status === 'out' && data && (
          <div className="grid md:grid-cols-3 gap-4 mt-8">

            {/* Calibration — full width */}
            <Tile label="Calibration · drag to trade precision against recall" className="md:col-span-3">
              <div className="flex items-end justify-between mb-4" aria-live="polite">
                <span className="font-mono tnum text-[2rem] leading-none text-text">{pct}%</span>
                <span className="font-mono text-[12px] text-muted tnum text-right">{nSup} of {claims.length} supported<br />threshold <span className="text-accent">{threshold.toFixed(2)}</span></span>
              </div>
              <div className="relative h-6">
                <input type="range" min={0} max={1} step={0.01} value={threshold} onChange={(e) => setThreshold(parseFloat(e.target.value))}
                  aria-label="Support-score threshold" aria-valuetext={`${threshold.toFixed(2)} — ${pct}% of claims supported`}
                  className="thumb-brass absolute inset-0 w-full h-full" />
                {/* fill (left of thumb) + per-claim ticks, drawn on top, non-interactive */}
                <div className="absolute top-1/2 -translate-y-1/2 left-0 h-[3px] rounded pointer-events-none" style={{ width: `${threshold * 100}%`, background: 'var(--color-supported-fg)', opacity: 0.55 }} />
                {claims.map((c, i) => (
                  <span key={i} title={`score ${c.support.toFixed(2)}`} className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-[2px] h-3.5 rounded-sm pointer-events-none"
                    style={{ left: `${c.support * 100}%`, background: supported(c.support) ? 'var(--color-supported-fg)' : 'var(--color-unsupported-fg)' }} />
                ))}
              </div>
              <div className="flex justify-between font-mono text-[10px] tracking-[0.04em] uppercase text-muted mt-3"><span>0.00 · not in context</span><span>1.00 · grounded</span></div>
            </Tile>

            {/* Claims — 2/3 */}
            <Tile label="Answer · claim by claim" className="md:col-span-2">
              {claims.map((c, i) => {
                const sup = supported(c.support)
                const ev = cleanEvidence(c.evidence)
                return (
                  <div key={i} className="pl-4 py-3 border-l-[3px] transition-colors duration-300" style={{ borderColor: sup ? 'var(--color-supported)' : 'var(--color-unsupported)' }}>
                    <div className="flex items-start gap-4">
                      <span className="flex-1 text-[14px] leading-relaxed" style={{ color: sup ? 'var(--color-text)' : 'var(--color-muted)', textDecoration: sup ? 'none' : 'line-through', textDecorationColor: 'rgba(235,87,87,0.35)' }}>{c.text}</span>
                      <span className="font-mono text-[10px] uppercase tracking-[0.06em] pt-1 w-[68px] text-right shrink-0" style={{ color: sup ? 'var(--color-supported-fg)' : 'var(--color-unsupported-fg)' }}>{sup ? 'supported' : 'dropped'}</span>
                      <span className="font-mono tnum text-[15px] pt-0.5 w-12 text-right shrink-0" style={{ color: sup ? 'var(--color-supported-fg)' : 'var(--color-unsupported-fg)' }}>{c.support.toFixed(2)}</span>
                    </div>
                    {ev && (
                      <>
                        <button type="button" onClick={() => setOpen(open === i ? null : i)} aria-expanded={open === i}
                          className="font-mono text-[11px] text-muted hover:text-accent mt-2">{open === i ? '▾' : '▸'} evidence</button>
                        {open === i && (
                          <div className="mt-2 p-3 bg-bg border border-border rounded-[4px]">
                            <div className="font-mono text-[10px] uppercase tracking-[0.06em] text-muted mb-1.5">closest passage in the retrieved context</div>
                            <p className="text-[13px] text-muted leading-relaxed">{ev.slice(0, 600)}{ev.length > 600 ? '…' : ''}</p>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )
              })}
            </Tile>

            {/* Corrected — 1/3 */}
            <Tile label="Corrected answer" className="md:col-span-1">
              <div className="flex gap-5 border-b border-border mb-4">
                {(['clean', 'annotated'] as const).map((v) => (
                  <button key={v} type="button" onClick={() => setView(v)}
                    className="font-mono text-[12px] tracking-[0.04em] uppercase pb-2 -mb-px border-b-2 transition-colors"
                    style={{ color: view === v ? 'var(--color-text)' : 'var(--color-muted)', borderColor: view === v ? 'var(--color-accent)' : 'transparent' }}>
                    {v === 'clean' ? 'corrected' : 'annotated'}
                  </button>
                ))}
              </div>
              <p className="text-[15px] leading-[1.7] text-text">
                {view === 'annotated'
                  ? claims.map((c, i) => <span key={i} style={{ color: supported(c.support) ? 'var(--color-text)' : 'var(--color-muted)', textDecoration: supported(c.support) ? 'none' : 'line-through' }}>{c.text}{' '}</span>)
                  : (kept.length ? kept.join(' ') : "I can't answer this from the provided context.")}
              </p>
              <div className="font-mono text-[11px] text-muted mt-5 pt-4 border-t border-border leading-relaxed">
                {data.sources.map((s) => s.source).join(', ')}{data.note ? ` · ${data.note}` : ''}
              </div>
            </Tile>
          </div>
        )}

        <footer className="border-t border-border mt-10 pt-6">
          <p className="font-mono text-[11px] text-muted">A faithfulness instrument — it checks grounding in the retrieved evidence, not world-truth.</p>
        </footer>
      </div>
    </div>
  )
}
