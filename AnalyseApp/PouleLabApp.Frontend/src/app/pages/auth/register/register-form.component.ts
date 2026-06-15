import { Component, Output, EventEmitter, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormBuilder, FormGroup, Validators,
  ReactiveFormsModule, AbstractControl,
} from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-register-form',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './register-form.component.html',
  styleUrls: ['./register.component.scss'],
})
export class RegisterFormComponent {
  @Output() onCreated = new EventEmitter<void>();
  form: FormGroup;
  isLoading      = signal(false);
  errorMessage   = signal('');
  showPassword   = signal(false);
  showConfirm    = signal(false);
  laboratories   = signal<any[]>([]);

  readonly staffRoles = ['Receptionist', 'Analyst', 'LabChief'];
  readonly roles = [
    { value: 'Client',        label: 'Client' },
    { value: 'Receptionist',  label: 'Réceptionniste' },
    { value: 'Analyst',       label: 'Laborantin' },
    { value: 'LabChief',      label: 'Chef de laboratoire' },
    { value: 'Manager',       label: 'Manager' },
    { value: 'Administrator', label: 'Administrateur' },
  ];
  readonly brands = ['DICK', 'SNA', 'GIPA', 'MEDOIL'];

  constructor(private fb: FormBuilder, private http: HttpClient) {
    this.form = this.fb.group(
      {
        firstName:       ['', [Validators.required, Validators.minLength(2)]],
        lastName:        ['', [Validators.required, Validators.minLength(2)]],
        email:           ['', [Validators.required, Validators.email]],
        phoneNumber:     ['', [Validators.pattern(/^(\+216 ?)?(\d{8}|\d{2} \d{3} \d{3})$/)]],
        filialeName:     [''],
        role:            ['Client', Validators.required],
        laboratoryId:    [null],
        password:        ['', [Validators.required, Validators.minLength(8), this.passwordStrengthValidator]],
        confirmPassword: ['', Validators.required],
      },
      { validators: this.passwordMatchValidator },
    );

    this.http.get<any[]>(`${environment.apiUrl}/laboratories`).subscribe({
      next: (labs: any[]) => this.laboratories.set(labs),
      error: () => {}
    });

    this.form.get('filialeName')?.setValidators(Validators.required);
    this.form.get('filialeName')?.updateValueAndValidity();

    this.form.get('role')?.valueChanges.subscribe((role: string) => {
      const labCtrl     = this.form.get('laboratoryId');
      const filialeCtrl = this.form.get('filialeName');
      if (this.staffRoles.includes(role)) {
        labCtrl?.setValidators(Validators.required);
        filialeCtrl?.clearValidators();
        filialeCtrl?.setValue('');
      } else if (role === 'Client') {
        filialeCtrl?.setValidators(Validators.required);
        labCtrl?.clearValidators();
        labCtrl?.setValue(null);
      } else {
        filialeCtrl?.clearValidators();
        labCtrl?.clearValidators();
        labCtrl?.setValue(null);
        filialeCtrl?.setValue('');
      }
      labCtrl?.updateValueAndValidity();
      filialeCtrl?.updateValueAndValidity();
    });
  }

  passwordStrengthValidator(control: AbstractControl) {
    const v = control.value as string;
    if (!v) return null;
    const ok = /[A-Z]/.test(v) && /[a-z]/.test(v) && /[0-9]/.test(v) && /[!@#$%^&*(),.?":{}|<>]/.test(v);
    return ok ? null : { weakPassword: true };
  }

  passwordMatchValidator(group: AbstractControl) {
    const pass    = group.get('password')?.value;
    const confirm = group.get('confirmPassword')?.value;
    return pass === confirm ? null : { mismatch: true };
  }

  get passwordStrength(): number {
    const v = (this.form.get('password')?.value as string) ?? '';
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

  isClientRole(): boolean {
    return this.form.get('role')?.value === 'Client';
  }

  isStaffRole(): boolean {
    return this.staffRoles.includes(this.form.get('role')?.value);
  }

  hasError(field: string, error: string): boolean {
    const ctrl = this.form.get(field);
    return !!(ctrl?.touched && ctrl?.errors?.[error]);
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
        this.onCreated.emit();
      },
      error: (err: any) => {
        this.isLoading.set(false);
        this.errorMessage.set(err.error?.message ?? 'Erreur.');
      },
    });
  }
}
