import { Component, OnInit, signal } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import { RouterLink } from '@angular/router';
import { NotificationService } from '../../core/services/notification.service';
import { NotificationDto } from '../../core/models/notification.model';
import { NotificationBadgeService } from '../../core/services/notification-badge.service';

@Component({
  selector: 'app-notifications',
  standalone: true,
  imports: [CommonModule, NgClass, RouterLink],
  templateUrl: './notifications.component.html',
  styleUrls: ['./notifications.component.scss'],
})
export class NotificationsComponent implements OnInit {
  notifications = signal<NotificationDto[]>([]);
  isLoading = signal(true);
  successMsg = signal('');

  constructor(
    private notificationService: NotificationService,
    private badgeService: NotificationBadgeService,
  ) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.isLoading.set(true);
    this.notificationService.getAll().subscribe({
      next: (data) => {
        this.notifications.set(data);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  get unreadCount(): number {
    return this.notifications().filter((n) => !n.isRead).length;
  }

  markAsRead(notification: NotificationDto): void {
    if (notification.isRead) return;
    this.notificationService.markAsRead(notification.id).subscribe({
      next: () => {
        this.notifications.update((list) =>
          list.map((n) => (n.id === notification.id ? { ...n, isRead: true } : n)),
        );
        this.badgeService.refresh();
      },
    });
  }

  markAllAsRead(): void {
    this.notificationService.markAllAsRead().subscribe({
      next: () => {
        this.notifications.update((list) => list.map((n) => ({ ...n, isRead: true })));
        this.badgeService.refresh();
        this.showSuccess('Toutes les notifications marquées comme lues.');
      },
    });
  }

  delete(id: number): void {
    this.notificationService.delete(id).subscribe({
      next: () => {
        this.notifications.update((list) => list.filter((n) => n.id !== id));
      },
    });
  }

  deleteAll(): void {
    if (!confirm('Supprimer toutes les notifications ?')) return;
    this.notificationService.deleteAll().subscribe({
      next: () => {
        this.notifications.set([]);
        this.showSuccess('Toutes les notifications supprimées.');
      },
    });
  }

  getStatusLabel(status: string): string {
    const map: Record<string, string> = {
      Draft: 'Brouillon',
      Submitted: 'Soumise',
      Received: 'Réceptionnée',
      Assigned: 'Assignée',
      InProgress: 'En cours',
      InReview: 'En révision',
      Validated: 'Validée',
      Rejected: 'Rejetée',
      Closed: 'Clôturée',
    };
    return map[status] ?? status;
  }

  getStatusBadge(status: string): string {
    const map: Record<string, string> = {
      Draft: 'badge-draft',
      Submitted: 'badge-submitted',
      Received: 'badge-received',
      Assigned: 'badge-assigned',
      InProgress: 'badge-inprogress',
      InReview: 'badge-inreview',
      Validated: 'badge-validated',
      Rejected: 'badge-rejected',
      Closed: 'badge-closed',
    };
    return map[status] ?? 'badge-draft';
  }

  private showSuccess(msg: string): void {
    this.successMsg.set(msg);
    setTimeout(() => this.successMsg.set(''), 3000);
  }

  // Détecter si c'est une notification de retard
  isOverdueNotification(message: string): boolean {
    return message.toLowerCase().includes('retard');
  }
}
