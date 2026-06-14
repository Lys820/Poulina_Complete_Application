import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormsModule,
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
} from '@angular/forms';
import { LaboratoryService } from '../../core/services/laboratory.service';
<<<<<<< HEAD
=======
import { extractErrorMessage } from '../../core/utils/error.utils';
>>>>>>> origin/Lilia

@Component({
  selector: 'app-laboratory-list',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './laboratory-list.component.html',
  styleUrls: ['./laboratory-list.component.scss'],
})
export class LaboratoryListComponent implements OnInit {
  labs = signal<any[]>([]);
  isLoading = signal(true);
  successMsg = signal('');
  errorMsg = signal('');

  showCreateModal = signal(false);
  showEditModal = signal(false);
  showDeleteModal = signal(false);
  editingLab = signal<any | null>(null);
  deletingLab = signal<any | null>(null);
  isSaving = signal(false);

  form!: FormGroup;

  constructor(
    private labService: LaboratoryService,
    private fb: FormBuilder,
  ) {}

  ngOnInit(): void {
    this.buildForm();
    this.loadLabs();
  }

  buildForm(): void {
    this.form = this.fb.group({
      name: ['', Validators.required],
      description: [''],
<<<<<<< HEAD
      address: [''],
=======
      address: ['', Validators.required],
>>>>>>> origin/Lilia
    });
  }

  loadLabs(): void {
    this.isLoading.set(true);
    this.labService.getAll().subscribe({
<<<<<<< HEAD
      next: (data) => {
        this.labs.set(data);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
=======
      next: (data: any[]) => {
        this.labs.set(data);
        this.isLoading.set(false);
      },
      error: (err: unknown) => {
        this.isLoading.set(false);
        this.showError(extractErrorMessage(err));
      },
>>>>>>> origin/Lilia
    });
  }

  openCreate(): void {
    this.form.reset();
    this.showCreateModal.set(true);
  }

  openEdit(lab: any): void {
    this.editingLab.set(lab);
    this.form.patchValue({
      name: lab.name,
      description: lab.description,
      address: lab.address,
    });
    this.showEditModal.set(true);
  }

  openDelete(lab: any): void {
    this.deletingLab.set(lab);
    this.showDeleteModal.set(true);
  }

  create(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.isSaving.set(true);
    this.labService.create(this.form.value).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.showCreateModal.set(false);
        this.loadLabs();
        this.showSuccess('Laboratoire créé avec succès.');
      },
<<<<<<< HEAD
      error: (err) => {
        this.isSaving.set(false);
        this.showError(err.error?.message);
=======
      error: (err: unknown) => {
        this.isSaving.set(false);
        this.showError(extractErrorMessage(err));
>>>>>>> origin/Lilia
      },
    });
  }

  saveEdit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const lab = this.editingLab();
    if (!lab) return;
    this.isSaving.set(true);
    this.labService.update(lab.id, this.form.value).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.showEditModal.set(false);
        this.loadLabs();
<<<<<<< HEAD
        this.showSuccess('Laboratoire mis à jour avec succès.');
      },
      error: (err) => {
        this.isSaving.set(false);
        this.showError(err.error?.message);
=======
        this.showSuccess('Laboratoire mis à jour.');
      },
      error: (err: unknown) => {
        this.isSaving.set(false);
        this.showError(extractErrorMessage(err));
>>>>>>> origin/Lilia
      },
    });
  }

  deleteLab(): void {
    const lab = this.deletingLab();
    if (!lab) return;
    this.labService.delete(lab.id).subscribe({
      next: () => {
        this.showDeleteModal.set(false);
        this.loadLabs();
        this.showSuccess('Laboratoire supprimé.');
      },
<<<<<<< HEAD
      error: (err) => {
        this.showDeleteModal.set(false);
        this.showError(err.error?.message);
=======
      error: (err: unknown) => {
        this.showDeleteModal.set(false);
        this.showError(extractErrorMessage(err));
>>>>>>> origin/Lilia
      },
    });
  }

  private showSuccess(msg: string): void {
    this.successMsg.set(msg);
    setTimeout(() => this.successMsg.set(''), 3000);
  }

  private showError(msg: string): void {
    this.errorMsg.set(msg ?? 'Une erreur est survenue.');
    setTimeout(() => this.errorMsg.set(''), 4000);
  }
}
