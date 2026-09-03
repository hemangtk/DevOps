// Name: Hemang | Enrollment number: 24bcs10209
import React from 'react'

const styles = {
  page: {
    fontFamily: 'system-ui, sans-serif',
    display: 'grid',
    placeItems: 'center',
    height: '100vh',
    margin: 0,
    background: '#111',
    color: '#eee',
  },
  h1: { fontSize: '3rem', margin: 0 },
  p: { color: '#8cc' },
}

export default function App() {
  return (
    <div style={styles.page}>
      <div>
        <h1 style={styles.h1}>Hello World</h1>
        <p style={styles.p}>React {React.version} &middot; built with Vite &middot; served by Nginx in Docker</p>
        <p style={styles.p}>Hemang &middot; 24bcs10209</p>
      </div>
    </div>
  )
}
