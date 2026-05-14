import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { RequestService } from '../../core/services/request.service';
import { RequestListDto } from '../../core/models/request.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit {
  requests = signal<RequestListDto[]>([]);
  isLoading = signal(true);

  constructor(
    public authService: AuthService,
    private requestService: RequestService,
  ) {}

  ngOnInit(): void {
    this.requestService.getAll().subscribe({
      next: (data) => {
        this.requests.set(data);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  // Compteurs par statut
  get totalRequests() {
    return this.requests().length;
  }
  get pendingRequests() {
    return this.requests().filter((r) => r.status === 'Submitted' || r.status === 'Received')
      .length;
  }
  get inProgressRequests() {
    return this.requests().filter((r) => r.status === 'InProgress' || r.status === 'Assigned')
      .length;
  }
  get validatedRequests() {
    return this.requests().filter((r) => r.status === 'Validated').length;
  }

  // 5 dernières demandes
  get recentRequests() {
    return this.requests().slice(0, 5);
  }

  // Badge couleur selon statut
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

  get greeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) return 'Bonjour';
    if (hour < 18) return 'Bon après-midi';
    return 'Bonsoir';
  }
}
