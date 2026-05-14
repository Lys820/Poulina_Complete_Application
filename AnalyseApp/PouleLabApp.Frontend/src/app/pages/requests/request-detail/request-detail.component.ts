import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { RequestService } from '../../../core/services/request.service';
import { AuthService } from '../../../core/services/auth.service';
import { RequestDetailDto, AuditLogDto } from '../../../core/models/request.model';

@Component({
  selector: 'app-request-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  templateUrl: './request-detail.component.html',
  styleUrls: ['./request-detail.component.scss'],
})
export class RequestDetailComponent implements OnInit {
  request = signal<RequestDetailDto | null>(null);
  history = signal<AuditLogDto[]>([]);
  isLoading = signal(true);

  // Actions modales
  showRejectModal = signal(false);
  showInvalidateModal = signal(false);
  showAssignModal = signal(false);
  rejectReason = signal('');
  invalidateReason = signal('');
  assignAnalystId = signal('');
  actionLoading = signal(false);
  successMessage = signal('');
  errorMessage = signal('');

  requestId!: number;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private requestService: RequestService,
    public authService: AuthService,
  ) {}

  ngOnInit(): void {
    this.requestId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadRequest();
  }

  loadRequest(): void {
    this.isLoading.set(true);
    this.requestService.getById(this.requestId).subscribe({
      next: (data) => {
        this.request.set(data);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });

    // Charger l'historique pour tous les rôles
    this.requestService.getHistory(this.requestId).subscribe({
      next: (data) => this.history.set(data),
    });
  }

  // -------------------------------------------------------
  // Actions Réceptionniste
  // -------------------------------------------------------
  receive(): void {
    this.actionLoading.set(true);
    this.requestService.receive(this.requestId).subscribe({
      next: (data) => {
        this.request.set(data);
        this.showSuccess('Demande réceptionnée avec succès.');
        this.actionLoading.set(false);
      },
      error: (err) => {
        this.showError(err.error?.message);
        this.actionLoading.set(false);
      },
    });
  }

  assign(): void {
    if (!this.assignAnalystId()) return;
    this.actionLoading.set(true);
    this.requestService.assign(this.requestId, this.assignAnalystId()).subscribe({
      next: (data) => {
        this.request.set(data);
        this.showAssignModal.set(false);
        this.showSuccess('Demande assignée avec succès.');
        this.actionLoading.set(false);
      },
      error: (err) => {
        this.showError(err.error?.message);
        this.actionLoading.set(false);
      },
    });
  }

  // -------------------------------------------------------
  // Actions Laborantin
  // -------------------------------------------------------
  analystAccept(): void {
    this.actionLoading.set(true);
    this.requestService.analystAccept(this.requestId).subscribe({
      next: (data) => {
        this.request.set(data);
        this.showSuccess('Demande acceptée. Vous pouvez maintenant saisir les résultats.');
        this.actionLoading.set(false);
      },
      error: (err) => {
        this.showError(err.error?.message);
        this.actionLoading.set(false);
      },
    });
  }

  analystReject(): void {
    if (!this.rejectReason()) return;
    this.actionLoading.set(true);
    this.requestService.analystReject(this.requestId, this.rejectReason()).subscribe({
      next: (data) => {
        this.request.set(data);
        this.showRejectModal.set(false);
        this.showSuccess('Demande refusée.');
        this.actionLoading.set(false);
      },
      error: (err) => {
        this.showError(err.error?.message);
        this.actionLoading.set(false);
      },
    });
  }

  completeAnalysis(): void {
    this.actionLoading.set(true);
    this.requestService.completeAnalysis(this.requestId).subscribe({
      next: (data) => {
        this.request.set(data);
        this.showSuccess('Analyses terminées. En attente de validation.');
        this.actionLoading.set(false);
      },
      error: (err) => {
        this.showError(err.error?.message);
        this.actionLoading.set(false);
      },
    });
  }

  // -------------------------------------------------------
  // Actions Chef de labo
  // -------------------------------------------------------
  validate(): void {
    this.actionLoading.set(true);
    this.requestService.validate(this.requestId).subscribe({
      next: (data) => {
        this.request.set(data);
        this.showSuccess('Résultats validés avec succès.');
        this.actionLoading.set(false);
      },
      error: (err) => {
        this.showError(err.error?.message);
        this.actionLoading.set(false);
      },
    });
  }

  invalidate(): void {
    if (!this.invalidateReason()) return;
    this.actionLoading.set(true);
    this.requestService.invalidate(this.requestId, this.invalidateReason()).subscribe({
      next: (data) => {
        this.request.set(data);
        this.showInvalidateModal.set(false);
        this.showSuccess('Résultats rejetés. Renvoyé au laborantin.');
        this.actionLoading.set(false);
      },
      error: (err) => {
        this.showError(err.error?.message);
        this.actionLoading.set(false);
      },
    });
  }

  // -------------------------------------------------------
  // Téléchargement PDF
  // -------------------------------------------------------
  downloadPdf(): void {
    this.requestService.downloadPdf(this.requestId).subscribe({
      next: (blob) => this.triggerDownload(blob, `demande-${this.requestId}.pdf`),
      error: () => this.showError('Erreur lors du téléchargement.'),
    });
  }

  downloadBulletin(): void {
    this.requestService.downloadBulletin(this.requestId).subscribe({
      next: (blob) => this.triggerDownload(blob, `bulletin-${this.requestId}.pdf`),
      error: () => this.showError('Bulletin non disponible.'),
    });
  }

  private triggerDownload(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  // -------------------------------------------------------
  // Helpers
  // -------------------------------------------------------
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

  isCurrentAnalyst(): boolean {
    const userId = this.authService.currentUser()?.userId;
    return this.request()?.assignedToId === userId;
  }

  private showSuccess(msg: string): void {
    this.successMessage.set(msg);
    setTimeout(() => this.successMessage.set(''), 4000);
  }

  private showError(msg: string): void {
    this.errorMessage.set(msg ?? 'Une erreur est survenue.');
    setTimeout(() => this.errorMessage.set(''), 4000);
  }

  // Naviguer vers la page de modification
  editRequest(): void {
    this.router.navigate(['/app/requests', this.requestId, 'edit']);
  }

  // Soumettre un brouillon
  submitDraft(): void {
    this.actionLoading.set(true);
    this.requestService.submit(this.requestId).subscribe({
      next: (data) => {
        this.request.set(data);
        this.showSuccess('Demande soumise avec succès.');
        this.actionLoading.set(false);
      },
      error: (err) => {
        this.showError(err.error?.message);
        this.actionLoading.set(false);
      },
    });
  }

  // Supprimer un brouillon
  deleteRequest(): void {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette demande ?')) return;

    this.requestService.delete(this.requestId).subscribe({
      next: () => this.router.navigate(['/app/requests']),
      error: (err) => this.showError(err.error?.message),
    });
  }
}
