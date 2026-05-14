import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import {
  FormBuilder,
  FormGroup,
  FormArray,
  FormControl,
  ReactiveFormsModule,
} from '@angular/forms';
import { RequestService } from '../../../core/services/request.service';
import { AuthService } from '../../../core/services/auth.service';
import { RequestDetailDto } from '../../../core/models/request.model';

@Component({
  selector: 'app-request-results',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './request-results.component.html',
  styleUrls: ['./request-results.component.scss'],
})
export class RequestResultsComponent implements OnInit {
  request = signal<RequestDetailDto | null>(null);
  isLoading = signal(true);
  isSaving = signal(false);
  successMsg = signal('');
  errorMsg = signal('');
  form!: FormGroup;
  requestId!: number;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private fb: FormBuilder,
    private requestService: RequestService,
    public authService: AuthService,
  ) {}

  ngOnInit(): void {
    this.requestId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadRequest();
  }

  loadRequest(): void {
    this.requestService.getById(this.requestId).subscribe({
      next: (data) => {
        this.request.set(data);
        this.buildForm(data);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  buildForm(data: RequestDetailDto): void {
    // Créer un contrôle par résultat dans tous les échantillons
    const resultsArray = data.samples.flatMap((s) =>
      s.results.map((r) =>
        this.fb.group({
          resultId: [r.id],
          measuredValue: [r.measuredValue === 0 ? null : r.measuredValue],
          // Infos en lecture seule pour l'affichage
          analysisTypeName: [r.analysisTypeName],
          lowerBound: [r.lowerBound],
          upperBound: [r.upperBound],
          unit: [r.unit],
          isAnomaly: [r.isAnomaly],
        }),
      ),
    );

    this.form = this.fb.group({
      results: this.fb.array(resultsArray),
    });

    // Recalculer IsAnomaly en temps réel
    this.results.controls.forEach((ctrl, i) => {
      ctrl.get('measuredValue')!.valueChanges.subscribe((val) => {
        const lb = ctrl.get('lowerBound')!.value;
        const ub = ctrl.get('upperBound')!.value;
        const isAnomaly = val !== null && val !== '' && (Number(val) < lb || Number(val) > ub);
        ctrl.get('isAnomaly')!.setValue(isAnomaly, { emitEvent: false });
      });
    });
  }

  get results(): FormArray {
    return this.form.get('results') as FormArray;
  }

  // Trouver les résultats d'un échantillon spécifique
  getResultsForSample(sampleId: number): any[] {
    const req = this.request();
    if (!req) return [];
    const sample = req.samples.find((s) => s.id === sampleId);
    if (!sample) return [];

    return this.results.controls.filter((ctrl) =>
      sample.results.some((r) => r.id === ctrl.get('resultId')!.value),
    );
  }

  // Sauvegarder les résultats
  saveResults(): void {
    const hasEmpty = this.results.controls.some(
      (ctrl) =>
        ctrl.get('measuredValue')!.value === null || ctrl.get('measuredValue')!.value === '',
    );

    if (hasEmpty) {
      this.errorMsg.set('Veuillez renseigner toutes les valeurs avant de sauvegarder.');
      return;
    }

    this.isSaving.set(true);
    this.errorMsg.set('');

    const dto = this.results.controls.map((ctrl) => ({
      resultId: ctrl.get('resultId')!.value,
      measuredValue: Number(ctrl.get('measuredValue')!.value),
    }));

    this.requestService.saveResults(this.requestId, dto).subscribe({
      next: (data) => {
        this.request.set(data);
        this.buildForm(data);
        this.isSaving.set(false);
        this.showSuccess('Résultats sauvegardés avec succès.');
      },
      error: (err) => {
        this.isSaving.set(false);
        this.errorMsg.set(err.error?.message ?? 'Erreur lors de la sauvegarde.');
      },
    });
  }

  // Terminer les analyses et envoyer au chef de labo
  completeAnalysis(): void {
    const hasEmpty = this.results.controls.some(
      (ctrl) =>
        ctrl.get('measuredValue')!.value === null || ctrl.get('measuredValue')!.value === '',
    );

    if (hasEmpty) {
      this.errorMsg.set('Renseignez toutes les valeurs avant de terminer.');
      return;
    }

    // Sauvegarder d'abord, puis terminer
    this.isSaving.set(true);
    const dto = this.results.controls.map((ctrl) => ({
      resultId: ctrl.get('resultId')!.value,
      measuredValue: Number(ctrl.get('measuredValue')!.value),
    }));

    this.requestService.saveResults(this.requestId, dto).subscribe({
      next: () => {
        this.requestService.completeAnalysis(this.requestId).subscribe({
          next: () => {
            this.isSaving.set(false);
            this.router.navigate(['/app/requests', this.requestId]);
          },
          error: (err) => {
            this.isSaving.set(false);
            this.errorMsg.set(err.error?.message ?? 'Erreur.');
          },
        });
      },
      error: (err) => {
        this.isSaving.set(false);
        this.errorMsg.set(err.error?.message ?? 'Erreur lors de la sauvegarde.');
      },
    });
  }

  private showSuccess(msg: string): void {
    this.successMsg.set(msg);
    setTimeout(() => this.successMsg.set(''), 4000);
  }

  // Retourne l'index global d'un résultat dans le FormArray
  getResultIndex(sampleId: number, resultId: number): number {
    const req = this.request();
    if (!req) return -1;
    let idx = 0;
    for (const sample of req.samples) {
      for (const result of sample.results) {
        if (result.id === resultId) return idx;
        idx++;
      }
    }
    return -1;
  }
}
