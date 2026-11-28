import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, BarChart3, CheckCircle2, FileCheck2, Shield } from 'lucide-react'
import { Emblem, Wordmark } from '../components/common/Logo'
import { ErrorState, Skeleton } from '../components/common/ui'
import { useMaybeAuth } from '../context/AuthContext'
import { useAsync } from '../hooks/useAsync'
import { systemService, type EvalMetrics, type EvalRetrievalSuite, type EvalSafetySuite } from '../services'

const pct = (v: number) => `${(v * 100).toFixed(1)}%`

function MetricRow({ label, m }: { label: string; m: EvalMetrics }) {
  return (
    <tr className="border-t border-line/70">
      <th scope="row" className="py-2.5 pr-3 text-left font-medium text-ink capitalize">{label.replace(/_/g, ' ')}</th>
      <td className="num px-2 py-2.5 text-right text-ink-2">{m.cases}</td>
      <td className="num px-2 py-2.5 text-right font-semibold text-ink">{pct(m['hit@1'])} <span className="text-xs font-normal text-ink-3">({m['hit@1']})</span></td>
      <td className="num px-2 py-2.5 text-right text-ink-2">{pct(m['hit@3'])}</td>
      <td className="num px-2 py-2.5 text-right text-ink-2">{pct(m['hit@6'])}</td>
      <td className="num py-2.5 pl-2 text-right font-medium text-ink">{m.mrr.toFixed(3)}</td>
    </tr>
  )
}

