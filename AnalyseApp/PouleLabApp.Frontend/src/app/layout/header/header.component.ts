import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { NotificationBadgeService } from '../../core/services/notification-badge.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss'],
})
export class HeaderComponent implements OnInit {
  showDropdown = false;

  constructor(
    public authService: AuthService,
    public badgeService: NotificationBadgeService,
  ) {}

  ngOnInit(): void {
    this.badgeService.refresh();
    setInterval(() => this.badgeService.refresh(), 30000);
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
    this.showDropdown = !this.showDropdown;
  }

  logout(): void {
    this.authService.logout();
  }
}
