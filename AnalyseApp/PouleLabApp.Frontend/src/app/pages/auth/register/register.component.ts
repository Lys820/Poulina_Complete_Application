import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder,
  FormGroup,
  Validators,
  ReactiveFormsModule,
  AbstractControl,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrls: ['./register.component.scss'],
})
export class RegisterComponent {
  form: FormGroup;
  isLoading = signal(false);
  errorMessage = signal('');
  showPassword = signal(false);
  showConfirm = signal(false);

  readonly roles = [
    { value: 'Client', label: 'Client' },
    { value: 'Receptionist', label: 'Réceptionniste' },
    { value: 'Analyst', label: 'Laborantin' },
    { value: 'LabChief', label: 'Chef de laboratoire' },
    { value: 'Manager', label: 'Manager' },
    { value: 'Administrator', label: 'Administrateur' },
  ];

  readonly brands = ['DICK', 'SNA', 'GIPA', 'MEDOIL'];

  constructor(
    private fb: FormBuilder,
    private router: Router,
    private http: HttpClient,
  ) {
    this.form = this.fb.group(
      {
        firstName: ['', [Validators.required, Validators.minLength(2)]],
        lastName: ['', [Validators.required, Validators.minLength(2)]],
        email: ['', [Validators.required, Validators.email]],
        phoneNumber: ['', [Validators.pattern(/^[+]?[\d\s\-().]{8,15}$/)]],
        filialeName: [''],
        role: ['Client', Validators.required],
        password: [
          '',
          [Validators.required, Validators.minLength(8), this.passwordStrengthValidator],
        ],
        confirmPassword: ['', Validators.required],
      },
      { validators: this.passwordMatchValidator },
    );
  }

  // Validateur — mot de passe fort
  passwordStrengthValidator(control: AbstractControl) {
    const v = control.value as string;
    if (!v) return null;
    const hasUpper = /[A-Z]/.test(v);
    const hasLower = /[a-z]/.test(v);
    const hasNumber = /[0-9]/.test(v);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(v);
    if (!hasUpper || !hasLower || !hasNumber || !hasSpecial) return { weakPassword: true };
    return null;
  }

  // Validateur — confirmation mot de passe
  passwordMatchValidator(group: AbstractControl) {
    const pass = group.get('password')?.value;
    const confirm = group.get('confirmPassword')?.value;
    return pass === confirm ? null : { mismatch: true };
  }

  // Indicateur de force du mot de passe
  get passwordStrength(): number {
    const v = (this.form.get('password')?.value as string) ?? '';
    let score = 0;
    if (v.length >= 8) score++;
    if (/[A-Z]/.test(v)) score++;
    if (/[a-z]/.test(v)) score++;
    if (/[0-9]/.test(v)) score++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(v)) score++;
    return score;
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
    if (s === 2) return '#F59E0B';
    if (s === 3) return '#F59E0B';
    if (s === 4) return '#10B981';
    return '#059669';
  }

  isClientRole(): boolean {
    return this.form.get('role')?.value === 'Client';
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set('');

    const { confirmPassword, ...dto } = this.form.value;

    this.http.post(`${environment.apiUrl}/auth/register`, dto).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.router.navigate(['/login'], {
          queryParams: { registered: 'true' },
        });
      },
      error: (err) => {
        this.isLoading.set(false);
        this.errorMessage.set(err.error?.message ?? 'Erreur lors de la création du compte.');
      },
    });
  }

  hasError(field: string, error: string): boolean {
    const ctrl = this.form.get(field);
    return !!(ctrl?.touched && ctrl?.errors?.[error]);
  }
}
