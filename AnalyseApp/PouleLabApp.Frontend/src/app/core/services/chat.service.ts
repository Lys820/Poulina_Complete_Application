import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface SouchePrediction {
  souche:        string;
  confiance_pct: number;
}

export interface ChatResponse {
  session_id:          string;
  answer:              string;
  souche_prediction?:  SouchePrediction;
  retrieved_analyses?: any[];
}

export interface ChatRequest {
  question:      string;
  session_id?:   string;
  filtre_ville?: string;
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly chatUrl = 'http://localhost:8000';
  constructor(private http: HttpClient) {}
  sendMessage(req: ChatRequest): Observable<ChatResponse> {
    return this.http.post<ChatResponse>(`${this.chatUrl}/chat`, req);
  }
}
