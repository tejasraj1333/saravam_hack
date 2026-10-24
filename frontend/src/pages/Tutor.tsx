import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

interface Doc { document_id: string; filename: string; title: string; status: string; }
interface Msg { role: string; content: string; speech_content?: string; citations: any[]; audio_url?: string; message_id: string; }

export default function Tutor() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [convId, setConvId] = useState<string | null>(null);
  const [language, setLanguage] = useState('hi-IN');
  // Voice
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [ttsLoading, setTtsLoading] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listDocuments().then(r => {
      const ready = (r.documents || []).filter((d: any) => d.status === 'ready');
      setDocs(ready);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const toggleDoc = (id: string) => {
    setSelectedDocs(prev => prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]);
  };

  const sendMessage = useCallback(async (question: string) => {
    if (!question.trim() || loading) return;
    setInput('');
    const userMsg: Msg = { role: 'user', content: question, citations: [], message_id: '' };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    try {
      const res = await api.askTutor({
        question,
        document_ids: selectedDocs,
        conversation_id: convId,
        language,
      });
      if (!convId) setConvId(res.conversation_id);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: res.answer,
        speech_content: res.speech_answer,
        citations: res.citations || [],
        message_id: res.message_id,
      }]);
    } catch (e: any) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ Error: ${e.message}`,
        citations: [],
        message_id: '',
      }]);
    } finally { setLoading(false); }
  }, [loading, selectedDocs, convId, language]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  // Voice recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      chunksRef.current = [];
      mr.ondataavailable = e => chunksRef.current.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        setTranscribing(true);
        try {
          const res = await api.transcribeAudio(blob, 'audio.webm');
          setInput(res.transcript || '');
        } catch (e: any) {
          alert('Transcription failed: ' + e.message);
        } finally { setTranscribing(false); }
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setRecording(true);
    } catch {
      alert('Microphone access denied.');
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    setRecording(false);
  };

  const playTTS = async (msg: Msg) => {
    if (!msg.speech_content) return;
    setTtsLoading(msg.message_id);
    try {
      const res = await api.generateTTS(msg.speech_content.slice(0, 1000), language);
      const audio = new Audio(`http://localhost:8000${res.audio_url}`);
      audio.play();
    } catch (e: any) {
      alert('TTS failed: ' + e.message);
    } finally { setTtsLoading(null); }
  };

  return (
    <div className="fade-in" style={{ display: 'flex', height: 'calc(100vh - 4rem)', gap: '1.25rem' }}>
      {/* Sidebar: doc selector */}
      <div style={{
        width: '220px', flexShrink: 0,
        background: 'var(--bg-card)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)', padding: '1rem',
        display: 'flex', flexDirection: 'column', gap: '0.5rem', overflow: 'auto',
      }}>
        <div style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '0.5rem' }}>
          Select Documents
        </div>
        {docs.length === 0 ? (
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Upload documents in the Library to select them here.</div>
        ) : docs.map(d => (
          <label key={d.document_id} style={{
            display: 'flex', alignItems: 'flex-start', gap: '0.5rem',
            padding: '0.5rem', borderRadius: '8px', cursor: 'pointer',
            background: selectedDocs.includes(d.document_id) ? 'rgba(108,143,255,0.1)' : 'transparent',
            border: `1px solid ${selectedDocs.includes(d.document_id) ? 'rgba(108,143,255,0.3)' : 'transparent'}`,
            transition: 'all 0.15s',
          }}>
            <input type="checkbox" checked={selectedDocs.includes(d.document_id)}
              onChange={() => toggleDoc(d.document_id)}
              style={{ width: 'auto', marginTop: '2px', accentColor: 'var(--accent)' }} />
            <div style={{ fontSize: '0.8rem', lineHeight: 1.3 }}>
              <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{d.title || d.filename}</div>
            </div>
          </label>
        ))}

        <div style={{ marginTop: 'auto', borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.35rem' }}>Language</div>
          <select value={language} onChange={e => setLanguage(e.target.value)} style={{ fontSize: '0.8rem' }}>
            <option value="hi-IN">Hindi (Hinglish)</option>
            <option value="en-IN">English</option>
            <option value="ta-IN">Tamil</option>
            <option value="te-IN">Telugu</option>
            <option value="bn-IN">Bengali</option>
            <option value="mr-IN">Marathi</option>
          </select>
        </div>
      </div>

      {/* Chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Messages */}
        <div style={{
          flex: 1, overflowY: 'auto', padding: '0.5rem 0',
          display: 'flex', flexDirection: 'column', gap: '1.25rem',
        }}>
          {messages.length === 0 && (
            <div className="empty-state" style={{ margin: 'auto' }}>
              <div className="empty-state-icon">🤖</div>
              <h3>ShikshaSetu AI Tutor</h3>
              <p>Select documents, then ask a question in text or voice.<br />
                Answers are grounded in your uploaded material.</p>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center', marginTop: '1.5rem' }}>
                {['Explain this concept', 'Summarise the chapter', 'What is the formula for...', 'Give an example of...'].map(s => (
                  <button key={s} className="btn btn-secondary" style={{ fontSize: '0.78rem' }}
                    onClick={() => setInput(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div className={`message-bubble ${msg.role}`}>
                {msg.role === 'assistant' ? (
                  <div className="markdown-body">
                    <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  <div>{msg.content}</div>
                )}
              </div>

              {/* Citations */}
              {msg.citations?.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem', maxWidth: '85%' }}>
                  {msg.citations.map((c, ci) => (
                    <div key={ci} className="citation-card">
                      <div className="citation-source">📄 {c.document_name} — Page {c.page_number}</div>
                      <div className="citation-snippet">"{c.snippet}"</div>
                    </div>
                  ))}
                </div>
              )}

              {/* TTS button for assistant */}
              {msg.role === 'assistant' && msg.message_id && (
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.35rem' }}>
                  <button className="btn-icon" title="Listen to answer"
                    onClick={() => playTTS(msg)}
                    disabled={ttsLoading === msg.message_id}>
                    {ttsLoading === msg.message_id ? <div className="spinner" style={{ width: 14, height: 14 }} /> : '🔊'}
                  </button>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <div className="message-bubble assistant" style={{ display: 'flex', gap: '6px', padding: '0.85rem 1rem' }}>
                {[0, 1, 2].map(i => (
                  <div key={i} className="pulse" style={{
                    width: 8, height: 8, borderRadius: '50%',
                    background: 'var(--accent)',
                    animationDelay: `${i * 0.15}s`,
                  }} />
                ))}
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input row */}
        <div style={{
          borderTop: '1px solid var(--border)', paddingTop: '1rem',
          display: 'flex', gap: '0.75rem', alignItems: 'flex-end',
        }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <textarea
              placeholder={selectedDocs.length === 0 ? 'Select a document above, then ask a question…' : 'Ask a question about your documents…'}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKey}
              rows={2}
              style={{ resize: 'none', paddingRight: '2.5rem' }}
              disabled={loading}
            />
            {transcribing && (
              <div style={{ position: 'absolute', right: '0.75rem', bottom: '0.75rem' }}>
                <div className="spinner" style={{ width: 16, height: 16 }} />
              </div>
            )}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
            <button
              className="btn-icon"
              title={recording ? 'Stop recording' : 'Record voice question'}
              onClick={recording ? stopRecording : startRecording}
              style={{ padding: '0.65rem', borderColor: recording ? 'var(--accent-danger)' : undefined }}
            >
              {recording ? <div className="recording-indicator" /> : '🎙️'}
            </button>
            <button
              className="btn btn-primary"
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || loading}
              style={{ height: '44px', padding: '0 1.25rem' }}
            >
              {loading ? <div className="spinner" style={{ width: 16, height: 16, borderTopColor: '#fff' }} /> : '→'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
