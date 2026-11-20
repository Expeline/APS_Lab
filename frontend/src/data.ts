import type { Row } from './api'

export function display(value: Row[string], key = '') {
  if (value == null || value === '') return '—'
  if (typeof value === 'number') {
    if (['Pотк', 'Kисп', 'Доля отказов', 'Отклонение K от 0,90', 'Оценка относительной погрешности'].includes(key)) {
      return new Intl.NumberFormat('ru', { style: 'percent', maximumFractionDigits: 2 }).format(value)
    }
    return new Intl.NumberFormat('ru', { maximumFractionDigits: 5 }).format(value)
  }
  if (typeof value === 'boolean') return value ? 'Да' : '—'
  return value
}

export function download(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const link = document.createElement('a')
  link.href = url
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function exportCsv(name: string, rows: Row[]) {
  const columns = Object.keys(rows[0] ?? {})
  const quote = (value: string | number | boolean | null) =>
    `"${String(value ?? '').replaceAll('"', '""')}"`
  const lines = [columns.map(quote), ...rows.map(row => columns.map(column => quote(row[column])))]
  download(name, '\ufeff' + lines.map(line => line.join(';')).join('\r\n'), 'text/csv;charset=utf-8')
}

export function exportJson(name: string, value: unknown) {
  download(name, JSON.stringify(value, null, 2), 'application/json;charset=utf-8')
}
