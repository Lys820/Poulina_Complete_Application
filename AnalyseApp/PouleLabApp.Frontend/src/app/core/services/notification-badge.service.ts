import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class NotificationBadgeService {
  // Signal partagé entre sidebar et header
  unreadCount = signal(0);

  constructor(private http: HttpClient) {}

  refresh(): void {
    this.http.get<{ count: number }>(`${environment.apiUrl}/notifications/unread`).subscribe({
      next: (res) => this.unreadCount.set(res.count),
      error: () => this.unreadCount.set(0),
    });
  }
}
