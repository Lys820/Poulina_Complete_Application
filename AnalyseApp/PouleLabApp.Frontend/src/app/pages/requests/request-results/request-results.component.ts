import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule } from '@angular/forms';
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
    const resultsArray = data.samples.flatMap((s) =>
      s.results.map((r) =>
        this.fb.group({
          resultId: [r.id],
          analysisName: [r.analysisName],
          measuredValue: [r.measuredValue === 0 ? null : r.measuredValue],
          lowerBound: [r.lowerBound || null],
          upperBound: [r.upperBound || null],
          unit: [r.unit || ''],
          isAnomaly: [r.isAnomaly],
        }),
      ),
    );

    this.form = this.fb.group({
      results: this.fb.array(resultsArray),
    });

    // Recalculer IsAnomaly en temps réel
    this.results.controls.forEach((ctrl) => {
      const recalculate = () => {
        const val = ctrl.get('measuredValue')!.value;
        const lb = ctrl.get('lowerBound')!.value;
        const ub = ctrl.get('upperBound')!.value;
        if (val !== null && lb !== null && ub !== null) {
          ctrl
            .get('isAnomaly')!
            .setValue(Number(val) < Number(lb) || Number(val) > Number(ub), { emitEvent: false });
        }
      };
      ctrl.get('measuredValue')!.valueChanges.subscribe(recalculate);
      ctrl.get('lowerBound')!.valueChanges.subscribe(recalculate);
      ctrl.get('upperBound')!.valueChanges.subscribe(recalculate);
    });
  }

  get results(): FormArray {
    return this.form.get('results') as FormArray;
  }

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

  saveResults(): void {
    const hasEmpty = this.results.controls.some(
      (ctrl) => ctrl.get('measuredValue')!.value === null || !ctrl.get('unit')!.value?.trim(),
    );

    if (hasEmpty) {
      this.errorMsg.set('Veuillez renseigner toutes les valeurs, bornes et unités.');
      return;
    }

    this.isSaving.set(true);
    this.errorMsg.set('');

    const dto = this.results.controls.map((ctrl) => ({
      resultId: ctrl.get('resultId')!.value,
      measuredValue: Number(ctrl.get('measuredValue')!.value),
      lowerBound: Number(ctrl.get('lowerBound')!.value ?? 0),
      upperBound: Number(ctrl.get('upperBound')!.value ?? 0),
      unit: ctrl.get('unit')!.value,
    }));

    this.requestService.saveResults(this.requestId, dto).subscribe({
      next: (data) => {
        this.request.set(data);
        this.buildForm(data);
        this.isSaving.set(false);
        this.showSuccess('Résultats sauvegardés.');
      },
      error: (err) => {
        this.isSaving.set(false);
        this.errorMsg.set(err.error?.message ?? 'Erreur lors de la sauvegarde.');
      },
    });
  }

  completeAnalysis(): void {
    this.isSaving.set(true);
    const dto = this.results.controls.map((ctrl) => ({
      resultId: ctrl.get('resultId')!.value,
      measuredValue: Number(ctrl.get('measuredValue')!.value),
      lowerBound: Number(ctrl.get('lowerBound')!.value ?? 0),
      upperBound: Number(ctrl.get('upperBound')!.value ?? 0),
      unit: ctrl.get('unit')!.value,
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
        this.errorMsg.set(err.error?.message ?? 'Erreur.');
      },
    });
  }

  private showSuccess(msg: string): void {
    this.successMsg.set(msg);
    setTimeout(() => this.successMsg.set(''), 4000);
  }
}
