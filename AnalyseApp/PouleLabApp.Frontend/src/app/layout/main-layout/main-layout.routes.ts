import { Routes } from '@angular/router';

export const LAYOUT_ROUTES: Routes = [
  {
    path: '',
    loadComponent: () => import('./main-layout.component').then((m) => m.MainLayoutComponent),
    children: [
      {
        path: 'dashboard',
        loadComponent: () =>
          import('../../pages/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'requests',
        loadComponent: () =>
          import('../../pages/requests/request-list/request-list.component').then(
            (m) => m.RequestListComponent,
          ),
      },
      {
        path: 'requests/new',
        loadComponent: () =>
          import('../../pages/requests/request-form/request-form.component').then(
            (m) => m.RequestFormComponent,
          ),
      },
      {
        path: 'requests/:id',
        loadComponent: () =>
          import('../../pages/requests/request-detail/request-detail.component').then(
            (m) => m.RequestDetailComponent,
          ),
      },
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'requests/:id/edit',
        loadComponent: () =>
          import('../../pages/requests/request-form/request-form.component').then(
            (m) => m.RequestFormComponent,
          ),
      },
    ],
  },
];
