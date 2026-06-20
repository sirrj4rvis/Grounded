import { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion, animate } from 'framer-motion'
import { HERO_DEMO } from '../data/demo'

const { question, threshold, claims } = HERO_DEMO
const KEPT = claims.filter((c) => c.support >= threshold).length
const CAUGHT = claims.length - KEPT
const FINAL_PCT = Math.round((KEPT / claims.length) * 100)

/** Mono score that counts up from 0 when its claim resolves. */
function CountUp({ to, run }: { to: number; run: boolean }) {
  const [v, setV] = useState(run ? 0 : to)
  useEffect(() => {
    if (!run) { setV(to); return }
    const controls = animate(0, to, { duration: 0.4, ease: 'easeOut', onUpdate: setV })
    return () => controls.stop()
  }, [run, to])
  return <>{v.toFixed(2)}</>
}

/**
 * The signature: a self-playing verification. No card box — claim rows sit
 * directly on --bg with a 3px left-border as the only structural device.
 * This is the one place motion is allowed (the self-playing reveal + resolve).
 */
export default function VerificationReadout() {
  const reduce = useReducedMotion()
  const [resolved, setResolved] = useState<boolean[]>(() => claims.map(() => false))
  const [active, setActive] = useState<number | null>(null)
  const [done, setDone] = useState(false)
  const [runId, setRunId] = useState(0)
  const rowRefs = useRef<(HTMLDivElement | null)[]>([])
  const [scan, setScan] = useState<{ top: number; on: boolean }>({ top: -10, on: false })

  useEffect(() => {
    if (reduce) {
      setResolved(claims.map(() => true)); setActive(null); setDone(true); setScan({ top: -10, on: false })
      return
    }
    setResolved(claims.map(() => false)); setActive(null); setDone(false); setScan({ top: -10, on: false })
    const timers: number[] = []
    claims.forEach((_, i) => {
      timers.push(window.setTimeout(() => {
        setActive(i)
        const el = rowRefs.current[i]
        setScan({ top: el ? el.offsetTop : i * 44, on: true })
      }, 500 + i * 820))
      timers.push(window.setTimeout(() => {
        setResolved((prev) => { const n = [...prev]; n[i] = true; return n })
      }, 500 + i * 820 + 430))
    })
    const end = 500 + claims.length * 820 + 480
    timers.push(window.setTimeout(() => { setActive(null); setScan((s) => ({ ...s, on: false })); setDone(true) }, end))
    timers.push(window.setTimeout(() => setRunId((r) => r + 1), end + 3600))
    return () => timers.forEach((t) => clearTimeout(t))
  }, [runId, reduce])

  const keptSoFar = claims.filter((c, i) => resolved[i] && c.support >= threshold).length
  const meterPct = done ? FINAL_PCT : Math.round((keptSoFar / claims.length) * 100)

  return (
    <div>
      {/* status row */}
      <div className="flex items-center justify-between mb-4">
        <span className="font-mono text-[11px] tracking-[0.12em] uppercase flex items-center gap-2" style={{ color: done ? 'var(--color-supported-fg)' : 'var(--color-accent)' }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: done ? 'var(--color-supported-fg)' : 'var(--color-accent)' }} />
          {done ? 'verified' : 'verifying'}
        </span>
        <button type="button" onClick={() => setRunId((r) => r + 1)}
          className="font-mono text-[11px] tracking-[0.08em] uppercase text-muted hover:text-text">replay</button>
      </div>

      {/* question */}
      <div className="mb-5">
        <div className="font-mono text-[11px] tracking-[0.12em] uppercase text-muted mb-2">Question</div>
        <div className="text-text text-[17px]">{question}</div>
      </div>

      {/* claim rows — directly on --bg, left-border is the only structure */}
      <div className="relative">
        <motion.div className="absolute left-0 right-0 h-px pointer-events-none"
          style={{ background: 'var(--color-accent)', boxShadow: '0 0 8px var(--color-accent)' }}
          animate={{ top: scan.top, opacity: scan.on ? 0.9 : 0 }} transition={{ duration: 0.34, ease: [0.4, 0, 0.2, 1] }} />
        {claims.map((c, i) => {
          const isResolved = resolved[i]
          const sup = c.support >= threshold
          const isActive = active === i
          return (
            <motion.div key={i} ref={(el) => { rowRefs.current[i] = el }}
              className="flex items-start gap-4 py-3 pl-4"
              style={{ borderLeft: '3px solid transparent' }}
              animate={{
                opacity: isResolved || isActive ? 1 : 0.35,
                borderLeftColor: isResolved ? (sup ? 'var(--color-supported)' : 'var(--color-unsupported)') : 'rgba(0,0,0,0)',
              }}
              transition={{ duration: 0.3 }}>
              <span className="font-mono text-[12px] text-muted w-4 pt-1 shrink-0">{i + 1}</span>
              <span className="flex-1 text-[14px] leading-relaxed"
                style={{ color: isResolved && !sup ? 'var(--color-muted)' : 'var(--color-text)', textDecoration: isResolved && !sup ? 'line-through' : 'none', textDecorationColor: 'rgba(235,87,87,0.4)' }}>
                {c.text}
              </span>
              {isResolved && (
                <span className="font-mono text-[10px] tracking-[0.06em] uppercase pt-1 shrink-0 w-[68px] text-right" style={{ color: sup ? 'var(--color-supported-fg)' : 'var(--color-unsupported-fg)' }}>
                  {sup ? 'supported' : 'dropped'}
                </span>
              )}
              <span className="font-mono text-[15px] tnum w-12 text-right pt-0.5 shrink-0" style={{ color: !isResolved ? 'var(--color-muted)' : sup ? 'var(--color-supported-fg)' : 'var(--color-unsupported-fg)' }}>
                {isResolved ? <CountUp to={c.support} run={!reduce} /> : '··'}
              </span>
            </motion.div>
          )
        })}
      </div>

      {/* 2px grounded meter — single line, no gradient */}
      <div className="mt-6 flex items-center gap-4">
        <div className="flex-1 h-0.5 bg-border overflow-hidden">
          <motion.div className="h-full" style={{ background: 'var(--color-supported-fg)' }} animate={{ width: `${meterPct}%` }} transition={{ duration: 0.5, ease: [0.2, 0.7, 0.2, 1] }} />
        </div>
        <div className="font-mono text-[12px] text-muted tnum shrink-0">
          grounded <span className="text-text">{meterPct}%</span>{done && <span> · {KEPT} kept, {CAUGHT} caught</span>}
        </div>
      </div>
    </div>
  )
}