function RetrievalBreakdown({ suite, mode }: { suite: EvalRetrievalSuite; mode: 'appliance_selected' | 'appliance_detected' }) {
  const split = suite[mode]
  const langs = Object.entries(split.by_language)
  const apps = Object.entries(split.by_appliance)

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <div className="rounded-xl border border-line bg-surface-2/45 p-3">
          <p className="text-xs text-ink-3">Cases</p>
          <p className="num font-display mt-1 text-2xl text-ink">{split.overall.cases}</p>
        </div>
        <div className="rounded-xl border border-line bg-surface-2/45 p-3">
          <p className="text-xs text-ink-3">Hit@1</p>
          <p className="num font-display mt-1 text-2xl text-accent">{pct(split.overall['hit@1'])}</p>
          <p className="num text-[11px] text-ink-3">raw {split.overall['hit@1']}</p>
        </div>
        <div className="rounded-xl border border-line bg-surface-2/45 p-3">
          <p className="text-xs text-ink-3">Hit@3</p>
          <p className="num font-display mt-1 text-2xl text-ink">{pct(split.overall['hit@3'])}</p>
          <p className="num text-[11px] text-ink-3">raw {split.overall['hit@3']}</p>
        </div>
        <div className="rounded-xl border border-line bg-surface-2/45 p-3">
          <p className="text-xs text-ink-3">Hit@6</p>
          <p className="num font-display mt-1 text-2xl text-ink">{pct(split.overall['hit@6'])}</p>
          <p className="num text-[11px] text-ink-3">raw {split.overall['hit@6']}</p>
        </div>
        <div className="rounded-xl border border-line bg-surface-2/45 p-3">
          <p className="text-xs text-ink-3">MRR</p>
          <p className="num font-display mt-1 text-2xl text-ink">{split.overall.mrr.toFixed(3)}</p>
          <p className="num text-[11px] text-ink-3">Detect {pct(suite.appliance_detection_accuracy)}</p>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="overflow-x-auto rounded-xl border border-line bg-bg/40 p-3.5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-3">By language</p>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-ink-3">
                <th scope="col" className="pb-2 pr-3 text-left font-medium">Language</th>
                <th scope="col" className="px-2 pb-2 text-right font-medium">Cases</th>
                <th scope="col" className="px-2 pb-2 text-right font-medium">Hit@1</th>
                <th scope="col" className="px-2 pb-2 text-right font-medium">Hit@3</th>
                <th scope="col" className="px-2 pb-2 text-right font-medium">Hit@6</th>
                <th scope="col" className="pb-2 pl-2 text-right font-medium">MRR</th>
              </tr>
            </thead>
            <tbody>{langs.map(([k, v]) => <MetricRow key={k} label={k} m={v} />)}</tbody>
          </table>
        </div>

        <div className="overflow-x-auto rounded-xl border border-line bg-bg/40 p-3.5">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-3">By appliance</p>
          <table className="w-full text-xs">
            <thead>
              <tr className="text-ink-3">
                <th scope="col" className="pb-2 pr-3 text-left font-medium">Appliance</th>
                <th scope="col" className="px-2 pb-2 text-right font-medium">Cases</th>
                <th scope="col" className="px-2 pb-2 text-right font-medium">Hit@1</th>
                <th scope="col" className="px-2 pb-2 text-right font-medium">Hit@3</th>
                <th scope="col" className="px-2 pb-2 text-right font-medium">Hit@6</th>
                <th scope="col" className="pb-2 pl-2 text-right font-medium">MRR</th>
              </tr>
            </thead>
            <tbody>{apps.map(([k, v]) => <MetricRow key={k} label={k} m={v} />)}</tbody>
          </table>
        </div>
      </div>

      {split.misses_top3.length > 0 && (
        <div className="rounded-xl border border-warn/40 bg-warn/10 p-3.5 text-xs">
          <p className="font-semibold text-warn">Outside top-3 ({split.misses_top3.length})</p>
          <ul className="mt-2 space-y-2">
            {split.misses_top3.map(miss => (
              <li key={miss.id} className="rounded-lg border border-line bg-surface px-3 py-2">
                <p className="font-medium text-ink"><span className="num font-mono text-ink-3">{miss.id}</span> · rank {miss.rank}: “{miss.query}”</p>
                <p className="mt-0.5 text-ink-2">Top 3 returned: {miss.top3.join(', ')}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {suite.appliance_detection_misses.length > 0 && (
        <div className="rounded-xl border border-line bg-surface-2/40 p-3.5 text-xs">
          <p className="font-semibold text-ink-2">
            Appliance detection misses ({suite.appliance_detection_misses.length}) · Accuracy {pct(suite.appliance_detection_accuracy)} ({suite.appliance_detection_accuracy})
          </p>
          <ul className="mt-2 space-y-1.5">
            {suite.appliance_detection_misses.map(miss => (
              <li key={miss.id} className="text-ink-2">
                <span className="num font-mono text-ink-3">{miss.id}</span>: “{miss.query}” — expected <span className="font-medium text-ink">{miss.expected}</span>, got <span className="font-medium text-warn">{miss.got}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function SafetyBlock({ title, sf }: { title: string; sf: EvalSafetySuite }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold text-ink">{title}</h3>
        <span className="num rounded-full border border-line bg-surface-2 px-2.5 py-0.5 text-xs text-ink-2">{sf.cases} test sentences</span>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-xl border border-line bg-surface-2/45 p-3">
          <p className="text-xs text-ink-3">Unsafe withheld</p>
          <p className="num font-display mt-1 text-2xl text-accent">{sf.unsafe_withheld}</p>
        </div>
        <div className="rounded-xl border border-line bg-surface-2/45 p-3">
          <p className="text-xs text-ink-3">Unsafe recall</p>
          <p className="num font-display mt-1 text-2xl text-ink">{pct(sf.recall_unsafe)}</p>
          <p className="num text-[11px] text-ink-3">raw {sf.recall_unsafe}</p>
        </div>
        <div className="rounded-xl border border-line bg-surface-2/45 p-3">
          <p className="text-xs text-ink-3">Safe shown</p>
          <p className="num font-display mt-1 text-2xl text-ink">{sf.safe_shown}</p>
        </div>
        <div className="rounded-xl border border-line bg-surface-2/45 p-3">
          <p className="text-xs text-ink-3">False positive rate</p>
          <p className="num font-display mt-1 text-2xl text-ink">{pct(sf.false_positive_rate)}</p>
          <p className="num text-[11px] text-ink-3">raw {sf.false_positive_rate}</p>
        </div>
      </div>
      {sf.errors.length > 0 && (
        <div className="rounded-xl border border-warn/40 bg-warn/10 p-3.5 text-xs">
          <p className="font-semibold text-warn">Recorded filter errors ({sf.errors.length})</p>
          <ul className="mt-2 space-y-1.5">
            {sf.errors.map(er => (
              <li key={er.id} className="rounded-lg border border-line bg-surface px-3 py-2 text-ink-2">
                <span className="num font-mono text-ink-3">{er.id}</span>: “{er.text}” — expected <span className="font-medium text-ink">{er.expected}</span>, withheld: <span className="font-medium text-warn">{String(er.withheld)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default function EvaluationPage() {
  const auth = useMaybeAuth()
  const { data, loading, error, retry } = useAsync(() => systemService.evaluation(), [])
  const [mode, setMode] = useState<'appliance_selected' | 'appliance_detected'>('appliance_selected')

  return (
    <div className="min-h-dvh bg-bg text-ink">
      <header className="border-b border-line bg-surface/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-3.5 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <Emblem height={34} />
            <Wordmark height={16} />
          </Link>
          <div className="flex flex-wrap items-center gap-2">
            {auth?.user ? (
              <Link to="/" className="btn btn-sm !min-h-[44px]"><ArrowLeft size={14} />Back to workspace</Link>
            ) : (
              <Link to="/login" className="btn btn-primary btn-sm !min-h-[44px]">Sign in</Link>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-7 sm:px-6">
        <section className="space-y-2">
          <p className="section-label">Public benchmark report</p>
          <h1 className="font-display text-2xl sm:text-3xl">Retrieval &amp; Safety Evaluation</h1>
          <p className="max-w-3xl text-sm leading-relaxed text-ink-2">
            Rendered directly from <code className="rounded bg-surface-2 px-1.5 py-0.5 text-xs">docs/EVALUATION_RESULTS.json</code> via{' '}
            <code className="rounded bg-surface-2 px-1.5 py-0.5 text-xs">/api/v1/evaluation</code>. No invented metrics; misses and false positives are shown alongside passes.
          </p>
        </section>

        {loading && (
          <div className="space-y-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-52" />
            <Skeleton className="h-64" />
          </div>
        )}
        {error && <ErrorState message={error} onRetry={retry} />}

        {data && (
          <>
            <section className="card card-pad space-y-2.5 text-sm">
              <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                <div><span className="text-xs text-ink-3">Measured on</span><p className="num font-semibold text-ink">{data.date}</p></div>
                <div><span className="text-xs text-ink-3">Channels</span><p className="font-semibold text-ink">{data.retrieval_channels}</p></div>
              </div>
              <p className="border-t border-line pt-2.5 text-xs leading-relaxed text-ink-2">{data.note}</p>
            </section>

            {/* Held-out Safety Filter */}
            <section aria-labelledby="eval-safety-h" className="card card-pad space-y-4">
              <div className="flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-surface-2 text-accent"><Shield size={16} /></span>
                <div>
                  <h2 id="eval-safety-h" className="text-base font-semibold">Held-out safety filter</h2>
                  <p className="text-xs text-ink-3">Written after the first fixes and never used to tune safety rules.</p>
                </div>
              </div>
              <SafetyBlock title={`Held-out safety (${data.held_out.safety_filter.cases} cases)`} sf={data.held_out.safety_filter} />
            </section>

            {/* Held-out v2 Retrieval */}
            <section aria-labelledby="eval-v2-h" className="card card-pad space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-surface-2 text-accent"><BarChart3 size={16} /></span>
                  <div>
                    <h2 id="eval-v2-h" className="text-base font-semibold">Held-out v2 retrieval ({data.held_out_v2.retrieval.appliance_selected.overall.cases} cases)</h2>
                    <p className="text-xs text-ink-3">Unseen test queries across 8 appliance categories and 3 query styles.</p>
                  </div>
                </div>
                <div className="inline-flex rounded-xl border border-line bg-bg/50 p-1" role="group" aria-label="Appliance mode">
                  {([
                    ['appliance_selected', 'Appliance selected'],
                    ['appliance_detected', 'Auto-detected'],
                  ] as const).map(([k, label]) => (
                    <button key={k} type="button" onClick={() => setMode(k)}
                      className={`min-h-[44px] rounded-lg px-3.5 py-1.5 text-xs font-medium transition-colors ${mode === k ? 'bg-surface text-ink shadow-[var(--shadow-card)] ring-1 ring-line-2' : 'text-ink-2 hover:text-ink'}`}>
                      {label}
                    </button>
                  ))}
                </div>
              </div>
              <RetrievalBreakdown suite={data.held_out_v2.retrieval} mode={mode} />
            </section>

            {/* Held-out v1 Retrieval */}
            <section aria-labelledby="eval-v1-h" className="card card-pad space-y-4">
              <div className="flex items-center gap-2.5">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-surface-2 text-teal"><FileCheck2 size={16} /></span>
                <div>
                  <h2 id="eval-v1-h" className="text-base font-semibold">Held-out v1 retrieval ({data.held_out.retrieval.appliance_selected.overall.cases} cases)</h2>
                  <p className="text-xs text-ink-3">Earlier held-out retrieval suite before v2 expansion.</p>
                </div>
              </div>
              <RetrievalBreakdown suite={data.held_out.retrieval} mode={mode} />
            </section>

            {/* Development set (explicitly collapsed & labelled non-held-out) */}
            <details className="card group px-5 py-4">
              <summary className="flex min-h-[44px] cursor-pointer list-none items-center justify-between gap-3 font-semibold marker:hidden">
                <span className="flex items-center gap-2">
                  <CheckCircle2 size={16} className="text-ink-3" />
                  Development set (non-held-out tuning set · {data.development.retrieval.appliance_selected.overall.cases} retrieval, {data.development.safety_filter.cases} safety)
                </span>
                <span className="text-ink-3 transition-transform group-open:rotate-45" aria-hidden>+</span>
              </summary>
              <div className="mt-4 space-y-6 border-t border-line pt-4">
                <RetrievalBreakdown suite={data.development.retrieval} mode={mode} />
                <SafetyBlock title={`Development safety (${data.development.safety_filter.cases} cases)`} sf={data.development.safety_filter} />
              </div>
            </details>
          </>
        )}
      </main>
    </div>
  )
}
