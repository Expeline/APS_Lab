import type { Row } from './api'
import { display } from './data'

export function Table({ title, rows, empty = 'Пока нет данных.' }: {
  title: string; rows: Row[]; empty?: string
}) {
  const columns = Object.keys(rows[0] ?? {})
  return <section className="table-section" aria-label={title}>
    <h3>{title}</h3>
    {rows.length ? <div className="table-scroll" tabIndex={0} aria-label={title}>
      <table aria-label={title}>
        <thead><tr>{columns.map(key => <th key={key} scope="col">{key}</th>)}</tr></thead>
        <tbody>{rows.map((row, index) =>
          <tr key={index}>{columns.map(key => <td key={key}>{display(row[key], key)}</td>)}</tr>
        )}</tbody>
      </table>
    </div> : <p className="muted">{empty}</p>}
  </section>
}
