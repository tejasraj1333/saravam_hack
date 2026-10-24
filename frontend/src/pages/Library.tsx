import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../services/api';

interface Doc { document_id: string; filename: string; title: string; page_count: number; status: string; chunk_count: number; is_scanned: boolean; error_message?: string; }

export default function Library() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<{ type: string; text: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  const load = useCallback(() =>
    api.listDocuments().then(r => setDocs(r.documents || [])).finally(() => setLoading(false)), []);

  useEffect(() => { load(); }, [load]);

  const upload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadMsg({ type: 'error', text: 'Only PDF files are supported.' }); return;
    }
    setUploading(true);
    setUploadMsg(null);
    try {
      const res = await api.uploadDocument(file);
      setUploadMsg({ type: res.status === 'ready' ? 'success' : 'warn', text: res.message });
      load();
    } catch (e: any) {
      setUploadMsg({ type: 'error', text: e.message });
    } finally { setUploading(false); }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) upload(file);
  };

  const deleteDoc = async (id: string) => {
    if (!confirm('Delete this document and all its chunks?')) return;
    try { await api.deleteDocument(id); load(); }
    catch (e: any) { alert(e.message); }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h2>📚 Document Library</h2>
        <p>Upload and manage your study PDFs. Text is extracted locally — no API credits used.</p>
      </div>

      {/* Upload Zone */}
      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        style={{ marginBottom: '2rem' }}
        onDrop={handleDrop}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onClick={() => inputRef.current?.click()}
      >
        <div className="upload-zone-icon">{uploading ? '⏳' : '📄'}</div>
        <div style={{ fontWeight: 600, marginBottom: '0.35rem' }}>
          {uploading ? 'Processing your document…' : 'Drop PDF here or click to browse'}
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Maximum 20 MB · 200 pages · PDF only
        </div>
        {uploading && <div className="spinner" style={{ margin: '1rem auto 0' }} />}
        <input ref={inputRef} type="file" accept=".pdf" style={{ display: 'none' }}
          onChange={e => e.target.files?.[0] && upload(e.target.files[0])} />
      </div>

      {uploadMsg && (
        <div className={`alert alert-${uploadMsg.type === 'success' ? 'success' : uploadMsg.type === 'warn' ? 'warn' : 'error'}`}
          style={{ marginBottom: '1.5rem' }}>
          {uploadMsg.type === 'success' ? '✅' : uploadMsg.type === 'warn' ? '⚠️' : '❌'} {uploadMsg.text}
        </div>
      )}

      {/* Document List */}
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: '3rem' }}><div className="spinner" /></div>
      ) : docs.length === 0 ? (
        <div className="empty-state card">
          <div className="empty-state-icon">📭</div>
          <h3>No documents uploaded yet</h3>
          <p>Upload a PDF to start learning with AI assistance</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {docs.map(doc => (
            <div key={doc.document_id} className="card" style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
              <div style={{ fontSize: '2rem', flexShrink: 0 }}>
                {doc.status === 'ready' ? '📗' : doc.status === 'error' ? '❌' : '⏳'}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{doc.title || doc.filename}</span>
                  <span className={`badge badge-${doc.status === 'ready' ? 'success' : doc.status === 'error' ? 'error' : 'warn'}`}>
                    {doc.status}
                  </span>
                  {doc.is_scanned && <span className="badge badge-warn">Scanned</span>}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.4rem' }}>
                  {doc.filename} · {doc.page_count} pages · {doc.chunk_count} text chunks
                </div>
                {doc.error_message && (
                  <div style={{ fontSize: '0.8rem', color: 'var(--accent-danger)', marginTop: '0.25rem' }}>
                    {doc.error_message}
                  </div>
                )}
                {doc.is_scanned && (
                  <div style={{ fontSize: '0.75rem', color: 'var(--accent-warn)', marginTop: '0.25rem' }}>
                    ⚠️ Scanned document detected — text extraction may be incomplete. For best results, use digital PDFs.
                  </div>
                )}
              </div>
              <button className="btn btn-danger" style={{ flexShrink: 0, fontSize: '0.8rem' }}
                onClick={() => deleteDoc(doc.document_id)}>🗑 Delete</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
