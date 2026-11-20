import type { AutoResult } from './api'
import { exportCsv, exportJson } from './data'
import { Table } from './Table'

export function Results({ result }: { result: AutoResult | null }) {
  if (!result) return <p className="note">Запустите автоматический прогон или завершите пошаговый.</p>
  return <>
    <Table title="Общий итог" rows={[result.summary.Общие]} />
    <Table title="По источникам" rows={result.summary.Источники} />
    <Table title="По приборам" rows={result.summary.Приборы} />
    <p className="muted">Времена рассчитаны по обслуженным заявкам. Для дисперсии используется деление на n.</p>
    {result.message && <p className="note">{result.message}</p>}
    {!!result.attempts.length && <Table title="Подбор N · пилот из 100 заявок" rows={result.attempts} />}
    <div className="buttons downloads" aria-label="Выгрузка результатов">
      <button onClick={() => exportJson('summary.json', { ...result.summary, Подбор: result.attempts })}>Итоги JSON</button>
      <button onClick={() => exportCsv('summary.csv', [result.summary.Общие])}>Итоги CSV</button>
      <button onClick={() => exportCsv('sources.csv', result.summary.Источники)}>Источники CSV</button>
      <button onClick={() => exportCsv('workers.csv', result.summary.Приборы)}>Приборы CSV</button>
      <button onClick={() => exportJson('events.json', result.journal)}>Журнал JSON</button>
      <button onClick={() => exportCsv('events.csv', result.journal)}>Журнал CSV</button>
    </div>
  </>
}
