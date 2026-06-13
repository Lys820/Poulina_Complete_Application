import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  FormGroup,
  Validators,
  ReactiveFormsModule,
  AbstractControl,
  FormsModule,
} from '@angular/forms';
import { UserService } from '../../core/services/user.service';
import { AuthService } from '../../core/services/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule],
  templateUrl: './profile.component.html',
  styleUrls: ['./profile.component.scss'],
})
export class ProfileComponent implements OnInit {
  form!: FormGroup;
  isLoading = signal(true);
  isSaving = signal(false);
  successMsg = signal('');
  errorMsg = signal('');
  showCurrent = signal(false);
  showNew = signal(false);
  showConfirm = signal(false);
  changePassword = signal(false);
  showDeleteModal = signal(false);
  deletePassword = signal('');

  readonly brands = ['DICK', 'SNA', 'GIPA', 'MEDOIL'];

  constructor(
    private fb: FormBuilder,
    private userService: UserService,
    public authService: AuthService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.buildForm();
    this.loadProfile();
  }

  buildForm(): void {
    this.form = this.fb.group(
      {
        firstName: ['', [Validators.required, Validators.minLength(2)]],
        lastName: ['', [Validators.required, Validators.minLength(2)]],
        email: [{ value: '', disabled: true }],
        phoneNumber: ['', [Validators.pattern(/^(\+216 ?)?(\d{8}|\d{2} \d{3} \d{3})$/)]],
        filialeName: [''],
        role: [{ value: '', disabled: true }],
        currentPassword: [''],
        newPassword: ['', [Validators.minLength(8), this.passwordStrengthValidator]],
        confirmPassword: [''],
      },
      { validators: this.passwordMatchValidator },
    );
  }

  loadProfile(): void {
    this.userService.getMyProfile().subscribe({
      next: (data) => {
        this.form.patchValue({
          firstName: data.firstName,
          lastName: data.lastName,
          email: data.email,
          phoneNumber: data.phoneNumber,
          filialeName: data.filialeName,
          role: data.role,
        });
        this.isLoading.set(false);
      },
      error: () => this.isLoading.set(false),
    });
  }

  isClientRole(): boolean {
    return this.authService.hasRole('Client');
  }

  passwordStrengthValidator(control: AbstractControl) {
    const v = control.value as string;
    if (!v) return null;
    const ok =
      /[A-Z]/.test(v) && /[a-z]/.test(v) && /[0-9]/.test(v) && /[!@#$%^&*(),.?":{}|<>]/.test(v);
    return ok ? null : { weakPassword: true };
  }

  passwordMatchValidator(group: AbstractControl) {
    if (!group.get('newPassword')?.value) return null;
    const nw = group.get('newPassword')?.value;
    const conf = group.get('confirmPassword')?.value;
    return nw === conf ? null : { mismatch: true };
  }

  get passwordStrength(): number {
    const v = (this.form.get('newPassword')?.value as string) ?? '';
    let s = 0;
    if (v.length >= 8) s++;
    if (/[A-Z]/.test(v)) s++;
    if (/[a-z]/.test(v)) s++;
    if (/[0-9]/.test(v)) s++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(v)) s++;
    return s;
  }

  get strengthLabel(): string {
    const s = this.passwordStrength;
    if (s <= 1) return 'Très faible';
    if (s === 2) return 'Faible';
    if (s === 3) return 'Moyen';
    if (s === 4) return 'Fort';
    return 'Très fort';
  }

  get strengthColor(): string {
    const s = this.passwordStrength;
    if (s <= 1) return '#DC2626';
    if (s <= 3) return '#F59E0B';
    if (s === 4) return '#10B981';
    return '#059669';
  }

  hasError(field: string, error: string): boolean {
    const ctrl = this.form.get(field);
    return !!(ctrl?.touched && ctrl?.errors?.[error]);
  }

  save(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid) {
      return;
    }

    const phone = this.form.get('phoneNumber')?.value;
    const phoneRegex = /^(\+216 ?)?(\d{8}|\d{2} \d{3} \d{3})$/;
    if (phone && !phoneRegex.test(phone)) {
      this.errorMsg.set('Format de téléphone invalide.');
      return;
    }
    this.isSaving.set(true);
    this.successMsg.set('');
    this.errorMsg.set('');

    const dto: any = {
      firstName: this.form.get('firstName')!.value,
      lastName: this.form.get('lastName')!.value,
      phoneNumber: this.form.get('phoneNumber')!.value,
      filialeName: this.form.get('filialeName')!.value,
    };

    if (this.changePassword() && this.form.get('newPassword')!.value) {
      dto.currentPassword = this.form.get('currentPassword')!.value;
      dto.newPassword = this.form.get('newPassword')!.value;
    }

    this.userService.updateMyProfile(dto).subscribe({
      next: () => {
        this.isSaving.set(false);
        this.successMsg.set('Profil mis à jour avec succès !');
        this.authService.updateUserInfo(dto.firstName, dto.lastName);
        this.changePassword.set(false);
        this.form.get('currentPassword')!.setValue('');
        this.form.get('newPassword')!.setValue('');
        this.form.get('confirmPassword')!.setValue('');
        setTimeout(() => this.successMsg.set(''), 4000);
      },
      error: (err) => {
        this.isSaving.set(false);
        this.errorMsg.set(err.error?.message ?? 'Erreur lors de la mise à jour.');
      },
    });
  }

  deleteAccount(): void {
    if (!this.deletePassword()) {
      this.errorMsg.set('Veuillez entrer votre mot de passe.');
      return;
    }

    this.userService.deleteMyAccount(this.deletePassword()).subscribe({
      next: () => {
        this.authService.logout();
        this.router.navigate(['/auth/login']);
      },
      error: (err) => {
        this.errorMsg.set(err.error?.message ?? 'Erreur lors de la suppression.');
      },
    });
  }
}
