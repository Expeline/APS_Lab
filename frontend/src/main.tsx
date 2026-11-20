import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import { identity } from './variant'
import './styles.css'

document.title = identity.title
createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
