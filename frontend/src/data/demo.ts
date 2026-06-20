import type { Claim } from '../lib/api'

// Real precomputed verification (RAGTruth · automotive pay · MiniCheck), condensed
// for the hero. Threshold 0.77: claims 1 & 3 supported (kept), 2/4/5 caught (dropped).
export const HERO_DEMO: { question: string; threshold: number; claims: Claim[] } = {
  question: 'How do automotive technicians get paid?',
  threshold: 0.77,
  claims: [
    { text: 'Automotive technicians can get paid in different ways, including hourly and commission-based pay.', support: 0.97 },
    { text: 'The highest average pay is in Alaska ($23.70/hr, $49,400/yr) and the lowest in Mississippi ($18.60/hr).', support: 0.01 },
    { text: 'Some technicians earn more in related industries such as aerospace manufacturing — about $32/hr ($66,300/yr).', support: 0.84 },
    { text: 'However, the passages do not give specific information on how technicians are typically paid.', support: 0.29 },
    { text: 'Therefore, I am unable to answer from the given passages.', support: 0.03 },
  ],
}

// Real distribution of verifier support scores across 17,213 RAGTruth-test sentences.
export const SCORE_HIST = {
  grounded: [0.24, 0.297, 0.214, 0.185, 0.158, 0.135, 0.117, 0.117, 0.112, 0.125, 0.135, 0.135, 0.168, 0.169, 0.195, 0.233, 0.281, 0.383, 0.693, 1.0],
  hallucinated: [1.0, 0.594, 0.262, 0.24, 0.142, 0.118, 0.086, 0.048, 0.064, 0.064, 0.068, 0.05, 0.044, 0.046, 0.046, 0.036, 0.056, 0.046, 0.054, 0.048],
}

export const OPERATING_POINTS = [
  { label: 'Conservative', rate: '34.9 → 20.6%', reduction: '−41%', kept: '89.5%', balanced: false },
  { label: 'Balanced', rate: '34.9 → 13.1%', reduction: '−63%', kept: '78.5%', balanced: true },
  { label: 'Aggressive', rate: '34.9 → 7.6%', reduction: '−78%', kept: '66.6%', balanced: false },
]
