import { Component, OnInit, signal } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import {
  FormsModule,
  ReactiveFormsModule,
  FormBuilder,
  FormGroup,
  Validators,
} from '@angular/forms';
import { UserService } from '../../../core/services/user.service';
import { AuthService } from '../../../core/services/auth.service';
import { UserDto } from '../../../core/models/user.model';
import { RegisterComponent } from '../../auth/register/register.component';
import { RegisterFormComponent } from '../../auth/register/register-form.component';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, NgClass, RegisterFormComponent],
  templateUrl: './user-list.component.html',
  styleUrls: ['./user-list.component.scss'],
})
export class UserListComponent implements OnInit {
  users = signal<UserDto[]>([]);
  isLoading = signal(true);
  successMsg = signal('');
  errorMsg = signal('');

  // Filtre
  roleFilter = signal('');

  // Modal édition
  showEditModal = signal(false);
  editingUser = signal<UserDto | null>(null);
  editForm!: FormGroup;
  showCreateModal = signal(false);
  deleteUserId = signal<string | null>(null);
  deleteUserName = signal('');
  laboratories = signal<any[]>([]);

  readonly roles = ['Administrator', 'Manager', 'Receptionist', 'Analyst', 'LabChief', 'Client'];

  readonly roleLabels: Record<string, string> = {
    Administrator: 'Administrateur',
    Manager: 'Manager',
    Receptionist: 'Réceptionniste',
    Analyst: 'Laborantin',
    LabChief: 'Chef de labo',
    Client: 'Client',
  };

  constructor(
    private userService: UserService,
    private fb: FormBuilder,
    public authService: AuthService,
  ) {
    this.editForm = this.fb.group({
      firstName: ['', Validators.required],
      lastName: ['', Validators.required],
      email: ['', [Validators.required, Validators.email]],
      phoneNumber: [''],
      filialeName: [''],
      laboratoryId: [null], // ← ajouter
      role: ['', Validators.required],
      isActive: [true],
    });
  }
  ngOnInit(): void {
    this.loadUsers();
    this.userService.getLaboratories().subscribe({
      next: (labs: any[]) => this.laboratories.set(labs),
      error: () => {},
    });
  }

  loadUsers(): void {
    this.isLoading.set(true);
    this.userService.getAll().subscribe({
      next: (data) => {
        this.users.set(data);
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  get filteredUsers(): UserDto[] {
    const role = this.roleFilter();
    return role ? this.users().filter((u) => u.role === role) : this.users();
  }

  // Ouvrir modal édition
  openEdit(user: any): void {
    this.editingUser.set(user);
    this.editForm.patchValue({
      firstName: user.firstName,
      lastName: user.lastName,
      email: user.email,
      phoneNumber: user.phoneNumber,
      filialeName: user.filialeName,
      laboratoryId: user.laboratoryId ?? null, // ← ajouter
      role: user.role,
      isActive: user.isActive,
    });
    this.showEditModal.set(true);
  }

  // Sauvegarder modifications
  saveEdit(): void {
    const user = this.editingUser();
    if (!user) return;

    // Convertir isActive en boolean (évite le bug string/boolean)
    const formValue = {
      ...this.editForm.value,
      isActive: this.editForm.value.isActive === true || this.editForm.value.isActive === 'true',
    };

    this.userService.update(user.id, this.editForm.value).subscribe({
      next: () => {
        this.showEditModal.set(false);
        this.loadUsers();
        this.showSuccess('Utilisateur mis à jour avec succès.');
      },
      error: (err) => this.showError(err.error?.message),
    });
  }

  deactivate(user: any): void {
    const action = user.isActive ? 'désactiver' : 'réactiver';
    if (!confirm(`Voulez-vous ${action} le compte de ${user.firstName} ${user.lastName} ?`)) return;

    this.userService.toggleStatus(user.id).subscribe({
      next: () => this.loadUsers(),
      error: (err) => this.errorMsg.set(err.error?.message ?? 'Erreur.'),
    });
  }

  getRoleBadgeClass(role: string): string {
    const map: Record<string, string> = {
      Administrator: 'role-admin',
      Manager: 'role-manager',
      Receptionist: 'role-receptionist',
      Analyst: 'role-analyst',
      LabChief: 'role-labchief',
      Client: 'role-client',
    };
    return map[role] ?? 'role-client';
  }

  private showSuccess(msg: string): void {
    this.successMsg.set(msg);
    setTimeout(() => this.successMsg.set(''), 3000);
  }

  private showError(msg: string): void {
    this.errorMsg.set(msg ?? 'Une erreur est survenue.');
    setTimeout(() => this.errorMsg.set(''), 4000);
  }

  // Créer un utilisateur (depuis le modal)
  onUserCreated(): void {
    this.showCreateModal.set(false);
    this.loadUsers();
  }

  // Confirmer suppression
  confirmDelete(user: any): void {
    this.deleteUserId.set(user.id);
    this.deleteUserName.set(`${user.firstName} ${user.lastName}`);
  }

  deleteUser(): void {
    const id = this.deleteUserId();
    if (!id) return;

    this.userService.deleteUser(id).subscribe({
      next: () => {
        this.deleteUserId.set(null);
        this.loadUsers();
      },
      error: (err) => alert(err.error?.message ?? 'Erreur.'),
    });
  }

  isClientRole(role?: string): boolean {
    return (role ?? this.editForm.get('role')?.value) === 'Client';
  }

  isStaffRole(role?: string): boolean {
    return ['Receptionist', 'Analyst', 'LabChief'].includes(
      role ?? this.editForm.get('role')?.value,
    );
  }

  getOrganisationLabel(user: UserDto): string {
    if (user.role === 'Client') return user.filialeName ?? '—';
    if (user.role === 'Administrator' || user.role === 'Manager') return 'Poulina Group Holding';
    return user.laboratoryName ?? '—';
  }
}
