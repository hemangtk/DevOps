// TaskBoard frontend - talks to the FastAPI backend over /api.
// Name: Hemang | Enrollment number: 24bcs10209
import React, { useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import './styles.css'

const API = '/api/tasks'

function App() {
  const [tasks, setTasks] = useState([])
  const [title, setTitle] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const res = await fetch(API)
      if (!res.ok) throw new Error(`GET ${API} -> ${res.status}`)
      setTasks(await res.json())
      setError('')
    } catch (e) {
      setError(`Could not reach the API: ${e.message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function addTask(e) {
    e.preventDefault()
    const text = title.trim()
    if (!text) return
    try {
      const res = await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: text, description: '' }),
      })
      if (!res.ok) throw new Error(`POST -> ${res.status}`)
      setTitle('')
      load()
    } catch (e) { setError(e.message) }
  }

  async function toggle(task) {
    try {
      await fetch(`${API}/${task.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ done: !task.done }),
      })
      load()
    } catch (e) { setError(e.message) }
  }

  async function remove(task) {
    try {
      await fetch(`${API}/${task.id}`, { method: 'DELETE' })
      load()
    } catch (e) { setError(e.message) }
  }

  const remaining = tasks.filter(t => !t.done).length

  return (
    <div className="wrap">
      <header>
        <h1>TaskBoard</h1>
        <span className="meta">Hemang · 24bcs10209</span>
      </header>
      <p className="meta">
        {loading ? 'loading…' : `${tasks.length} task${tasks.length === 1 ? '' : 's'} · ${remaining} open`}
      </p>

      <div className="card">
        <form onSubmit={addTask}>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="What needs doing?"
            aria-label="New task title"
          />
          <button type="submit">Add task</button>
        </form>
        {error && <p className="err">{error}</p>}
      </div>

      <div className="card">
        {tasks.length === 0 && !loading
          ? <p className="empty">Nothing here yet — add your first task above.</p>
          : (
            <ul>
              {tasks.map(t => (
                <li key={t.id} className={t.done ? 'done' : ''}>
                  <span className={`badge ${t.done ? 'ok' : ''}`}>#{t.id}</span>
                  <span className="title">{t.title}</span>
                  <button className="ghost" onClick={() => toggle(t)}>
                    {t.done ? 'Reopen' : 'Done'}
                  </button>
                  <button className="ghost" onClick={() => remove(t)}>Delete</button>
                </li>
              ))}
            </ul>
          )}
      </div>
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode><App /></React.StrictMode>
)
