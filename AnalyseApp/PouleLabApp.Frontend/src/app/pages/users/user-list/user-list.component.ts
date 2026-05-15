import { Component, OnInit, signal } from '@angular/core';
import { CommonModule, NgClass } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup } from '@angular/forms';
import { UserService } from '../../../core/services/user.service';
import { AuthService } from '../../../core/services/auth.service';
import { UserDto } from '../../../core/models/user.model';

@Component({
  selector: 'app-user-list',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule, NgClass],
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
  ) {}

  ngOnInit(): void {
    this.loadUsers();
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
  openEdit(user: UserDto): void {
    this.editingUser.set(user);
    this.editForm = this.fb.group({
      firstName: [user.firstName],
      lastName: [user.lastName],
      filialeName: [user.filialeName],
      isActive: [user.isActive],
      role: [user.role],
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

  // Désactiver un compte
  deactivate(user: UserDto): void {
    if (!confirm(`Désactiver le compte de ${user.firstName} ${user.lastName} ?`)) return;

    this.userService.deactivate(user.id).subscribe({
      next: () => {
        this.loadUsers();
        this.showSuccess('Compte désactivé.');
      },
      error: (err) => this.showError(err.error?.message),
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
}
