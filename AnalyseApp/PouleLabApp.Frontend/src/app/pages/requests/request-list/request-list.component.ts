import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { RequestService } from '../../../core/services/request.service';
import { AuthService } from '../../../core/services/auth.service';
import { RequestListDto } from '../../../core/models/request.model';

@Component({
  selector: 'app-request-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './request-list.component.html',
  styleUrls: ['./request-list.component.scss'],
})
export class RequestListComponent implements OnInit {
  requests = signal<RequestListDto[]>([]);
  isLoading = signal(true);
  statusFilter = signal('');

  readonly statuses = [
    { value: '', label: 'Tous les statuts' },
    { value: 'Draft', label: 'Brouillon' },
    { value: 'Submitted', label: 'Soumise' },
    { value: 'Received', label: 'Réceptionnée' },
    { value: 'Assigned', label: 'Assignée' },
    { value: 'InProgress', label: 'En cours' },
    { value: 'InReview', label: 'En révision' },
    { value: 'Validated', label: 'Validée' },
    { value: 'Rejected', label: 'Rejetée' },
    { value: 'Closed', label: 'Clôturée' },
  ];

  constructor(
    private requestService: RequestService,
    public authService: AuthService,
  ) {}

  ngOnInit(): void {
    this.loadRequests();
  }

  loadRequests(): void {
    this.isLoading.set(true);
    this.requestService.getAll(this.statusFilter() || undefined).subscribe({
      next: (data) => {
        this.requests.set(data);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  onFilterChange(): void {
    this.loadRequests();
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
}
