import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

// Intercepte les erreurs HTTP et redirige si nécessaire
export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const authService = inject(AuthService);

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        // Token expiré — déconnecter et rediriger
        authService.logout();
      }
      if (error.status === 403) {
        // Accès refusé — rediriger vers une page d'erreur
        router.navigate(['/forbidden']);
      }
      return throwError(() => error);
    }),
  );
};
