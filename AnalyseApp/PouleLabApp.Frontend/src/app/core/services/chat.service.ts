import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ChatRequest {
  question: string;
  session_id?: string;
  filtre_ville?: string;
  force_collection?: string;
  predict_souche?: Record<string, unknown>;
}

export interface ChatResponse {
  question: string;
  answer: string;
  session_id: string;
  retrieved_analyses: { score: number; text: string }[];
  retrieved_labos: { score: number; nom: string }[];
  souche_prediction?: { souche: string; confiance_pct: number };
  model_used: string;
  execution_time_ms: number;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly apiUrl = `${environment.chatbotApiUrl}/api/v1/chat`;

  constructor(private http: HttpClient) {}

  sendMessage(payload: ChatRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(this.apiUrl, payload);
  }
}