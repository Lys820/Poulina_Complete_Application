import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RequestService } from '../../../core/services/request.service';
import { AuthService } from '../../../core/services/auth.service';
import { RequestDetailDto, AuditLogDto } from '../../../core/models/request.model';
import { DeadlineDto } from '../../../core/models/request.model';
import { AnalystDto } from '../../../core/models/user.model';
import { UserService } from '../../../core/services/user.service';
import { NotificationService } from '../../../core/services/notification.service';
import { NotificationBadgeService } from '../../../core/services/notification-badge.service';

@Component({
  selector: 'app-request-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, ReactiveFormsModule],
  templateUrl: './request-detail.component.html',
  styleUrls: ['./request-detail.component.scss'],
})
export class RequestDetailComponent implements OnInit {
  request = signal<RequestDetailDto | null>(null);
  history = signal<AuditLogDto[]>([]);
  analysts = signal<AnalystDto[]>([]);
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
  deadlines = signal<DeadlineDto[]>([]);
  showDeadlineForm = signal(false);

  deadlineForm!: FormGroup;
  requestId!: number;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private fb: FormBuilder,
    private requestService: RequestService,
    private userService: UserService,
    private notificationService: NotificationService,
    private badgeService: NotificationBadgeService,
    public authService: AuthService,
  ) {}

  ngOnInit(): void {
    this.requestId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadRequest(); // buildDeadlineForm sera appelé dedans
  }

  loadRequest(): void {
    this.isLoading.set(true);
    this.requestService.getById(this.requestId).subscribe({
      next: (data) => {
        this.request.set(data);
        this.buildDeadlineForm(); // ← ICI seulement, après que data est disponible
        this.isLoading.set(false);
        console.log('Status:', data.status);
        console.log('Samples:', data.samples);
        console.log('canEditDeadlines:', this.canEditDeadlines());
        console.log('isCreator:', this.isCreator());
        console.log('deadlineForm:', this.deadlineForm);

        // Marquer les notifications liées à cette demande comme lues
        this.notificationService.markAsReadByRequestId(this.requestId);
        // Rafraîchir le badge dans la sidebar/header
        setTimeout(() => this.badgeService.refresh(), 500);
      },
      error: () => this.isLoading.set(false),
    });

    this.requestService.getHistory(this.requestId).subscribe({
      next: (data) => this.history.set(data),
    });

    this.loadDeadlines();

    // Charger l'historique pour tous les rôles
    this.requestService.getHistory(this.requestId).subscribe({
      next: (data) => this.history.set(data),
    });

    this.loadDeadlines();
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

  openAssignModal(): void {
    this.userService.getAnalysts().subscribe({
      next: (data) => this.analysts.set(data),
    });
    this.showAssignModal.set(true);
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

  get deadlinesBySample(): Map<number | null, DeadlineDto[]> {
    const map = new Map<number | null, DeadlineDto[]>();
    this.deadlines().forEach((d) => {
      const key = d.sampleId ?? null;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(d);
    });
    return map;
  }

  // Vérifier si les échéances peuvent être modifiées
  canEditDeadlines(): boolean {
    const status = this.request()?.status;
    return (status === 'Draft' || status === 'Submitted') && this.isCreator();
  }

  buildDeadlineForm(): void {
    // Un groupe par échantillon (les phases sont les mêmes pour chaque)
    const req = this.request();
    if (!req) return; // ← sécurité

    const groups: any = {};
    req.samples.forEach((s) => {
      groups[`sample_${s.id}`] = this.buildPhaseGroup();
    });
    this.deadlineForm = this.fb.group(groups);
  }

  loadDeadlines(): void {
    this.requestService.getDeadlines(this.requestId).subscribe({
      next: (data) => this.deadlines.set(data),
    });
  }

  private buildPhaseGroup(): FormGroup {
    return this.fb.group({
      reception: [''],
      assignment: [''],
      analysis: [''],
      validation: [''],
      resultDelivery: [''],
    });
  }

  saveDeadlines(): void {
    const dto: any[] = [];
    const req = this.request();
    if (!req) return;

    const addPhases = (group: any, sampleId?: number) => {
      const phases = [
        { key: 'reception', phase: 'Reception' },
        { key: 'assignment', phase: 'Assignment' },
        { key: 'analysis', phase: 'Analysis' },
        { key: 'validation', phase: 'Validation' },
        { key: 'resultDelivery', phase: 'ResultDelivery' },
      ];

      phases.forEach((p) => {
        if (group[p.key]) {
          // Fix timezone — conserver l'heure locale
          const local = new Date(group[p.key]);
          const offset = local.getTimezoneOffset() * 60000;
          const adjusted = new Date(local.getTime() - offset);

          dto.push({
            phase: p.phase,
            plannedDate: adjusted.toISOString(),
            sampleId: sampleId ?? null,
          });
        }
      });
    };

    req.samples.forEach((s) => {
      const group = this.deadlineForm.get(`sample_${s.id}`)?.value;
      if (group) addPhases(group, s.id);
    });

    if (dto.length === 0) {
      this.showError('Renseignez au moins une échéance.');
      return;
    }

    this.actionLoading.set(true);
    this.requestService.setDeadlines(this.requestId, dto).subscribe({
      next: () => {
        this.loadDeadlines();
        this.showDeadlineForm.set(false);
        this.showSuccess('Échéances enregistrées avec succès.');
        this.actionLoading.set(false);
      },
      error: (err) => {
        // Afficher le message d'erreur du backend (ex: date passée)
        const msg =
          err.error?.message ??
          err.error?.detail ??
          "Erreur lors de l'enregistrement des échéances.";
        this.showError(msg);
        this.actionLoading.set(false);
      },
    });
  }

  deleteDeadline(deadlineId: number): void {
    if (!confirm('Supprimer cette échéance ?')) return;

    // Trouver l'échéance à supprimer pour connaître sa phase et son sampleId
    const deadline = this.deadlines().find((d) => d.id === deadlineId);

    this.requestService.deleteDeadline(this.requestId, deadlineId).subscribe({
      next: () => {
        // Supprimer de la liste
        this.deadlines.update((list) => list.filter((d) => d.id !== deadlineId));

        // Vider le champ correspondant dans le formulaire
        if (deadline && this.deadlineForm) {
          const phaseKeyMap: Record<string, string> = {
            Reception: 'reception',
            Assignment: 'assignment',
            Analysis: 'analysis',
            Validation: 'validation',
            ResultDelivery: 'resultDelivery',
          };
          const key = phaseKeyMap[deadline.phase];
          const sampleKey = `sample_${deadline.sampleId}`;
          this.deadlineForm.get(`${sampleKey}.${key}`)?.setValue('');
        }

        this.showSuccess('Échéance supprimée.');
      },
      error: (err) => this.showError(err.error?.message),
    });
  }

  // Calcul temps réel du retard
  isDeadlineOverdue(deadline: DeadlineDto): boolean {
    return !deadline.actualDate && new Date(deadline.plannedDate) < new Date();
  }

  // Noms des phases
  getPhaseLabel(phase: string): string {
    const map: Record<string, string> = {
      Reception: 'Réception',
      Assignment: 'Assignation',
      Analysis: 'Analyse',
      Validation: 'Validation',
      ResultDelivery: 'Livraison des résultats',
    };
    return map[phase] ?? phase;
  }

  isCreator(): boolean {
    const userId = this.authService.currentUser()?.userId;
    return this.request()?.clientId === userId || this.authService.hasRole('Administrator');
  }

  validateChronologicalOrder(sampleId: number): string {
    const group = this.deadlineForm.get(`sample_${sampleId}`)?.value;
    if (!group) return '';

    const phases = [
      { key: 'reception', label: 'Réception' },
      { key: 'assignment', label: 'Assignation' },
      { key: 'analysis', label: 'Analyse' },
      { key: 'validation', label: 'Validation' },
      { key: 'resultDelivery', label: 'Livraison' },
    ];

    const dates = phases
      .filter((p) => group[p.key])
      .map((p) => ({ label: p.label, date: new Date(group[p.key]) }));

    for (let i = 1; i < dates.length; i++) {
      if (dates[i].date <= dates[i - 1].date) {
        return `⚠ L'échéance "${dates[i].label}" doit être après "${dates[i - 1].label}".`;
      }
    }
    return '';
  }

  readonly phaseList = [
    { key: 'reception', label: 'Réception', order: 1 },
    { key: 'assignment', label: 'Assignation', order: 2 },
    { key: 'analysis', label: 'Analyse', order: 3 },
    { key: 'validation', label: 'Validation', order: 4 },
    { key: 'resultDelivery', label: 'Livraison résultats', order: 5 },
  ];

  getPhaseOrder(phase: string): number {
    return (
      this.phaseList.find(
        (p) =>
          p.key.toLowerCase() === phase.toLowerCase() ||
          p.label.toLowerCase() === phase.toLowerCase(),
      )?.order ?? 0
    );
  }
}
