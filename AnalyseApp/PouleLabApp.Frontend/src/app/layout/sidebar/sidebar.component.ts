import { Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { DomSanitizer } from '@angular/platform-browser';
import { SafeHtmlPipe } from '../../shared/pipes/safe-html.pipe';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  roles: string[]; // Rôles autorisés à voir ce lien
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, SafeHtmlPipe],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss'],
})
export class SidebarComponent {
  isCollapsed = signal(false);

  // Navigation — filtrée selon le rôle de l'utilisateur connecté
  navItems: NavItem[] = [
    {
      label: 'Tableau de bord',
      icon: 'grid',
      route: '/app/dashboard',
      roles: ['Administrator', 'Manager', 'Receptionist', 'Analyst', 'LabChief', 'Client'],
    },
    {
      label: 'Mes demandes',
      icon: 'file-text',
      route: '/app/requests',
      roles: ['Client'],
    },
    {
      label: 'Toutes les demandes',
      icon: 'list',
      route: '/app/requests',
      roles: ['Administrator', 'Manager', 'Receptionist', 'Analyst', 'LabChief'],
    },
    {
      label: 'Nouvelle demande',
      icon: 'plus-circle',
      route: '/app/requests/new',
      roles: ['Administrator', 'Manager', 'Client'],
    },
    {
      label: 'Utilisateurs',
      icon: 'users',
      route: '/app/users',
      roles: ['Administrator', 'Manager'],
    },
    {
      label: 'Notifications',
      icon: 'bell',
      route: '/app/notifications',
      roles: ['Administrator', 'Manager', 'Receptionist', 'Analyst', 'LabChief', 'Client'],
    },
  ];

  constructor(
    public authService: AuthService,
    private sanitizer: DomSanitizer,
  ) {}

  // Filtrer les liens selon le rôle connecté
  get filteredNavItems(): NavItem[] {
    const role = this.authService.getRole();
    return this.navItems.filter((item) => item.roles.includes(role));
  }

  toggleSidebar(): void {
    this.isCollapsed.update((v) => !v);
  }

  logout(): void {
    this.authService.logout();
  }

  // Retourne les initiales de l'utilisateur pour l'avatar
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

  // Icônes SVG inline — pas besoin de librairie externe
  getIcon(name: string): string {
    const icons: Record<string, string> = {
      grid: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>`,
      'file-text': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`,
      list: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>`,
      'plus-circle': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="16"/><line x1="8" y1="12" x2="16" y2="12"/></svg>`,
      users: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>`,
      bell: `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>`,
      'log-out': `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>`,
    };
    return icons[name] ?? '';
  }
}
