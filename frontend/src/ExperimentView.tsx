import { useState } from 'react'
import type { Config, Economics, Experiments } from './api'
import { NumberField } from './Configuration'
import { exportCsv } from './data'
import { Table } from './Table'

type Resource = { capacity: number; workers: number }
function resources(config: Config): Resource[] {
  const workers = config.workers === 50 ? 49 : config.workers + 1
  const capacity = config.capacity > 198 ? config.capacity - 2 : config.capacity + 2
  return [
    { workers: config.workers, capacity: config.capacity },
    { workers, capacity: config.capacity },
    { workers: config.workers, capacity },
    { workers, capacity },
  ]
}

export function ExperimentView({ config, busy, error, result, compare }: {
  config: Config; busy: boolean; error: string; result: Experiments | null
  compare: (options: Config[], costs: Economics) => void
}) {
  const [overrides, setOverrides] = useState<Record<number, Partial<Resource>>>({})
  const [costs, setCosts] = useState<Economics>({ price: 0, workerHour: 0, slotHour: 0, secondsPerUnit: 1 })
  const options = resources(config).map((resource, index) => ({ ...config, ...resource, ...overrides[index] }))
  const update = (index: number, key: keyof Resource, value: number) =>
    setOverrides(previous => ({ ...previous, [index]: { ...previous[index], [key]: value } }))
  const costFields: [keyof Economics, string][] = [
    ['price', 'Цена одной обработки'], ['workerHour', 'Цена прибора в час'],
    ['slotHour', 'Цена ячейки в час'], ['secondsPerUnit', 'Секунд в единице времени'],
  ]
  return <>
    <p className="muted">Источники, среднее обслуживание, N и seed берутся из вкладки «Параметры».</p>
    {error && <p className="callout">Исправьте параметры базовой конфигурации. {error}</p>}
    <form onSubmit={event => { event.preventDefault(); compare(options, costs) }}>
      <section className="surface">
        <h3>Конфигурации</h3>
        <div className="fields four">{options.map((option, index) => <fieldset key={index}>
          <legend>Конфигурация {index + 1}</legend>
          <NumberField label="Приборы M" value={option.workers} change={value => update(index, 'workers', value)} min={1} max={50} />
          <NumberField label="Буфер B" value={option.capacity} change={value => update(index, 'capacity', value)} min={1} max={200} />
        </fieldset>)}</div>
      </section>
      <section className="surface">
        <h3>Экономические допущения</h3>
        <div className="fields four">{costFields.map(([key, label]) =>
          <NumberField key={key} label={label} value={costs[key]} change={value => setCosts({ ...costs, [key]: value })}
            min={key === 'secondsPerUnit' ? .001 : 0} max={key === 'secondsPerUnit' ? 1e6 : 1e9} step="any" />
        )}</div>
        <p className="muted">Затраты начисляются на все приборы и ячейки за длительность прогона. Критерии отбора: Pотк ≤ 10%, загрузка 85–95%.</p>
      </section>
      <button className="primary" disabled={busy || !!error}>Сравнить конфигурации</button>
    </form>
    {result && <>
      <Table title="Сравнение конфигураций" rows={result.rows} />
      <p className="note">{result.message}</p>
      <button onClick={() => exportCsv('comparison.csv', result.rows)}>Сравнение CSV</button>
    </>}
  </>
}
