import React, { useState, useEffect } from 'react';
import './index.css';
import Dashboard from './pages/Dashboard';
import Library from './pages/Library';
import Tutor from './pages/Tutor';
import Quiz from './pages/Quiz';
import Mastery from './pages/Mastery';
import { api } from './services/api';

type Page = 'dashboard' | 'library' | 'tutor' | 'quiz' | 'mastery';

const NAV = [
  { id: 'dashboard', label: 'Dashboard', icon: '🏠' },
  { id: 'library', label: 'Library', icon: '📚' },
  { id: 'tutor', label: 'Tutor', icon: '🤖' },
  { id: 'quiz', label: 'Quiz', icon: '🧪' },
  { id: 'mastery', label: 'Mastery', icon: '📈' },
] as const;

export default function App() {
  const [page, setPage] = useState<Page>('dashboard');
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);

  useEffect(() => {
    api.health()
      .then(() => setApiOnline(true))
      .catch(() => setApiOnline(false));
  }, []);

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <nav className="sidebar">
        <div className="sidebar-logo">
          <h1>ShikshaSetu</h1>
          <p>AI Learning Platform</p>
        </div>

        <div className="sidebar-nav">
          {NAV.map(n => (
            <button
              key={n.id}
              className={`nav-item ${page === n.id ? 'active' : ''}`}
              onClick={() => setPage(n.id)}
            >
              <span className="nav-icon">{n.icon}</span>
              <span>{n.label}</span>
            </button>
          ))}
        </div>

        <div className="sidebar-status">
          <div className="status-badge">
            <div className={`status-dot ${apiOnline === true ? 'online' : apiOnline === false ? 'offline' : ''}`} />
            <span>
              {apiOnline === null ? 'Connecting…' : apiOnline ? 'Backend Online' : 'Backend Offline'}
            </span>
          </div>
          {apiOnline === false && (
            <div style={{ fontSize: '0.7rem', color: 'var(--accent-danger)', marginTop: '0.35rem' }}>
              Start backend: <code style={{ fontSize: '0.65rem' }}>uvicorn app.main:app</code>
            </div>
          )}
        </div>
      </nav>

      {/* Main content */}
      <main className="main-content">
        {page === 'dashboard' && <Dashboard onNavigate={setPage} />}
        {page === 'library' && <Library />}
        {page === 'tutor' && <Tutor />}
        {page === 'quiz' && <Quiz />}
        {page === 'mastery' && <Mastery />}
      </main>
    </div>
  );
}
