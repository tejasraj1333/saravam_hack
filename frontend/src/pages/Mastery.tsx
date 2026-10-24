import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function Mastery() {
  const [progress, setProgress] = useState<any>(null);
  const [plan, setPlan] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'overview' | 'plan'>('overview');

  useEffect(() => {
    Promise.all([
      api.getProgress().then(setProgress),
      api.getRevisionPlan().then(setPlan),
    ]).finally(() => setLoading(false));
  }, []);

  const levelColor: Record<string, string> = {
    not_started: 'var(--text-muted)',
    beginner: 'var(--accent-danger)',
    developing: 'var(--accent-warn)',
    proficient: 'var(--accent)',
    mastered: 'var(--accent-3)',
  };

  const levelEmoji: Record<string, string> = {
    not_started: '⚪', beginner: '🔴', developing: '🟡', proficient: '🔵', mastered: '🟢',
  };

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: '4rem' }}><div className="spinner" /></div>
  );

  const concepts = progress?.concepts || [];
  const planItems = plan?.plan || [];
  const suggestions = progress?.revision_suggestions || [];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>📈 Concept Mastery</h2>
        <p>Track your understanding across concepts. Scores are estimates based on accuracy and practice.</p>
      </div>

      {/* Stats row */}
      <div className="grid-3" style={{ marginBottom: '1.5rem' }}>
        <div className="stat-card">
          <div className="stat-icon">🎯</div>
          <div className="stat-value">{Math.round((progress?.overall_mastery || 0) * 100)}%</div>
          <div className="stat-label">Overall Mastery</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">📝</div>
          <div className="stat-value">{progress?.total_questions_attempted || 0}</div>
          <div className="stat-label">Questions Attempted</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-value">
            {progress?.total_questions_attempted > 0
              ? `${Math.round((progress.total_correct / progress.total_questions_attempted) * 100)}%`
              : '—'}
          </div>
          <div className="stat-label">Accuracy</div>
        </div>
      </div>

      {/* Mastery formula explanation */}
      <div className="alert alert-info" style={{ marginBottom: '1.5rem', fontSize: '0.82rem' }}>
        ℹ️ <strong>Mastery Score Formula:</strong> accuracy × 0.6 + retention × 0.3 − hint_penalty × 0.1.
        This is a transparent estimate, not a scientifically validated measure of knowledge.
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
        {(['overview', 'plan'] as const).map(t => (
          <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setTab(t)}>
            {t === 'overview' ? '🧠 Concepts' : '📅 Revision Plan'}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <>
          {/* Revision suggestions */}
          {suggestions.length > 0 && (
            <div className="card" style={{ marginBottom: '1.25rem', borderColor: 'rgba(245,158,11,0.3)' }}>
              <h3 style={{ fontWeight: 600, marginBottom: '0.75rem', color: 'var(--accent-warn)' }}>
                🔁 Due for Review
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {suggestions.map((s: any, i: number) => (
                  <div key={i} style={{
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                    padding: '0.5rem 0.75rem', background: 'var(--bg-secondary)',
                    borderRadius: '8px', fontSize: '0.875rem',
                  }}>
                    <span>{s.concept_name}</span>
                    <span style={{ color: 'var(--accent-warn)', fontSize: '0.8rem' }}>{s.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {concepts.length === 0 ? (
            <div className="empty-state card">
              <div className="empty-state-icon">🧠</div>
              <h3>No mastery data yet</h3>
              <p>Take a quiz to start tracking your concept mastery</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {concepts.map((c: any) => (
                <div key={c.concept_id} className="card">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.65rem' }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{levelEmoji[c.level] || '⚪'} {c.concept_name}</div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                        {c.total_attempts} attempts · {c.correct_attempts} correct
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 700, color: levelColor[c.level] || 'var(--text-muted)' }}>
                        {Math.round(c.mastery_score * 100)}%
                      </div>
                      <div style={{ fontSize: '0.75rem', color: levelColor[c.level], textTransform: 'capitalize' }}>
                        {c.level.replace('_', ' ')}
                      </div>
                    </div>
                  </div>
                  <div className="mastery-bar">
                    <div className={`mastery-fill ${c.level}`} style={{ width: `${c.mastery_score * 100}%` }} />
                  </div>
                  {c.misconceptions?.length > 0 && (
                    <div style={{ marginTop: '0.5rem', fontSize: '0.78rem', color: 'var(--accent-danger)' }}>
                      Misconceptions: {c.misconceptions.join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'plan' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {planItems.length === 0 ? (
            <div className="empty-state card">
              <div className="empty-state-icon">📅</div>
              <h3>No revision plan yet</h3>
              <p>Take some quizzes to generate a personalized plan</p>
            </div>
          ) : planItems.map((item: any) => (
            <div key={item.concept_id} className="card" style={{
              borderLeft: `3px solid ${item.recommended_action === 'start' ? 'var(--accent-3)' :
                item.recommended_action === 'practice' ? 'var(--accent)' : 'var(--border)'}`,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                  <div style={{ fontWeight: 600 }}>{item.concept_name}</div>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {item.domain} {item.prerequisites?.length > 0 && `· Prerequisites: ${item.prerequisites.join(', ')}`}
                  </div>
                </div>
                <div style={{ textAlign: 'right', flexShrink: 0 }}>
                  <div className={`badge badge-${
                    item.recommended_action === 'start' ? 'success' :
                    item.recommended_action === 'practice' ? 'info' : 'warn'}`}>
                    {item.recommended_action}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    {Math.round(item.mastery_score * 100)}% mastery
                  </div>
                </div>
              </div>
              {!item.prerequisites_met && (
                <div style={{ marginTop: '0.5rem', fontSize: '0.78rem', color: 'var(--accent-warn)' }}>
                  ⚠️ Complete prerequisites first
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
