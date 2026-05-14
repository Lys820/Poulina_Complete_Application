import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, FormArray, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
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

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private route: ActivatedRoute,
    private labService: LaboratoryService,
    private requestService: RequestService,
  ) {}

  requestId = signal<number | null>(null);
  isEditMode = signal(false);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.requestId.set(Number(id));
      this.isEditMode.set(true);
      this.loadExistingRequest(Number(id));
    }
    this.buildForm();
    this.loadData();
  }

  loadExistingRequest(id: number): void {
    this.requestService.getById(id).subscribe({
      next: (req) => {
        this.form.patchValue({
          laboratoryId: req.laboratoryName,
          notes: req.notes,
          isDraft: req.isDraft,
        });
      },
    });
  }

  buildForm(): void {
    this.form = this.fb.group({
      laboratoryId: [null, Validators.required],
      notes: [''],
      isDraft: [false],
      samples: this.fb.array([this.createSample()]),
    });
  }

  loadData(): void {
    this.labService.getLaboratories().subscribe({
      next: (labs) => this.laboratories.set(labs),
    });
    this.labService.getAnalysisTypes().subscribe({
      next: (types) => this.analysisTypes.set(types),
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
      type: ['', Validators.required],
      characteristics: ['', Validators.required],
      quantity: [null, [Validators.required, Validators.min(0.01)]],
      unit: ['', Validators.required],
      analysisTypeIds: [[], Validators.required],
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

  // -------------------------------------------------------
  // Gestion des types d'analyses par échantillon
  // -------------------------------------------------------
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
    const current: number[] = this.samples.at(sampleIndex).get('analysisTypeIds')!.value;
    return current.includes(typeId);
  }

  // -------------------------------------------------------
  // Navigation entre étapes
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

  canGoNext(): boolean {
    if (this.currentStep() === 1) {
      return this.form.get('laboratoryId')!.valid;
    }
    if (this.currentStep() === 2) {
      return this.samples.controls.every(
        (s) =>
          s.get('type')!.valid &&
          s.get('characteristics')!.valid &&
          s.get('quantity')!.valid &&
          s.get('unit')!.valid,
      );
    }
    return true;
  }

  // -------------------------------------------------------
  // Soumission
  // -------------------------------------------------------
  submit(isDraft: boolean): void {
    this.form.patchValue({ isDraft });

    // Vérifier qu'au moins un type d'analyse est sélectionné par échantillon
    const hasAnalysisTypes = this.samples.controls.every(
      (s) => (s.get('analysisTypeIds')!.value as number[]).length > 0,
    );

    if (!isDraft && !hasAnalysisTypes) {
      this.errorMessage.set("Sélectionnez au moins un type d'analyse par échantillon.");
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    // Mode édition — PUT
    if (this.isEditMode() && this.requestId()) {
      this.requestService.update(this.requestId()!, this.form.value).subscribe({
        next: (result) => {
          this.isLoading.set(false);
          this.router.navigate(['/app/requests', result.id]);
        },
        error: (err) => {
          this.isLoading.set(false);
          this.errorMessage.set(err.error?.detail ?? 'Erreur lors de la modification.');
        },
      });
    } else {
      // Mode création — POST
      this.requestService.create(this.form.value).subscribe({
        next: (result) => {
          this.isLoading.set(false);
          this.router.navigate(['/app/requests', result.id]);
        },
        error: (err) => {
          this.isLoading.set(false);
          this.errorMessage.set(err.error?.detail ?? 'Erreur lors de la création.');
        },
      });
    }
  }

  // Vérifie si aucun type d'analyse n'est sélectionné pour un échantillon
  hasNoAnalysisTypes(sampleIndex: number): boolean {
    const value = this.samples.at(sampleIndex).get('analysisTypeIds')!.value;
    return (value as number[]).length === 0;
  }
}
