import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-forbidden',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div
      class="d-flex flex-column align-items-center justify-content-center"
      style="min-height:100vh"
    >
      <h1 style="font-size:80px;color:#7366FF">403</h1>
      <h4>Accès refusé</h4>
      <p class="text-muted">Vous n'avez pas les droits pour accéder à cette page.</p>
      <a routerLink="/app/dashboard" class="btn btn-primary mt-3"> Retour au tableau de bord </a>
    </div>
  `,
})
export class ForbiddenComponent {}
