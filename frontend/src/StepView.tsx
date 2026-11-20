import type { Session, Snapshot } from './api'
import { display } from './data'
import { Table } from './Table'
import { BufferPointer, VariantPanel } from './variant'

function StateMap({ snapshot }: { snapshot: Snapshot }) {
  return <section className="state-map" aria-label="Схема СМО">
    <article><h3>Источники</h3>
      <div className="tiles">{snapshot.sources.map(row =>
        <div className="tile" key={String(row.Источник)}>
          <strong>И{row.Источник}</strong><span>Создано {row.Создано}</span>
          <small>Следующий · {display(row['Следующий приход'])}</small>
        </div>
      )}</div>
    </article>
    <article><h3>Буфер</h3>
      <div className="tiles">{snapshot.slots.map(row => {
        const pointer = BufferPointer(snapshot, row)
        return <div className={`tile ${row.Заявка !== '—' ? 'occupied' : ''} ${pointer ? 'pointer' : ''}`} key={String(row.Ячейка)}>
          <strong>Ячейка {row.Ячейка}</strong><span>{row.Заявка === '—' ? 'Свободна' : row.Заявка}</span>
          {pointer && <small>Указатель буфера</small>}
        </div>
      })}</div>
    </article>
    <article><h3>Приборы</h3>
      <div className="tiles">{snapshot.workers.map(row =>
        <div className={`tile ${row.Состояние === 'BUSY' ? 'occupied' : ''} ${row.Указатель ? 'pointer' : ''}`} key={String(row.Прибор)}>
          <strong>П{row.Прибор}</strong><span>{row.Заявка ?? 'Свободен'}</span>
          {row.Указатель && <small>Указатель приборов</small>}
        </div>
      )}</div>
    </article>
  </section>
}

const events: Record<string, string> = {
  REQUEST_GENERATED: 'Поступление заявки', SERVICE_COMPLETED: 'Завершение обслуживания',
}

export function StepView({ session, step, finish, busy }: {
  session: Session | null; step: (count: number) => void; finish: () => void; busy: boolean
}) {
  if (!session) return <p className="note">Начните пошаговый прогон на вкладке «Параметры».</p>
  const state = session.snapshot
  return <>
    <div className="runbar">
      <div><strong>t = {display(state.modelTime)}</strong>
        <span>{state.finished ? 'Прогон завершён' : events[state.event] ?? state.event}</span></div>
      <div className="buttons">
        <button className="primary" onClick={() => step(1)} disabled={busy || state.finished}>Следующее событие</button>
        <button onClick={() => step(10)} disabled={busy || state.finished}>+10 событий</button>
        <button onClick={finish} disabled={busy || state.finished}>До конца</button>
      </div>
    </div>
    <div className="metrics">
      {Object.entries({ Создано: state.generated, 'В очереди': state.waiting, 'В работе': state.running,
        Обслужено: state.completed, Отказано: state.rejected, 'Доля отказов': state.loss }).map(([label, value]) =>
        <div key={label}><span>{label}</span><strong>{display(value, label)}</strong></div>
      )}
    </div>
    <StateMap snapshot={state} />
    <p className="note">Д2П2 · указатель приборов → П{state.workerPointer}</p>
    <VariantPanel snapshot={state} />
    {state.lastEviction && <p className="callout">Последнее вытеснение · t = {display(state.lastEviction.Время)} · {state.lastEviction.Заявка} · {state.lastEviction.Подробности}</p>}
    <div className="table-grid">
      <Table title="Календарь особых событий" rows={state.calendar} empty="Календарь пуст." />
      <Table title="Журнал действий перехода" rows={state.actions} />
      <Table title="Состояние источников" rows={state.sources} />
      <Table title="Состояние приборов" rows={state.workers} />
      <Table title="Все ячейки буфера" rows={state.slots} />
      <Table title="История заявок · последние 500" rows={state.history} />
    </div>
  </>
}
