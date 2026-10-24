const API_BASE = 'http://localhost:8000';

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// ── Health ────────────────────────────────────────────────────
export const api = {
  health: () => request<any>('/api/health'),

  // ── Documents ───────────────────────────────────────────────
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return fetch(`${API_BASE}/api/documents/upload`, {
      method: 'POST',
      body: form,
    }).then(async r => {
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }));
        throw new Error(err.detail || `HTTP ${r.status}`);
      }
      return r.json();
    });
  },

  listDocuments: () => request<any>('/api/documents'),

  deleteDocument: (id: string) =>
    request<any>(`/api/documents/${id}`, { method: 'DELETE' }),

  getDocument: (id: string) => request<any>(`/api/documents/${id}`),

  // ── Tutor ────────────────────────────────────────────────────
  askTutor: (body: any) =>
    request<any>('/api/tutor/ask', { method: 'POST', body: JSON.stringify(body) }),

  getHistory: (convId: string) =>
    request<any>(`/api/tutor/history/${convId}`),

  submitFeedback: (body: any) =>
    request<any>('/api/tutor/feedback', { method: 'POST', body: JSON.stringify(body) }),

  // ── Voice ────────────────────────────────────────────────────
  transcribeAudio: (file: Blob, filename = 'audio.wav') => {
    const form = new FormData();
    form.append('file', file, filename);
    return fetch(`${API_BASE}/api/voice/transcribe`, {
      method: 'POST',
      body: form,
    }).then(async r => {
      if (!r.ok) {
        const err = await r.json().catch(() => ({ detail: r.statusText }));
        throw new Error(err.detail || `HTTP ${r.status}`);
      }
      return r.json();
    });
  },

  generateTTS: (text: string, language = 'hi-IN') =>
    request<any>('/api/voice/tts', {
      method: 'POST',
      body: JSON.stringify({ text, language }),
    }),

  audioUrl: (filename: string) => `${API_BASE}/api/audio/${filename}`,

  // ── Quiz ─────────────────────────────────────────────────────
  generateQuiz: (body: any) =>
    request<any>('/api/quiz/generate', { method: 'POST', body: JSON.stringify(body) }),

  submitQuiz: (body: any) =>
    request<any>('/api/quiz/submit', { method: 'POST', body: JSON.stringify(body) }),

  // ── Learning ─────────────────────────────────────────────────
  getProgress: () => request<any>('/api/learning/progress'),
  getRevisionPlan: () => request<any>('/api/learning/revision-plan'),
};
