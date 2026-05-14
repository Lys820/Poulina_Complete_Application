import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../core/services/auth.service';
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss'],
})
export class HeaderComponent implements OnInit {
  unreadCount = signal(0);
  showDropdown = signal(false);

  constructor(
    public authService: AuthService,
    private http: HttpClient,
  ) {}

  ngOnInit(): void {
    this.loadUnreadCount();
    // Vérifier les notifications toutes les 30 secondes
    setInterval(() => this.loadUnreadCount(), 30000);
  }

  loadUnreadCount(): void {
    this.http.get<{ count: number }>(`${environment.apiUrl}/notifications/unread`).subscribe({
      next: (res) => this.unreadCount.set(res.count),
      error: () => this.unreadCount.set(0),
    });
  }

  get userInitials(): string {
    const user = this.authService.currentUser();
    if (!user) return '?';
    return `${user.firstName[0]}${user.lastName[0]}`.toUpperCase();
  }

  get userName(): string {
    const user = this.authService.currentUser();
    return user ? `${user.firstName} ${user.lastName}` : '';
  }

  get userRole(): string {
    return this.authService.getRole();
  }

  toggleDropdown(): void {
    this.showDropdown.update((v) => !v);
  }

  logout(): void {
    this.authService.logout();
  }
}
