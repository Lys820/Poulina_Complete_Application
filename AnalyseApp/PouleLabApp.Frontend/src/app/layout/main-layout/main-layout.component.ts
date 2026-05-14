import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { HeaderComponent } from '../header/header.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [RouterOutlet, SidebarComponent, HeaderComponent],
  template: `
    <app-sidebar />
    <div class="main-content">
      <app-header />
      <div class="page-content">
        <router-outlet />
      </div>
    </div>
  `,
})
export class MainLayoutComponent {}
