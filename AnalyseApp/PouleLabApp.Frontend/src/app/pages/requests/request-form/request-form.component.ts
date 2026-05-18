import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { LaboratoryService } from '../../../core/services/laboratory.service';
import { RequestService } from '../../../core/services/request.service';
import { Laboratory, AnalysisType } from '../../../core/models/laboratory.model';

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
  analysisTypes = signal<AnalysisType[]>([]);
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

    // Détecter le mode édition
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.requestId.set(Number(id));
      this.isEditMode.set(true);
    }
  }

  buildForm(): void {
    this.form = this.fb.group({
      laboratoryId: [null], // ← pas de Validators.required
      notes: [''],
      isDraft: [true],
      samples: this.fb.array([this.createSample()]),
    });
  }

  loadData(): void {
    this.labService.getLaboratories().subscribe({
      next: (labs) => {
        this.laboratories.set(labs);
        // Charger la demande existante APRÈS avoir les données
        if (this.isEditMode() && this.requestId()) {
          this.loadExistingRequest(this.requestId()!);
        }
      },
    });
    this.labService.getAnalysisTypes().subscribe({
      next: (types) => this.analysisTypes.set(types),
    });
  }

  loadExistingRequest(id: number): void {
    this.requestService.getById(id).subscribe({
      next: (req) => {
        // Vider les échantillons existants
        while (this.samples.length) {
          this.samples.removeAt(0);
        }

        // Pré-remplir les infos de base
        this.form.patchValue({
          laboratoryId: req.laboratoryId,
          notes: req.notes,
          isDraft: req.isDraft,
        });

        // Recréer les échantillons avec leurs valeurs
        req.samples.forEach((sample) => {
          const sampleGroup = this.createSample();
          sampleGroup.patchValue({
            type: sample.type,
            characteristics: sample.characteristics,
            quantity: sample.quantity,
            unit: sample.unit,
            analysisTypeIds: sample.results.map((r) => r.analysisTypeId),
          });
          this.samples.push(sampleGroup);
        });

        // Si aucun échantillon, en ajouter un vide
        if (this.samples.length === 0) {
          this.samples.push(this.createSample());
        }
      },
    });
  }

  // -------------------------------------------------------
  // Gestion des échantillons — sans validators obligatoires
  // -------------------------------------------------------
  get samples(): FormArray {
    return this.form.get('samples') as FormArray;
  }

  createSample(): FormGroup {
    return this.fb.group({
      type: [''], // ← pas de Validators.required
      characteristics: [''],
      quantity: [null],
      unit: [''],
      analysisTypeIds: [[]],
    });
  }

  addSample(): void {
    this.samples.push(this.createSample());
  }

  removeSample(index: number): void {
    if (this.samples.length > 1) {
      this.samples.removeAt(index);
    }
  }

  toggleAnalysisType(sampleIndex: number, typeId: number): void {
    const control = this.samples.at(sampleIndex).get('analysisTypeIds')!;
    const current: number[] = control.value;
    const idx = current.indexOf(typeId);
    if (idx === -1) {
      control.setValue([...current, typeId]);
    } else {
      control.setValue(current.filter((id) => id !== typeId));
    }
  }

  isTypeSelected(sampleIndex: number, typeId: number): boolean {
    return (this.samples.at(sampleIndex).get('analysisTypeIds')!.value as number[]).includes(
      typeId,
    );
  }

  hasNoAnalysisTypes(sampleIndex: number): boolean {
    return (this.samples.at(sampleIndex).get('analysisTypeIds')!.value as number[]).length === 0;
  }

  // -------------------------------------------------------
  // Navigation libre entre étapes
  // -------------------------------------------------------
  nextStep(): void {
    if (this.currentStep() < this.totalSteps) {
      this.currentStep.update((s) => s + 1);
    }
  }

  prevStep(): void {
    if (this.currentStep() > 1) {
      this.currentStep.update((s) => s - 1);
    }
  }

  // Plus de blocage sur la navigation
  canGoNext(): boolean {
    return true;
  }

  // -------------------------------------------------------
  // Validation avant soumission
  // -------------------------------------------------------
  isFormCompleteForSubmit(): boolean {
    // Labo obligatoire
    if (!this.form.get('laboratoryId')!.value) return false;

    // Chaque échantillon doit être complet
    return this.samples.controls.every(
      (s) =>
        s.get('type')!.value?.trim() &&
        s.get('characteristics')!.value?.trim() &&
        s.get('quantity')!.value > 0 &&
        s.get('unit')!.value?.trim() &&
        (s.get('analysisTypeIds')!.value as number[]).length > 0,
    );
  }

  // -------------------------------------------------------
  // Soumission
  // -------------------------------------------------------
  submit(isDraft: boolean): void {
    // Pour soumettre, valider que tout est rempli
    if (!isDraft) {
      // Vérifications explicites avec messages clairs
      if (!this.form.get('laboratoryId')!.value) {
        this.errorMessage.set('Veuillez sélectionner un laboratoire avant de soumettre.');
        return;
      }
      if (!this.isFormCompleteForSubmit()) {
        console.log('isDraft envoyé :', isDraft); // ← ajouter
        console.log('formValue :', this.form.value);
        this.errorMessage.set(
          'Veuillez remplir tous les champs obligatoires et sélectionner au moins une analyse par échantillon.',
        );
        return;
      }
    }

    const formValue = {
      ...this.form.value,
      isDraft,
      laboratoryId: this.form.value.laboratoryId ?? 0,
      samples: isDraft
        ? this.form.value.samples
            .filter((s: any) => s.type?.trim())
            .map((s: any) => ({
              ...s,
              quantity: s.quantity ?? 0, // ← null devient 0
            }))
        : this.form.value.samples.map((s: any) => ({
            ...s,
            quantity: s.quantity ?? 0, // ← null devient 0 aussi pour la soumission
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
