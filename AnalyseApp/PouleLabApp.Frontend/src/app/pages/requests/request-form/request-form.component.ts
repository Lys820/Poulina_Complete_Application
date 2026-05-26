import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { LaboratoryService } from '../../../core/services/laboratory.service';
import { RequestService } from '../../../core/services/request.service';
import { Laboratory } from '../../../core/models/laboratory.model';

@Component({
  selector: 'app-request-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './request-form.component.html',
  styleUrls: ['./request-form.component.scss'],
})
export class RequestFormComponent implements OnInit {
  form!: FormGroup;
  laboratories = signal<Laboratory[]>([]);
  isLoading = signal(false);
  errorMessage = signal('');
  currentStep = signal(1);
  totalSteps = 3;
  isEditMode = signal(false);
  requestId = signal<number | null>(null);

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private labService: LaboratoryService,
    private requestService: RequestService,
  ) {}

  ngOnInit(): void {
    this.buildForm();
    this.loadData();

    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.requestId.set(Number(id));
      this.isEditMode.set(true);
    }
  }

  buildForm(): void {
    this.form = this.fb.group({
      laboratoryId: [null],
      notes: [''],
      isDraft: [true],
      samples: this.fb.array([this.createSample()]),
    });
  }

  loadData(): void {
    this.labService.getLaboratories().subscribe({
      next: (labs) => {
        this.laboratories.set(labs);
        if (this.isEditMode() && this.requestId()) {
          this.loadExistingRequest(this.requestId()!);
        }
      },
    });
  }

  loadExistingRequest(id: number): void {
    this.requestService.getById(id).subscribe({
      next: (req) => {
        // Construire les groupes échantillons depuis la demande existante
        const sampleGroups =
          req.samples.length > 0
            ? req.samples.map((sample) => {
                // Restaurer les noms d'analyses ou mettre un champ vide
                const names =
                  sample.results.length > 0
                    ? sample.results.map((r) => this.fb.control(r.analysisName))
                    : [this.fb.control('')];

                return this.fb.group({
                  type: [sample.type ?? ''],
                  characteristics: [sample.characteristics ?? ''],
                  quantity: [sample.quantity ?? null],
                  unit: [sample.unit ?? ''],
                  analysisNames: this.fb.array(names),
                });
              })
            : [this.createSample()]; // Aucun échantillon → un vide par défaut

        // Reconstruire entièrement le formulaire avec les données existantes
        this.form = this.fb.group({
          laboratoryId: [req.laboratoryId ?? null],
          notes: [req.notes ?? ''],
          isDraft: [req.isDraft ?? true],
          samples: this.fb.array(sampleGroups),
        });
      },
      error: (err) => {
        console.error('Erreur lors du chargement de la demande :', err);
        this.errorMessage.set('Impossible de charger la demande.');
      },
    });
  }

  // -------------------------------------------------------
  // Gestion des échantillons
  // -------------------------------------------------------
  get samples(): FormArray {
    return this.form.get('samples') as FormArray;
  }

  createSample(): FormGroup {
    return this.fb.group({
      type: [''],
      characteristics: [''],
      quantity: [null],
      unit: [''],
      analysisNames: this.fb.array([this.fb.control('')]),
    });
  }

  addSample(): void {
    this.samples.push(this.createSample());
  }

  removeSample(index: number): void {
    if (this.samples.length > 1) {
      // Récupérer tous les groupes sauf celui à supprimer
      const remaining = this.samples.controls
        .filter((_, i) => i !== index)
        .map((c) => c as FormGroup);

      // Reconstruire le FormArray entièrement
      this.form.setControl('samples', this.fb.array(remaining));
    }
  }

  // -------------------------------------------------------
  // Gestion des noms d'analyses
  // -------------------------------------------------------
  getAnalysisNames(sampleIndex: number): FormArray {
    return this.samples.at(sampleIndex).get('analysisNames') as FormArray;
  }

  addAnalysisName(sampleIndex: number): void {
    this.getAnalysisNames(sampleIndex).push(this.fb.control(''));
  }

  removeAnalysisName(sampleIndex: number, nameIndex: number): void {
    const arr = this.getAnalysisNames(sampleIndex);
    if (arr.length > 1) arr.removeAt(nameIndex);
  }

  // -------------------------------------------------------
  // Navigation
  // -------------------------------------------------------
  nextStep(): void {
    if (this.currentStep() < this.totalSteps) this.currentStep.update((s) => s + 1);
  }

  prevStep(): void {
    if (this.currentStep() > 1) this.currentStep.update((s) => s - 1);
  }

  // -------------------------------------------------------
  // Validation
  // -------------------------------------------------------
  isFormCompleteForSubmit(): boolean {
    if (!this.form.get('laboratoryId')!.value) return false;
    return this.samples.controls.every((s) => {
      const names = (s.get('analysisNames') as FormArray).controls;
      return (
        s.get('type')!.value?.trim() &&
        s.get('characteristics')!.value?.trim() &&
        s.get('quantity')!.value > 0 &&
        s.get('unit')!.value?.trim() &&
        names.some((n) => n.value?.trim())
      );
    });
  }

  hasNoAnalysisNames(sampleIndex: number): boolean {
    return this.getAnalysisNames(sampleIndex).controls.every((c) => !c.value?.trim());
  }

  // -------------------------------------------------------
  // Soumission
  // -------------------------------------------------------
  submit(isDraft: boolean): void {
    if (!isDraft) {
      if (!this.form.get('laboratoryId')!.value) {
        this.errorMessage.set('Veuillez sélectionner un laboratoire.');
        return;
      }
      if (!this.isFormCompleteForSubmit()) {
        this.errorMessage.set(
          'Remplissez tous les champs et ajoutez au moins une analyse par échantillon.',
        );
        return;
      }
    }

    const formValue = {
      ...this.form.value,
      isDraft,
      laboratoryId: this.form.value.laboratoryId ?? 0,
      samples: this.form.value.samples
        .filter((s: any) => {
          if (!isDraft) return true;
          // Conserver si au moins un champ est rempli
          return (
            s.type?.trim() ||
            s.characteristics?.trim() ||
            (s.quantity && s.quantity > 0) ||
            s.analysisNames?.some((n: string) => n?.trim())
          );
        })
        .map((s: any) => ({
          type: s.type || '',
          characteristics: s.characteristics || '',
          quantity: s.quantity ?? 0,
          unit: s.unit || '',
          analysisNames: (s.analysisNames || []).filter((n: string) => n?.trim()),
        })),
    };

    this.isLoading.set(true);
    this.errorMessage.set('');

    const action =
      this.isEditMode() && this.requestId()
        ? this.requestService.update(this.requestId()!, formValue)
        : this.requestService.create(formValue);

    action.subscribe({
      next: (result) => {
        this.isLoading.set(false);
        this.router.navigate(['/app/requests', result.id]);
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(err.error?.detail ?? "Erreur lors de l'enregistrement.");
      },
    });
  }
}
