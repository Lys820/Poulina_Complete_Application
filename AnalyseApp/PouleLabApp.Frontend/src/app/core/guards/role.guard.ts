import { inject } from '@angular/core';
import { CanActivateFn, Router, ActivatedRouteSnapshot } from '@angular/router';
import { AuthService } from '../services/auth.service';

// Bloque l'accès si l'utilisateur n'a pas le bon rôle
export const roleGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  const allowedRoles: string[] = route.data['roles'] ?? [];

  if (authService.hasAnyRole(allowedRoles)) return true;

  router.navigate(['/forbidden']);
  return false;
};
