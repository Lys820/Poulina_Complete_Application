import { Component, ElementRef, OnInit, ViewChild, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatService, ChatResponse } from '../../../core/services/chat.service';

interface Message {
  role: 'user' | 'assistant';
  content: string | null;
  ts: Date;
  meta?: Partial<ChatResponse>;
}

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chat.component.html',
  styleUrls: ['./chat.component.scss'],
})
export class ChatComponent implements OnInit {
  @ViewChild('messagesContainer') messagesContainer!: ElementRef;

  messages: Message[] = [];
  input = '';
  loading = false;
  ville = '';
  sessionId: string | undefined = undefined;

  readonly suggestions = [
    'Quelle souche recommandes-tu pour mon centre ?',
    'Quel laboratoire est disponible rapidement ?',
    'Y a-t-il des alertes sanitaires actives ?',
  ];

  get showSuggestions() { return this.messages.length === 0; }
  get sessionShort()    { return this.sessionId ? this.sessionId.slice(0, 8) + '…' : '—'; }

  constructor(private chatService: ChatService) {}

  ngOnInit(): void {
    this.messages.push({
      role: 'assistant',
      content: 'Bonjour ! Je suis l\'assistant IA Poulina. Comment puis-je vous aider ?',
      ts: new Date(),
    });
  }

  send(text?: string): void {
    const question = (text ?? this.input).trim();
    if (!question || this.loading) return;

    this.messages.push({ role: 'user', content: question, ts: new Date() });
    this.messages.push({ role: 'assistant', content: null, ts: new Date() }); // typing
    this.input = '';
    this.loading = true;
    this.scrollBottom();

    this.chatService.sendMessage({
      question,
      session_id: this.sessionId,
      filtre_ville: this.ville || undefined,
    }).subscribe({
      next: (res) => {
        this.sessionId = res.session_id;
        this.messages[this.messages.length - 1] = {
          role: 'assistant',
          content: res.answer,
          ts: new Date(),
          meta: res,
        };
        this.loading = false;
        this.scrollBottom();
      },
      error: () => {
        this.messages[this.messages.length - 1].content = 'Erreur de connexion au service IA.';
        this.loading = false;
      },
    });
  }

  reset(): void {
    this.messages = [];
    this.sessionId = undefined;
  }

  onKeyDown(e: KeyboardEvent): void {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); }
  }

  autoResize(e: Event): void {
    const el = e.target as HTMLTextAreaElement;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }

  hasMeta(msg: Message): boolean {
    return !!(msg.meta?.souche_prediction || msg.meta?.retrieved_analyses?.length);
  }

  formatTime(d: Date): string {
    return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
  }

  private scrollBottom(): void {
    setTimeout(() => {
      if (this.messagesContainer)
        this.messagesContainer.nativeElement.scrollTop =
          this.messagesContainer.nativeElement.scrollHeight;
    }, 50);
  }
}