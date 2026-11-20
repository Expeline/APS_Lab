import type { Row, Snapshot } from './api'
import { Table } from './Table'

export const identity = {
  title: 'Центр обработки заданий рендеринга',
  student: 'Калашян Артур · 5130904/40102 · Вариант 24',
  formula: 'ИБ ИЗ2 ПЗ1 Д1ОЗ3 Д1ОО2 Д2П2 Д2Б5 ОР1 ОД3',
  free: 'Свободная система',
  overflow: 'Переполнение',
  demo: 'Пакеты и приоритеты',
}

export type VariantState = { batch: Row | null; last_batch: Row | null }
export function SourceType(_props: { index: number }) { return null }
export function BufferPointer(_snapshot: Snapshot, _row: Row) { return false }

export function VariantPanel({ snapshot }: { snapshot: Snapshot }) {
  return <section className="variant-panel">
    <p className="muted">Д2Б5 · состав пакета фиксируется при открытии.</p>
    <Table title="Активный пакет" rows={snapshot.batch ? [snapshot.batch] : []} empty="Активного пакета нет." />
    {snapshot.last_batch && <Table title="Последний закрытый пакет" rows={[snapshot.last_batch]} />}
  </section>
}
