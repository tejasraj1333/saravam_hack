import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface Doc { document_id: string; filename: string; title: string; status: string; }
interface Question { question_id: string; question_text: string; question_type: string; options: string[]; difficulty: number; }

export default function Quiz() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [topic, setTopic] = useState('');
  const [numQ, setNumQ] = useState(5);
  const [diff, setDiff] = useState(2);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.listDocuments().then(r => {
      const ready = (r.documents || []).filter((d: any) => d.status === 'ready');
      setDocs(ready);
    });
  }, []);

  const generate = async () => {
    setLoading(true); setResult(null); setAnswers({});
    try {
      const res = await api.generateQuiz({ document_ids: selectedDocs, topic, num_questions: numQ, difficulty: diff });
      setSessionId(res.session_id);
      setQuestions(res.questions || []);
    } catch (e: any) { alert('Quiz generation failed: ' + e.message); }
    finally { setLoading(false); }
  };

  const submit = async () => {
    if (!sessionId) return;
    const answerList = questions.map(q => ({ question_id: q.question_id, student_answer: answers[q.question_id] || '' }));
    setSubmitting(true);
    try {
      const res = await api.submitQuiz({ session_id: sessionId, answers: answerList });
      setResult(res);
    } catch (e: any) { alert('Submit failed: ' + e.message); }
    finally { setSubmitting(false); }
  };

  const reset = () => { setSessionId(null); setQuestions([]); setAnswers({}); setResult(null); };

  const diffLabel = ['', 'Easy', 'Medium-Easy', 'Medium', 'Hard', 'Expert'][diff] || 'Medium';

  if (result) {
    const pct = result.score.toFixed(1);
    const color = result.score >= 80 ? 'var(--accent-3)' : result.score >= 60 ? 'var(--accent-warn)' : 'var(--accent-danger)';
    return (
      <div className="fade-in">
        <div className="page-header">
          <h2>🧪 Quiz Results</h2>
        </div>
        <div className="card" style={{ textAlign: 'center', marginBottom: '1.5rem', borderColor: color }}>
          <div style={{ fontSize: '4rem', fontWeight: 800, color, marginBottom: '0.25rem' }}>{pct}%</div>
          <div style={{ color: 'var(--text-secondary)' }}>{result.correct} / {result.total} correct</div>
          {result.recommendations.map((r: string, i: number) => (
            <div key={i} className="alert alert-info" style={{ marginTop: '0.75rem', textAlign: 'left' }}>💡 {r}</div>
          ))}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '1.5rem' }}>
          {result.results.map((r: any, i: number) => (
            <div key={i} className="card" style={{ borderColor: r.is_correct ? 'rgba(52,211,153,0.3)' : 'rgba(248,113,113,0.3)' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                <span style={{ fontSize: '1.25rem' }}>{r.is_correct ? '✅' : '❌'}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, marginBottom: '0.4rem' }}>{r.question_text}</div>
                  <div style={{ fontSize: '0.82rem', display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.4rem' }}>
                    <span><span style={{ color: 'var(--text-muted)' }}>Your answer: </span>
                      <span style={{ color: r.is_correct ? 'var(--accent-3)' : 'var(--accent-danger)', fontWeight: 500 }}>
                        {r.student_answer || '(no answer)'}
                      </span>
                    </span>
                    {!r.is_correct && <span><span style={{ color: 'var(--text-muted)' }}>Correct: </span>
                      <span style={{ color: 'var(--accent-3)', fontWeight: 500 }}>{r.correct_answer}</span></span>}
                  </div>
                  {r.explanation && <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', background: 'var(--bg-secondary)', padding: '0.5rem 0.75rem', borderRadius: '6px' }}>
                    💡 {r.explanation}
                  </div>}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-primary" onClick={reset}>🔄 New Quiz</button>
          <button className="btn btn-secondary" onClick={generate}>Retry Same Topic</button>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>🧪 Adaptive Quiz</h2>
        <p>Generate quiz questions from your study material and test your understanding.</p>
      </div>

      {questions.length === 0 ? (
        <div className="card" style={{ maxWidth: '560px' }}>
          <h3 style={{ fontWeight: 600, marginBottom: '1.25rem' }}>Generate Quiz</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                Select Documents
              </label>
              {docs.length === 0 ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Upload documents in the Library first.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {docs.map(d => (
                    <label key={d.document_id} style={{ display: 'flex', gap: '0.5rem', cursor: 'pointer', fontSize: '0.85rem' }}>
                      <input type="checkbox" checked={selectedDocs.includes(d.document_id)}
                        onChange={() => setSelectedDocs(p => p.includes(d.document_id) ? p.filter(x => x !== d.document_id) : [...p, d.document_id])}
                        style={{ accentColor: 'var(--accent)', width: 'auto' }} />
                      {d.title || d.filename}
                    </label>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                Topic Focus (optional)
              </label>
              <input type="text" placeholder="e.g. Quantum Mechanics, Band Theory…"
                value={topic} onChange={e => setTopic(e.target.value)} />
            </div>
            <div className="grid-2">
              <div>
                <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                  Questions: {numQ}
                </label>
                <input type="range" min={2} max={15} value={numQ} onChange={e => setNumQ(+e.target.value)}
                  style={{ background: 'none', border: 'none', padding: 0, accentColor: 'var(--accent)' }} />
              </div>
              <div>
                <label style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.35rem' }}>
                  Difficulty: {diffLabel}
                </label>
                <input type="range" min={1} max={5} value={diff} onChange={e => setDiff(+e.target.value)}
                  style={{ background: 'none', border: 'none', padding: 0, accentColor: 'var(--accent)' }} />
              </div>
            </div>
            <button className="btn btn-primary" onClick={generate} disabled={loading || selectedDocs.length === 0}
              style={{ marginTop: '0.5rem' }}>
              {loading ? <><div className="spinner" style={{ width: 16, height: 16, borderTopColor: '#fff' }} /> Generating…</> : '✨ Generate Quiz'}
            </button>
          </div>
        </div>
      ) : (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
            <div style={{ fontWeight: 600 }}>{questions.length} Questions</div>
            <button className="btn btn-secondary" onClick={reset}>← Back</button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '1.5rem' }}>
            {questions.map((q, i) => (
              <div key={q.question_id} className="card">
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', marginBottom: '0.85rem' }}>
                  <span style={{
                    width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                    background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: '0.8rem', fontWeight: 700, color: '#fff',
                  }}>{i + 1}</span>
                  <div style={{ fontWeight: 500, lineHeight: 1.5 }}>{q.question_text}</div>
                </div>
                {q.question_type === 'mcq' && q.options.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                    {q.options.map((opt, oi) => (
                      <label key={oi} style={{
                        display: 'flex', gap: '0.65rem', alignItems: 'center',
                        padding: '0.6rem 0.85rem', borderRadius: '8px', cursor: 'pointer',
                        border: `1px solid ${answers[q.question_id] === opt ? 'var(--accent)' : 'var(--border)'}`,
                        background: answers[q.question_id] === opt ? 'rgba(108,143,255,0.1)' : 'var(--bg-secondary)',
                        transition: 'all 0.15s',
                      }}>
                        <input type="radio" name={q.question_id} value={opt}
                          checked={answers[q.question_id] === opt}
                          onChange={() => setAnswers(p => ({ ...p, [q.question_id]: opt }))}
                          style={{ accentColor: 'var(--accent)', width: 'auto' }} />
                        <span style={{ fontSize: '0.875rem' }}>{opt}</span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <textarea placeholder="Type your answer…" rows={2}
                    value={answers[q.question_id] || ''}
                    onChange={e => setAnswers(p => ({ ...p, [q.question_id]: e.target.value }))} />
                )}
              </div>
            ))}
          </div>

          <button className="btn btn-primary" onClick={submit} disabled={submitting}
            style={{ fontSize: '1rem', padding: '0.75rem 2rem' }}>
            {submitting ? <><div className="spinner" style={{ width: 16, height: 16, borderTopColor: '#fff' }} /> Evaluating…</> : '✅ Submit Quiz'}
          </button>
        </div>
      )}
    </div>
  );
}
