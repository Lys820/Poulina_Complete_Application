import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { NotificationDto, UnreadNotificationsResponse } from '../models/notification.model';

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private url = `${environment.apiUrl}/notifications`;

  constructor(private http: HttpClient) {}

  getAll(): Observable<NotificationDto[]> {
    return this.http.get<NotificationDto[]>(this.url);
  }

  getUnread(): Observable<UnreadNotificationsResponse> {
    return this.http.get<UnreadNotificationsResponse>(`${this.url}/unread`);
  }

  markAsRead(id: number): Observable<void> {
    return this.http.put<void>(`${this.url}/${id}/read`, {});
  }

  markAllAsRead(): Observable<void> {
    return this.http.put<void>(`${this.url}/read-all`, {});
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.url}/${id}`);
  }

  deleteAll(): Observable<void> {
    return this.http.delete<void>(this.url);
  }
}
