import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';

export const routes: Routes = [
  // Redirection par défaut
  { path: '', redirectTo: '/auth/login', pathMatch: 'full' },

  // Auth — pas de guard
  {
    path: 'auth',
    loadChildren: () => import('./pages/auth/auth.routes').then((m) => m.AUTH_ROUTES),
  },

  // ← Register — avant le wildcard
  {
    path: 'register',
    loadComponent: () =>
      import('./pages/auth/register/register.component').then((m) => m.RegisterComponent),
  },

  // App principale — protégée par authGuard
  {
    path: 'app',
    canActivate: [authGuard],
    loadChildren: () =>
      import('./layout/main-layout/main-layout.routes').then((m) => m.LAYOUT_ROUTES),
  },

  // Page forbidden
  {
    path: 'forbidden',
    loadComponent: () =>
      import('./pages/forbidden/forbidden.component').then((m) => m.ForbiddenComponent),
  },

  // Wildcard — toujours en dernier
  { path: '**', redirectTo: '/auth/login' },
];
