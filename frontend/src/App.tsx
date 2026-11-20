import { useState } from 'react'
import { api } from './api'
import type { AutoResult, Config, Economics, Experiments, Session } from './api'
import { baseConfig, Configuration, presets, validation } from './Configuration'
import { ExperimentView } from './ExperimentView'
import { Results } from './Results'
import { StepView } from './StepView'
import { identity } from './variant'

const tabs = { setup: 'Параметры', step: 'Пошагово', results: 'Итоги', experiments: 'Эксперименты' }
type Tab = keyof typeof tabs

export default function App() {
  const [tab, setTab] = useState<Tab>('setup')
  const [preset, setPreset] = useState('base')
  const [config, setConfig] = useState(baseConfig)
  const [adaptive, setAdaptive] = useState(false)
  const [cap, setCap] = useState(10000)
  const [session, setSession] = useState<Session | null>(null)
  const [result, setResult] = useState<AutoResult | null>(null)
  const [experiments, setExperiments] = useState<Experiments | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [showValidation, setShowValidation] = useState(false)
  const [resetKey, setResetKey] = useState(0)
  const demo = preset === 'demo'
  const invalid = validation(config)

  async function action(callback: () => Promise<void>) {
    setError('')
    setBusy(true)
    try {
      await callback()
    } catch (problem) {
      setError(problem instanceof Error ? problem.message : 'Не удалось выполнить запрос.')
    } finally {
      setBusy(false)
    }
  }

  function start(automatic: boolean) {
    setError('')
    setShowValidation(true)
    if (!demo && invalid) return
    if (automatic && !demo && adaptive && (!Number.isInteger(cap) || cap < 100 || cap > 50000)) {
      setError('Предельное N должно быть целым числом от 100 до 50 000.')
      return
    }
    void action(async () => {
      const settings = demo ? baseConfig : config
      if (automatic) {
        setResult(await api.auto(settings, demo, !demo && adaptive, !demo && adaptive ? cap : 10000))
        setTab('results')
      } else {
        setSession(await api.create(settings, demo))
        setTab('step')
      }
    })
  }

  function selectPreset(value: string) {
    setPreset(value)
    setShowValidation(false)
    setError('')
    if (value in presets) setConfig(presets[value])
  }

  function reset() {
    selectPreset('base')
    setSession(null)
    setResult(null)
    setExperiments(null)
    setAdaptive(false)
    setCap(10000)
    setResetKey(key => key + 1)
  }

  function compare(options: Config[], costs: Economics) {
    void action(async () => setExperiments(await api.compare(config, options, costs)))
  }

  return <>
    <header className="masthead"><div className="frame heading">
      <div className="wordmark" aria-hidden="true">APS</div>
      <div><h1>{identity.title}</h1><p>{identity.student}</p></div>
      <div className="formula">{identity.formula}</div>
    </div></header>
    <main className="frame">
      <nav className="navigation" aria-label="Режимы программы">
        {(Object.keys(tabs) as Tab[]).map(value =>
          <button key={value} type="button" aria-current={tab === value ? 'page' : undefined}
            onClick={() => { setTab(value); setError('') }} disabled={busy}>{tabs[value]}</button>
        )}
      </nav>
      {busy && <p className="note" role="status">Выполняется запрос…</p>}
      {error && <p className="callout" role="alert">{error}</p>}
      <section className="workspace" aria-labelledby="page-heading">
        <h2 id="page-heading">{tab === 'setup' ? 'Настройка модели' : tabs[tab]}</h2>
        <div hidden={tab !== 'setup'}>
          <Configuration key={resetKey} {...{ config, setConfig, demo, preset, adaptive, setAdaptive, cap, setCap }} setPreset={selectPreset} />
          {!demo && showValidation && invalid && <p className="callout" role="alert">{invalid}</p>}
          <div className="buttons controls">
            <button className="primary" disabled={busy} onClick={() => start(false)}>Начать пошагово</button>
            <button disabled={busy} onClick={() => start(true)}>Запустить автоматически</button>
            <button className="quiet" disabled={busy} onClick={reset}>Сбросить</button>
          </div>
        </div>
        {tab === 'step' && <StepView session={session} busy={busy}
          step={count => { if (session) void action(async () => {
            const next = await api.step(session.id, count)
            setSession(next)
            if (next.result) setResult(next.result)
          }) }}
          finish={() => { if (session) void action(async () => {
            const end = await api.finish(session.id)
            setSession(end)
            setResult(end.result)
          }) }} />}
        {tab === 'results' && <Results result={result} />}
        <div hidden={tab !== 'experiments'}><ExperimentView key={resetKey}
          config={config} busy={busy} error={invalid} result={experiments} compare={compare} /></div>
      </section>
    </main>
  </>
}
