// Stacks - library lending UI.
// Name: Hemang | Enrollment number: 24bcs10209
import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './styles.css'

const api = async (path, options) => {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (response.status === 204) return null
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail || 'request failed')
  return body
}

function Stats({ stats }) {
  if (!stats) return null
  const cells = [
    ['On the shelf', stats.available, 'ok'],
    ['On loan', stats.borrowed, 'warn'],
    ['Overdue', stats.overdue, stats.overdue > 0 ? 'bad' : 'ok'],
    ['Catalogue', stats.total, ''],
  ]
  return (
    <div className="stats">
      {cells.map(([label, value, tone]) => (
        <div key={label} className={`stat ${tone}`}>
          <span className="value">{value}</span>
          <span className="label">{label}</span>
        </div>
      ))}
    </div>
  )
}

function AddBook({ onAdded, onError }) {
  const blank = { title: '', author: '', isbn: '' }
  const [form, setForm] = useState(blank)
  const field = (k) => ({
    value: form[k],
    onChange: (e) => setForm({ ...form, [k]: e.target.value }),
  })

  const submit = async (e) => {
    e.preventDefault()
    try {
      await api('/books', { method: 'POST', body: JSON.stringify(form) })
      setForm(blank)
      onAdded()
    } catch (err) {
      onError(err.message)
    }
  }

  return (
    <form className="add" onSubmit={submit}>
      <input placeholder="Title" required {...field('title')} />
      <input placeholder="Author" required {...field('author')} />
      <input placeholder="ISBN (10 or 13 digits)" required {...field('isbn')} />
      <button type="submit">Shelve it</button>
    </form>
  )
}

function Row({ book, refresh, onError }) {
  const [borrower, setBorrower] = useState('')

  const act = async (body) => {
    try {
      await api(`/books/${book.id}`, { method: 'PUT', body: JSON.stringify(body) })
      setBorrower('')
      refresh()
    } catch (err) {
      onError(err.message)
    }
  }

  const withdraw = async () => {
    try {
      await api(`/books/${book.id}`, { method: 'DELETE' })
      refresh()
    } catch (err) {
      onError(err.message)
    }
  }

  return (
    <li className={book.overdue ? 'book overdue' : 'book'}>
      <div className="meta">
        <strong>{book.title}</strong>
        <span className="author">{book.author}</span>
        <code>{book.isbn}</code>
      </div>

      <div className="loan">
        {book.state === 'AVAILABLE' ? (
          <>
            <span className="badge ok">on the shelf</span>
            <input
              placeholder="Borrower"
              value={borrower}
              onChange={(e) => setBorrower(e.target.value)}
            />
            <button onClick={() => act({ state: 'BORROWED', borrower })} disabled={!borrower}>
              Lend
            </button>
            <button className="ghost" onClick={withdraw}>
              Withdraw
            </button>
          </>
        ) : (
          <>
            <span className={book.overdue ? 'badge bad' : 'badge warn'}>
              {book.overdue ? 'overdue' : 'on loan'}
            </span>
            <span className="who">
              {book.borrower} &middot; due {book.due_date}
            </span>
            <button onClick={() => act({ state: 'AVAILABLE' })}>Return</button>
          </>
        )}
      </div>
    </li>
  )
}

function App() {
  const [books, setBooks] = useState([])
  const [stats, setStats] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    try {
      const [b, s] = await Promise.all([api('/books'), api('/books/stats')])
      setBooks(b)
      setStats(s)
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  return (
    <main>
      <header>
        <h1>Stacks</h1>
        <p className="sub">A small library lending desk &middot; Hemang &middot; 24bcs10209</p>
      </header>

      <Stats stats={stats} />
      <AddBook onAdded={refresh} onError={setError} />

      {error && <p className="error">{error}</p>}

      {loading ? (
        <p className="empty">Loading the catalogue…</p>
      ) : books.length === 0 ? (
        <p className="empty">Nothing shelved yet. Add the first book above.</p>
      ) : (
        <ul className="books">
          {books.map((book) => (
            <Row key={book.id} book={book} refresh={refresh} onError={setError} />
          ))}
        </ul>
      )}
    </main>
  )
}

createRoot(document.getElementById('root')).render(<App />)
