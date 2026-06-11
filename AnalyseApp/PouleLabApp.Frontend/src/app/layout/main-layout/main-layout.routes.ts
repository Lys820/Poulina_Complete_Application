import { Routes } from '@angular/router';
import { roleGuard } from '../../core/guards/role.guard';

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
      {
        path: 'requests/:id/results',
        loadComponent: () =>
          import('../../pages/requests/request-results/request-results.component').then(
            (m) => m.RequestResultsComponent,
          ),
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import('../../pages/notifications/notifications.component').then(
            (m) => m.NotificationsComponent,
          ),
      },
      {
        path: 'users',
        loadComponent: () =>
          import('../../pages/users/user-list/user-list.component').then(
            (m) => m.UserListComponent,
          ),
      },
      {
        path: 'profile',
        loadComponent: () =>
          import('../../pages/profile/profile.component').then((m) => m.ProfileComponent),
      },
      {
        path: 'chat',
        loadComponent: () =>
          import('../../pages/chat/chat.component').then((m) => m.ChatComponent),
      },
      {
        path: 'laboratories',
        canActivate: [roleGuard],
        data: { roles: ['Administrator'] },
        loadComponent: () =>
          import('../../pages/laboratories/laboratory-list.component').then(
            (m) => m.LaboratoryListComponent,
          ),
      },
    ],
  },
];
