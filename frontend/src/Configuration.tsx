import type { Config } from './api'
import { identity, SourceType } from './variant'

export const baseConfig: Config = {
  n: 3, intervals: [[1, 3], [2, 4], [3, 5]], workers: 3, capacity: 5,
  meanService: 2, limit: 100, seed: 42,
}

export const presets: Record<string, Config> = {
  base: baseConfig,
  free: { ...baseConfig, n: 2, intervals: [[5, 8], [6, 9]], meanService: .25, limit: 30 },
  overflow: { ...baseConfig, workers: 1, capacity: 2, meanService: 7 },
}

export function NumberField({ label, value, change, min, max, step = 1 }: {
  label: string; value: number; change: (value: number) => void
  min: number; max: number; step?: number | 'any'
}) {
  return <label className="field">
    <span>{label}</span>
    <input type="number" min={min} max={max} step={step} required
      value={Number.isNaN(value) ? '' : value} onChange={event => change(event.target.valueAsNumber)} />
  </label>
}

export function validation(config: Config) {
  if (!Number.isInteger(config.n) || config.n < 1 || config.n > 20) return 'Укажите от 1 до 20 источников.'
  if (config.intervals.some(([a, b]) => !Number.isFinite(a) || !Number.isFinite(b) || a < .001 || b < a || b > 1e6)) {
    return 'Для каждого источника требуется 0,001 ≤ a ≤ b ≤ 1 000 000.'
  }
  const integers: [number, number, number][] = [
    [config.workers, 1, 50], [config.capacity, 1, 200],
    [config.limit, 1, 50000], [config.seed, 0, 2147483647],
  ]
  if (integers.some(([value, min, max]) => !Number.isInteger(value) || value < min || value > max)
    || !Number.isFinite(config.meanService) || config.meanService < .001 || config.meanService > 1e6) {
    return 'Проверьте диапазоны параметров приборов, буфера и прогона.'
  }
  return ''
}

export function Configuration({ config, setConfig, demo, preset, setPreset, adaptive, setAdaptive, cap, setCap }: {
  config: Config; setConfig: (value: Config) => void; demo: boolean
  preset: string; setPreset: (value: string) => void
  adaptive: boolean; setAdaptive: (value: boolean) => void; cap: number; setCap: (value: number) => void
}) {
  const update = (key: Exclude<keyof Config, 'n' | 'intervals'>, value: number) => setConfig({ ...config, [key]: value })
  const resize = (n: number) => {
    const intervals = Number.isInteger(n) && n >= 1 && n <= 20
      ? Array.from({ length: n }, (_, index) => config.intervals[index] ?? [1, 3] as [number, number])
      : config.intervals
    setConfig({ ...config, n, intervals })
  }
  function updateInterval(index: number, bound: 0 | 1, value: number) {
    const intervals = config.intervals.map((pair, i): [number, number] =>
      i === index ? (bound === 0 ? [value, pair[1]] : [pair[0], value]) : pair)
    setConfig({ ...config, intervals })
  }
  return <>
    <label className="field preset">
      <span>Демонстрационный сценарий</span>
      <select value={preset} onChange={event => setPreset(event.target.value)}>
        <option value="base">Базовая конфигурация</option>
        <option value="free">{identity.free}</option>
        <option value="overflow">{identity.overflow}</option>
        <option value="demo">{identity.demo} · фиксированная трасса</option>
      </select>
    </label>
    {demo ? <p className="note">Поступления и длительности заданы заранее.</p> :
      <div className="setup-grid">
        <section className="surface">
          <h3>Источники</h3>
          <p className="muted">ИЗ2 · равномерный интервал [a, b]</p>
          <NumberField label="Число источников" value={config.n} change={resize} min={1} max={20} />
          <div className="source-list">{config.intervals.map(([a, b], index) =>
            <fieldset className="source" key={index}>
              <legend>И{index + 1}</legend>
              <SourceType index={index} />
              <div className="fields two">
                <NumberField label={`И${index + 1} · a`} value={a} change={value => updateInterval(index, 0, value)} min={.001} max={1e6} step="any" />
                <NumberField label={`И${index + 1} · b`} value={b} change={value => updateInterval(index, 1, value)} min={.001} max={1e6} step="any" />
              </div>
            </fieldset>
          )}</div>
        </section>
        <section className="surface">
          <h3>Приборы и буфер</h3>
          <p className="muted">ПЗ1 · экспоненциальное время со средним 1/μ</p>
          <div className="fields two">
            <NumberField label="Число приборов" value={config.workers} change={value => update('workers', value)} min={1} max={50} />
            <NumberField label="Ячейки буфера" value={config.capacity} change={value => update('capacity', value)} min={1} max={200} />
          </div>
          <NumberField label="Среднее время обслуживания" value={config.meanService} change={value => update('meanService', value)} min={.001} max={1e6} step="any" />
          <hr />
          <h3>Параметры прогона</h3>
          <div className="fields two">
            <NumberField label="Лимит заявок N" value={config.limit} change={value => update('limit', value)} min={1} max={50000} />
            <NumberField label="Начальное число (seed)" value={config.seed} change={value => update('seed', value)} min={0} max={2147483647} />
          </div>
          <label className="check"><input type="checkbox" checked={adaptive} onChange={event => setAdaptive(event.target.checked)} />
            Подобрать N по оценке точности для автоматического прогона
          </label>
          {adaptive && <NumberField label="Предельное N" value={cap} change={setCap} min={100} max={50000} />}
        </section>
      </div>}
  </>
}
