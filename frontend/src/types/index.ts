// ── Core domain types ──────────────────────────────────────────

export interface Document {
  document_id: string;
  filename: string;
  title: string;
  page_count: number;
  status: 'pending' | 'processing' | 'ready' | 'error';
  chunk_count: number;
  uploaded_at: string;
  error_message?: string;
  is_scanned: boolean;
}

export interface Citation {
  document_id: string;
  document_name: string;
  chunk_id: string;
  page_number: number;
  snippet: string;
}

export interface Message {
  message_id: string;
  conversation_id: string;
  role: 'user' | 'assistant';
  content: string;
  speech_content?: string;
  citations: Citation[];
  audio_url?: string;
  created_at: string;
}

export interface AskRequest {
  question: string;
  document_ids: string[];
  conversation_id?: string;
  language: string;
  learning_level?: string;
}

export interface AskResponse {
  answer: string;
  speech_answer: string;
  citations: Citation[];
  conversation_id: string;
  message_id: string;
  audio_url?: string;
}

export interface QuizQuestion {
  question_id: string;
  concept_id: string;
  question_text: string;
  question_type: 'mcq' | 'short_answer' | 'true_false';
  options: string[];
  difficulty: number;
}

export interface QuizResult {
  question_id: string;
  question_text: string;
  student_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation: string;
}

export interface QuizSubmitResponse {
  session_id: string;
  score: number;
  total: number;
  correct: number;
  results: QuizResult[];
  recommendations: string[];
}

export interface ConceptMastery {
  concept_id: string;
  concept_name: string;
  mastery_score: number;
  level: 'not_started' | 'beginner' | 'developing' | 'proficient' | 'mastered';
  total_attempts: number;
  correct_attempts: number;
  last_practiced?: string;
  misconceptions: string[];
}

export interface LearningProgress {
  concepts: ConceptMastery[];
  overall_mastery: number;
  total_questions_attempted: number;
  total_correct: number;
  weak_concepts: string[];
  revision_suggestions: Array<{
    concept_id: string;
    concept_name: string;
    mastery_score: number;
    reason: string;
  }>;
}

export interface HealthResponse {
  status: string;
  sarvam_configured: boolean;
  mongodb_connected: boolean;
  version: string;
}
