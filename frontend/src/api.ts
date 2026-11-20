import type { VariantState } from './variant'

export type Cell = string | number | boolean | null
export type Row = Record<string, Cell>
export type Config = {
  n: number
  intervals: [number, number][]
  workers: number
  capacity: number
  meanService: number
  limit: number
  seed: number
}
export type Snapshot = VariantState & {
  modelTime: number
  event: string
  workerPointer: number
  generated: number
  waiting: number
  running: number
  completed: number
  rejected: number
  loss: number
  calendar: Row[]
  sources: Row[]
  slots: Row[]
  workers: Row[]
  actions: Row[]
  history: Row[]
  lastEviction: Row | null
  finished: boolean
}
export type Session = { id: string; snapshot: Snapshot }
export type Summary = { Общие: Row; Источники: Row[]; Приборы: Row[] }
export type AutoResult = {
  summary: Summary
  journal: Row[]
  attempts: Row[]
  message: string
}
export type Economics = { price: number; workerHour: number; slotHour: number; secondsPerUnit: number }
export type Experiments = { rows: Row[]; message: string; best: Row | null }

async function post<T>(path: string, data?: object): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api/${path}`, {
      method: 'POST',
      ...(data && { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
    })
  } catch {
    throw new Error('Не удалось связаться с сервером. Проверьте запуск FastAPI на порту 8000.')
  }
  const isJson = response.headers.get('Content-Type')?.includes('application/json')
  if (!response.ok || !isJson) {
    const detail = isJson ? (await response.json()).detail : null
    throw new Error(typeof detail === 'string' ? detail : 'Сервер не выполнил запрос. Проверьте FastAPI.')
  }
  return response.json()
}

export const api = {
  create: (configuration: Config, demo: boolean) => post<Session>('simulations', { configuration, demo }),
  step: (id: string, count: number) => post<Session & { result?: AutoResult }>(`simulations/${id}/step`, { count }),
  finish: (id: string) => post<Session & { result: AutoResult }>(`simulations/${id}/run`),
  auto: (configuration: Config, demo: boolean, adaptive: boolean, cap: number) =>
    post<AutoResult>('auto', { configuration, demo, adaptive, cap }),
  compare: (configuration: Config, configurations: Config[], costs: Economics) =>
    post<Experiments>('experiments', { configuration, configurations, ...costs }),
}
