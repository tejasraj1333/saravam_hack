import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface Doc {
  document_id: string;
  filename: string;
  title: string;
  page_count: number;
  status: string;
  chunk_count: number;
  uploaded_at: string;
  error_message?: string;
  is_scanned: boolean;
}

export default function Dashboard({ onNavigate }: { onNavigate: (page: string) => void }) {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [progress, setProgress] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.health().then(setHealth).catch(() => {}),
      api.listDocuments().then(r => setDocs(r.documents || [])).catch(() => {}),
      api.getProgress().then(setProgress).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, []);

  const totalDocs = docs.length;
  const readyDocs = docs.filter(d => d.status === 'ready').length;
  const overallMastery = progress?.overall_mastery ?? 0;
  const weakCount = progress?.weak_concepts?.length ?? 0;

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>🏠 Dashboard</h2>
        <p>Welcome back! Here's your learning overview.</p>
      </div>

      {/* API Status */}
      {health && !health.sarvam_configured && (
        <div className="alert alert-warn" style={{ marginBottom: '1.5rem' }}>
          ⚠️ Sarvam API key not configured. Set <code>SARVAM_API_KEY</code> in <code>backend/.env</code> to enable AI features.
        </div>
      )}

      {/* Stats Row */}
      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        <div className="stat-card">
          <div className="stat-icon">📚</div>
          <div className="stat-value">{readyDocs}</div>
          <div className="stat-label">Documents Ready</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🎯</div>
          <div className="stat-value">{Math.round(overallMastery * 100)}%</div>
          <div className="stat-label">Overall Mastery</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⚠️</div>
          <div className="stat-value">{weakCount}</div>
          <div className="stat-label">Weak Concepts</div>
        </div>
      </div>

      {/* Main content row */}
      <div className="grid-2" style={{ marginBottom: '2rem' }}>
        {/* Recent Documents */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ fontWeight: 600 }}>Recent Documents</h3>
            <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '0.3rem 0.7rem' }}
              onClick={() => onNavigate('library')}>View All</button>
          </div>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: '2rem' }}><div className="spinner" /></div>
          ) : docs.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📄</div>
              <h3>No documents yet</h3>
              <p>Upload your study material to get started</p>
              <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={() => onNavigate('library')}>
                Upload PDF
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {docs.slice(0, 4).map(doc => (
                <div key={doc.document_id} style={{
                  display: 'flex', alignItems: 'center', gap: '0.75rem',
                  padding: '0.65rem 0.75rem', borderRadius: '8px',
                  background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                  cursor: 'pointer', transition: 'border-color 0.15s',
                }} onClick={() => onNavigate('tutor')}>
                  <span style={{ fontSize: '1.25rem' }}>
                    {doc.status === 'ready' ? '📗' : doc.status === 'error' ? '❌' : '⏳'}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 500, fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {doc.title || doc.filename}
                    </div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {doc.page_count} pages · {doc.chunk_count} chunks
                    </div>
                  </div>
                  <span className={`badge badge-${doc.status === 'ready' ? 'success' : doc.status === 'error' ? 'error' : 'warn'}`}>
                    {doc.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Learning Progress */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ fontWeight: 600 }}>Concept Mastery</h3>
            <button className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '0.3rem 0.7rem' }}
              onClick={() => onNavigate('mastery')}>Details</button>
          </div>
          {!progress || progress.concepts.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">🧠</div>
              <h3>No mastery data yet</h3>
              <p>Take a quiz to track your progress</p>
              <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={() => onNavigate('quiz')}>
                Take Quiz
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.35rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Overall Mastery</span>
                  <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{Math.round(overallMastery * 100)}%</span>
                </div>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${overallMastery * 100}%` }} />
                </div>
              </div>
              {progress.concepts.slice(0, 5).map((c: any) => (
                <div key={c.concept_id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                    <span style={{ color: 'var(--text-secondary)' }}>{c.concept_name}</span>
                    <span className={`badge badge-${
                      c.level === 'mastered' ? 'success' : c.level === 'proficient' ? 'info' :
                      c.level === 'developing' ? 'warn' : 'error'}`}>
                      {c.level}
                    </span>
                  </div>
                  <div className="mastery-bar">
                    <div className={`mastery-fill ${c.level}`} style={{ width: `${c.mastery_score * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card">
        <h3 style={{ fontWeight: 600, marginBottom: '1rem' }}>Quick Actions</h3>
        <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={() => onNavigate('tutor')}>💬 Ask Tutor</button>
          <button className="btn btn-secondary" onClick={() => onNavigate('library')}>📤 Upload Document</button>
          <button className="btn btn-secondary" onClick={() => onNavigate('quiz')}>🧪 Take Quiz</button>
          <button className="btn btn-secondary" onClick={() => onNavigate('mastery')}>📈 View Progress</button>
        </div>
      </div>

      {/* Weak Concepts */}
      {progress?.weak_concepts?.length > 0 && (
        <div className="card" style={{ marginTop: '1.25rem', borderColor: 'rgba(245,158,11,0.3)' }}>
          <h3 style={{ fontWeight: 600, marginBottom: '0.75rem', color: 'var(--accent-warn)' }}>
            ⚠️ Concepts Needing Attention
          </h3>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {progress.weak_concepts.map((c: string, i: number) => (
              <span key={i} className="badge badge-warn">{c}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
