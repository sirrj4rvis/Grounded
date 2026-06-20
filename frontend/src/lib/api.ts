// API layer + shared types. Talks to the existing FastAPI backend
// (proxied in dev by vite.config.ts; same-origin in production).

export type Claim = {
  text: string
  support: number
  supported?: boolean
  evidence?: string
  gt_hallucination?: boolean
}

export type Verification = {
  query: string
  answer: string
  corrected: string
  groundedness: number
  abstained: boolean
  threshold: number
  claims: Claim[]
  sources: { id: string; source: string }[]
  note?: string
}

export async function fetchExamples(): Promise<Verification[]> {
  const r = await fetch('/examples')
  if (!r.ok) return []
  return r.json()
}

export async function ask(query: string): Promise<Verification> {
  const r = await fetch('/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!r.ok) {
    const detail = await r.json().catch(() => ({}))
    throw new Error((detail as { detail?: string }).detail || r.statusText)
  }
  return r.json()
}

// RAGTruth context windows arrive as JSON ({question, passages}); show readable text.
export function cleanEvidence(s?: string): string {
  if (!s) return ''
  if (s.trim()[0] === '{') {
    try {
      const o = JSON.parse(s) as Record<string, unknown>
      return Object.values(o)
        .filter((v) => typeof v === 'string')
        .join('  ')
        .trim()
    } catch {
      /* fall through */
    }
  }
  return s
}
