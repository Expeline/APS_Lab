import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = fileURLToPath(new URL('../', import.meta.url))
const backend = resolve(frontend, '../backend')
const windows = process.platform === 'win32'
const python = resolve(backend, windows ? '.venv/Scripts/python.exe' : '.venv/bin/python')
if (!existsSync(python)) {
  console.error('Сначала создайте backend/.venv и установите зависимости по README.')
  process.exit(1)
}

const children = [
  spawn(python, ['-m', 'uvicorn', 'app.main:app', '--port', '8000'],
    { cwd: backend, stdio: 'inherit' }),
  spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', 'localhost', '--strictPort', '--open'],
    { cwd: frontend, stdio: 'inherit' }),
]
let stopping = false
function stop(code) {
  if (stopping) return
  stopping = true
  process.exitCode = code
  for (const child of children) {
    if (child.exitCode === null && child.signalCode === null) child.kill()
  }
}
for (const child of children) {
  child.on('exit', (code) => stop(code ?? 1))
  child.on('error', (error) => { console.error(error.message); stop(1) })
}
process.on('SIGINT', () => stop(0))
process.on('SIGTERM', () => stop(0))
