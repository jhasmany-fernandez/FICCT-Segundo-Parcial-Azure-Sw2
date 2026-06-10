import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map, startWith } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  private readonly router = inject(Router);

  readonly navigation = [
    { label: 'Inicio', path: '/' },
    { label: 'Servicios', path: '/servicios' },
    { label: 'Cobertura', path: '/planes' },
    { label: 'Mapa', path: '/mapa' },
    { label: 'Contacto', path: '/contacto' },
  ];

  private isInternalPanelRoute(url: string): boolean {
    return (
      url.startsWith('/login') ||
      url.startsWith('/forgot-password') ||
      url.startsWith('/dashboard') ||
      url.startsWith('/recepciones') ||
      url.startsWith('/fichas-recepcion')
    );
  }

  readonly isAuthRoute$ = this.router.events.pipe(
    filter((event): event is NavigationEnd => event instanceof NavigationEnd),
    map((event) => this.isInternalPanelRoute(event.urlAfterRedirects)),
    startWith(this.isInternalPanelRoute(this.router.url)),
  );
}
