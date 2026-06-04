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
  selectedBrand = signal<string>('');
  showBrandError = signal(false);

  readonly brands = [
    { value: 'DICK', label: 'DICK', color: '#991B1B', icon: '🔴' },
    { value: 'SNA', label: 'SNA', color: '#1E3A8A', icon: '🔵' },
    { value: 'GIPA', label: 'GIPA', color: '#7C3AED', icon: '🟣' },
    { value: 'MEDOIL', label: 'MEDOIL', color: '#B45309', icon: '🟠' },
  ];

  private readonly brandConfig: Record<
    string,
    {
      color: string;
      lightColor: string;
      textColor: string;
      label: string;
    }
  > = {
    DICK: { color: '#991B1B', lightColor: '#FEF2F2', textColor: '#7F1D1D', label: 'DICK' },
    SNA: { color: '#1E3A8A', lightColor: '#EFF6FF', textColor: '#1E3A8A', label: 'SNA' },
    GIPA: { color: '#7C3AED', lightColor: '#F5F3FF', textColor: '#6D28D9', label: 'GIPA' },
    MEDOIL: { color: '#B45309', lightColor: '#FFFBEB', textColor: '#92400E', label: 'MEDOIL' },
  };

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
        const sampleGroups =
          req.samples.length > 0
            ? req.samples.map((sample) => {
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
            : [this.createSample()];

        this.form = this.fb.group({
          laboratoryId: [req.laboratoryId ?? null],
          notes: [req.notes ?? ''],
          isDraft: [req.isDraft ?? true],
          samples: this.fb.array(sampleGroups),
        });
        if (req.brand) {
          this.selectedBrand.set(req.brand);
        }
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
      const remaining = this.samples.controls
        .filter((_, i) => i !== index)
        .map((c) => c as FormGroup);
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
    if (this.currentStep() === 1) {
      if (!this.form.get('laboratoryId')!.value || !this.selectedBrand()) {
        this.showBrandError.set(true);
        return;
      }
    }
    this.showBrandError.set(false);
    this.currentStep.update((s) => s + 1);
  }

  prevStep(): void {
    if (this.currentStep() > 1) this.currentStep.update((s) => s - 1);
  }

  canGoNext(): boolean {
    if (this.currentStep() === 1) {
      return !!this.form.get('laboratoryId')!.value && !!this.selectedBrand();
    }
    return true;
  }

  // -------------------------------------------------------
  // Validation
  // -------------------------------------------------------
  isFormCompleteForSubmit(): boolean {
    if (!this.form.get('laboratoryId')!.value) return false;
    if (!this.selectedBrand()) return false;
    return this.samples.controls.every((s) => {
      const names = (s.get('analysisNames') as FormArray).controls;
      return (
        s.get('type')!.value?.trim() &&
        s.get('characteristics')!.value?.trim() &&
        s.get('quantity')!.value > 0 &&
        s.get('unit')!.value?.trim() &&
        names.some((n) => n.value?.trim()) &&
        s.get('urgencyLevel')!.value
      ); // ← urgence obligatoire
    });
  }

  hasNoAnalysisNames(sampleIndex: number): boolean {
    return this.getAnalysisNames(sampleIndex).controls.every((c) => !c.value?.trim());
  }

  // -------------------------------------------------------
  // Marque
  // -------------------------------------------------------
  getBrandConfig() {
    return (
      this.brandConfig[this.selectedBrand()] ?? {
        color: '#7366FF',
        lightColor: '#F5F3FF',
        textColor: '#5b4fd4',
        label: '',
      }
    );
  }

  selectBrand(brand: string): void {
    this.selectedBrand.set(brand);
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
      brand: this.selectedBrand(),
      laboratoryId: this.form.value.laboratoryId ?? 0,
      samples: this.form.value.samples
        .filter((s: any) => {
          if (!isDraft) return true;
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
          urgencyLevel: 'Normal',
          urgencyDescription: '',
          isPerishable: false,
          expiryDate: null,
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

  readonly brandFieldConfig: Record<
    string,
    {
      sampleTypeLabel: string;
      sampleTypePlaceholder: string;
      characteristicsLabel: string;
      characteristicsPlaceholder: string;
      extraFields: { key: string; label: string; placeholder: string }[];
    }
  > = {
    DICK: {
      sampleTypeLabel: 'Espèce animale *',
      sampleTypePlaceholder: 'Ex: Poulet, Dinde, Vache...',
      characteristicsLabel: 'Description / Symptômes',
      characteristicsPlaceholder: 'Ex: Poulets de 6 semaines, mortalité élevée...',
      extraFields: [],
    },
    SNA: {
      sampleTypeLabel: "Type d'huile *",
      sampleTypePlaceholder: 'Ex: Huile moteur, Huile hydraulique...',
      characteristicsLabel: 'Grade / Spécification',
      characteristicsPlaceholder: 'Ex: SAE 10W-40, ISO VG 46...',
      extraFields: [],
    },
    GIPA: {
      sampleTypeLabel: 'Type de lubrifiant *',
      sampleTypePlaceholder: 'Ex: Lubrifiant industriel, Graisse...',
      characteristicsLabel: 'Application / Usage',
      characteristicsPlaceholder: 'Ex: Compresseur, Engrenage, Roulement...',
      extraFields: [],
    },
    MEDOIL: {
      sampleTypeLabel: 'Corps gras / Huile *',
      sampleTypePlaceholder: "Ex: Huile d'olive, Huile de tournesol...",
      characteristicsLabel: 'Origine / Qualité',
      characteristicsPlaceholder: 'Ex: Première pression à froid, Raffinée...',
      extraFields: [],
    },
  };

  getFieldConfig() {
    return (
      this.brandFieldConfig[this.selectedBrand()] ?? {
        sampleTypeLabel: "Type d'échantillon *",
        sampleTypePlaceholder: 'Ex: Huile, Eau industrielle...',
        characteristicsLabel: 'Caractéristiques',
        characteristicsPlaceholder: "Décrivez l'échantillon...",
        extraFields: [],
      }
    );
  }
}
