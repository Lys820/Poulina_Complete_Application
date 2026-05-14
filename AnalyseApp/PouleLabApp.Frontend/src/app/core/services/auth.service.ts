import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { AuthResponse, LoginDto } from '../models/auth.model';
import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly TOKEN_KEY = 'pgh_token';
  private readonly USER_KEY = 'pgh_user';

  // Signal pour réactivité dans les composants
  currentUser = signal<AuthResponse | null>(this.getUserFromStorage());

  constructor(
    private http: HttpClient,
    private router: Router,
  ) {}

  // Connexion — stocke le token et les infos utilisateur
  login(dto: LoginDto): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>(`${environment.apiUrl}/auth/login`, dto)
      .pipe(tap((response) => this.storeSession(response)));
  }

  // Déconnexion — nettoie le stockage et redirige
  logout(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
    this.currentUser.set(null);
    this.router.navigate(['/auth/login']);
  }

  // Récupère le token JWT stocké
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  // Vérifie si l'utilisateur est authentifié
  isAuthenticated(): boolean {
    const token = this.getToken();
    if (!token) return false;

    // Vérifier que le token n'est pas expiré
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  }

  // Récupère le rôle de l'utilisateur connecté
  getRole(): string {
    return this.currentUser()?.role ?? '';
  }

  // Vérifie si l'utilisateur a un rôle spécifique
  hasRole(role: string): boolean {
    return this.getRole() === role;
  }

  // Vérifie si l'utilisateur a l'un des rôles donnés
  hasAnyRole(roles: string[]): boolean {
    return roles.includes(this.getRole());
  }

  private storeSession(response: AuthResponse): void {
    localStorage.setItem(this.TOKEN_KEY, response.token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(response));
    this.currentUser.set(response);
  }

  private getUserFromStorage(): AuthResponse | null {
    const user = localStorage.getItem(this.USER_KEY);
    return user ? JSON.parse(user) : null;
  }
}
