import { CommonModule, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AppRole, AppSession, clearStoredSession, getStoredSession } from '../session';
import { FichaRecepcionListItem, FichasRecepcionService } from '../services/fichas-recepcion.service';

@Component({
  selector: 'app-fichas-recepcion-page',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, DatePipe],
  template: `
    <main class="dashboard-page dashboard-page-standalone">
      <aside class="dashboard-sidebar">
        <a class="dashboard-brand" routerLink="/">
          <span class="dashboard-brand-mark">
            <img src="/favicon.svg" alt="Logo ACB" />
          </span>
          <span>
            <strong>Emergencias Vehiculares</strong>
            <small>Centro de operaciones</small>
          </span>
        </a>

        <nav class="dashboard-menu">
          <div class="dashboard-menu-group">
            <a class="dashboard-menu-link" routerLink="/dashboard" routerLinkActive="is-active" [routerLinkActiveOptions]="{ exact: true }">
              <span class="dashboard-menu-icon">⌂</span>
              <span>Dashboard</span>
            </a>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessReceptionModule">
            <a class="dashboard-menu-link" routerLink="/fichas-recepcion" routerLinkActive="is-active" [routerLinkActiveOptions]="{ exact: true }">
              <span class="dashboard-menu-icon">▤</span>
              <span>Fichas de Recepción</span>
            </a>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('mecanicos')">
            <a class="dashboard-menu-link" routerLink="/dashboard" [queryParams]="{ section: 'mecanicos' }">
              <span class="dashboard-menu-icon">◔</span>
              <span>Mecanicos</span>
            </a>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('clients')">
            <a class="dashboard-menu-link" routerLink="/dashboard" [queryParams]="{ section: 'clients' }">
              <span class="dashboard-menu-icon">◉</span>
              <span>Clientes</span>
            </a>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('emergencies')">
            <a class="dashboard-menu-link" routerLink="/dashboard" [queryParams]="{ section: 'emergencies' }">
              <span class="dashboard-menu-icon">⬒</span>
              <span>Emergencias</span>
              <span class="dashboard-menu-badge">24/7</span>
            </a>
          </div>

          <div class="dashboard-menu-group" *ngIf="canAccessSection('reports')">
            <a class="dashboard-menu-link" routerLink="/dashboard" [queryParams]="{ section: 'reports' }">
              <span class="dashboard-menu-icon">▥</span>
              <span>Reportes</span>
            </a>
          </div>
        </nav>

        <section class="dashboard-sidebar-card">
          <span>Turno activo</span>
          <strong>Administración general</strong>
          <p>Supervision de sucursales, coordinacion operativa y control del panel empresarial.</p>
        </section>
      </aside>

      <section class="dashboard-content standalone-content">
        <header class="dashboard-topbar dashboard-topbar-surface">
          <div class="dashboard-topbar-copy">
            <button class="dashboard-sidebar-toggle" type="button" aria-label="Menu lateral">
              ☰
            </button>
            <div class="dashboard-topbar-copy-text">
              <span class="dashboard-topbar-kicker">Panel interno</span>
              <strong>Fichas de recepción</strong>
            </div>
          </div>

          <div class="dashboard-topbar-actions">
            <div class="dashboard-user-pill">
              <span class="dashboard-user-avatar">{{ userInitials }}</span>
              <span class="dashboard-user-name">{{ userDisplayName }}</span>
            </div>
            <button class="dashboard-icon-button" type="button" aria-label="Notificaciones" (click)="openEmergencyNotifications()">🔔</button>
            <button class="dashboard-icon-button" type="button" aria-label="Cerrar sesion" (click)="logout()">⛔</button>
          </div>
        </header>

        <main class="recepciones-shell">
          <section class="recepciones-header">
            <div>
              <p class="eyebrow">Ficha de Recepcion Vehicular</p>
              <h1>Fichas de recepcion</h1>
              <p class="subtitle">Consulta y revisa las fichas registradas desde el mismo panel operativo del taller.</p>
            </div>

            <div class="header-actions">
              <a class="button ghost" routerLink="/dashboard">Volver al dashboard</a>
              <a class="button primary" routerLink="/fichas-recepcion/nueva" *ngIf="canCreate">Nueva ficha</a>
            </div>
          </section>

          <section class="recepciones-card" *ngIf="accessDenied">
            <p class="error">Solo admin, secretaria y mecanico pueden consultar fichas de recepcion.</p>
          </section>

          <section class="recepciones-card" *ngIf="!accessDenied">
            <div class="toolbar">
              <div>
                <strong>Total:</strong> {{ items.length }}
                <span class="toolbar-detail">Fichas visibles en este momento</span>
              </div>
            </div>

            <p class="loading" *ngIf="isLoading">Cargando fichas...</p>
            <p class="error" *ngIf="!isLoading && errorMessage">{{ errorMessage }}</p>
            <p class="empty" *ngIf="!isLoading && !errorMessage && !items.length">No hay fichas registradas.</p>

            <div class="table-wrap" *ngIf="!isLoading && items.length">
              <table>
                <thead>
                  <tr>
                    <th>Codigo</th>
                    <th>Emergencia</th>
                    <th>Cliente</th>
                    <th>Vehiculo</th>
                    <th>Placa</th>
                    <th>Problema</th>
                    <th>Mecanico</th>
                    <th>Ingreso</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let item of items">
                    <td>{{ item.codigo_ficha }}</td>
                    <td>{{ item.emergencia_id ?? '-' }}</td>
                    <td>{{ item.cliente_id ?? '-' }}</td>
                    <td>{{ item.vehiculo }}</td>
                    <td>{{ item.placa || '-' }}</td>
                    <td>{{ item.problema_reportado }}</td>
                    <td>{{ item.assigned_mechanic_name || item.assigned_mechanic_id || 'Sin asignar' }}</td>
                    <td>{{ item.fecha_ingreso | date:'short' }}</td>
                    <td><span class="status-pill">{{ item.estado }}</span></td>
                    <td class="actions-cell">
                      <a class="inline-link" [routerLink]="['/fichas-recepcion', item.id]">Ver detalle</a>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </main>
      </section>
    </main>
  `,
  styles: [`
    .dashboard-page { min-height: 100vh; display: grid; grid-template-columns: 280px minmax(0, 1fr); background: linear-gradient(180deg, #f5f8fc 0%, #eef3f8 100%); color: #15304f; }
    .dashboard-sidebar { background: linear-gradient(180deg, #143761 0%, #102a49 100%); color: #e9f1ff; padding: 1.5rem 1.1rem; display: flex; flex-direction: column; gap: 1.25rem; box-shadow: inset -1px 0 0 rgba(255,255,255,.08); }
    .dashboard-brand { display: flex; align-items: center; gap: .85rem; color: inherit; text-decoration: none; padding: .75rem; border-radius: 1rem; background: rgba(255,255,255,.06); }
    .dashboard-brand-mark { width: 2.75rem; height: 2.75rem; border-radius: .9rem; background: rgba(255,255,255,.12); display: inline-flex; align-items: center; justify-content: center; overflow: hidden; }
    .dashboard-brand-mark img { width: 1.75rem; height: 1.75rem; object-fit: contain; }
    .dashboard-brand strong, .dashboard-brand small { display: block; }
    .dashboard-brand small { color: rgba(233,241,255,.72); }
    .dashboard-menu { display: flex; flex-direction: column; gap: .8rem; }
    .dashboard-menu-group { display: flex; flex-direction: column; gap: .45rem; }
    .dashboard-menu-link { display: flex; align-items: center; gap: .8rem; padding: .9rem 1rem; border-radius: 1rem; color: #dce9ff; text-decoration: none; background: transparent; transition: background .2s ease, color .2s ease, transform .2s ease; }
    .dashboard-menu-link:hover { background: rgba(255,255,255,.08); transform: translateX(2px); }
    .dashboard-menu-link.is-active { background: linear-gradient(180deg, #ffd95f 0%, #f7c93d 100%); color: #17345c; box-shadow: 0 14px 28px rgba(10, 18, 34, .24); }
    .dashboard-menu-icon { width: 1.35rem; text-align: center; opacity: .95; }
    .dashboard-menu-badge { margin-left: auto; background: rgba(202, 223, 255, .18); color: #f0f6ff; padding: .22rem .6rem; border-radius: 999px; font-size: .74rem; font-weight: 700; }
    .dashboard-sidebar-card { margin-top: auto; background: rgba(255,255,255,.08); border: 1px solid rgba(255,255,255,.08); border-radius: 1rem; padding: 1rem; }
    .dashboard-sidebar-card span { display: block; font-size: .78rem; text-transform: uppercase; letter-spacing: .08em; color: rgba(233,241,255,.7); margin-bottom: .45rem; }
    .dashboard-sidebar-card strong { display: block; margin-bottom: .35rem; }
    .dashboard-sidebar-card p { margin: 0; color: rgba(233,241,255,.78); line-height: 1.45; }
    .dashboard-content { min-width: 0; }
    .standalone-content { display: flex; flex-direction: column; }
    .dashboard-topbar { padding: 1.25rem 2rem 0; }
    .dashboard-topbar-surface { margin: 1.25rem 2rem 0; padding: 2rem 1.25rem; border-radius: 2rem; background: linear-gradient(90deg, #143761 0%, #102a49 100%); box-shadow: 0 28px 50px rgba(24, 54, 102, .18); display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
    .dashboard-topbar-copy { display: flex; align-items: center; gap: 1rem; }
    .dashboard-topbar-copy-text { display: flex; flex-direction: row; align-items: baseline; gap: 1rem; flex-wrap: wrap; }
    .dashboard-sidebar-toggle { width: 3rem; height: 3rem; border-radius: 1rem; border: 1px solid rgba(255,255,255,.24); background: rgba(255,255,255,.08); color: #fff; font-size: 1.2rem; cursor: default; }
    .dashboard-topbar-kicker { text-transform: uppercase; letter-spacing: .16em; font-size: .74rem; color: rgba(255,223,142,.92); font-weight: 700; }
    .dashboard-topbar-copy strong { font-size: 2rem; color: #fff; }
    .dashboard-topbar-actions { display: flex; align-items: center; gap: .85rem; }
    .dashboard-user-pill { display: inline-flex; align-items: center; gap: .85rem; padding: .55rem .9rem; border-radius: 999px; background: rgba(255,255,255,.92); color: #143761; font-weight: 700; }
    .dashboard-user-avatar { width: 2.35rem; height: 2.35rem; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center; background: #143761; color: #fff; font-size: .95rem; font-weight: 800; }
    .dashboard-user-name { white-space: nowrap; }
    .dashboard-icon-button { width: 3rem; height: 3rem; border: none; border-radius: 999px; background: rgba(255,255,255,.92); color: #143761; font-size: 1.1rem; cursor: pointer; }
    .recepciones-shell { padding: 1.25rem 2rem 2rem; background: transparent; min-height: 100%; color: #15304f; }
    .recepciones-header { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; margin-bottom: 1.5rem; }
    .eyebrow { margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .12em; font-size: .78rem; color: #85711b; font-weight: 700; }
    h1 { margin: 0; font-size: 2rem; }
    .subtitle { margin: .5rem 0 0; color: #50667f; max-width: 48rem; }
    .header-actions { display: flex; gap: .75rem; flex-wrap: wrap; }
    .recepciones-card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; margin-bottom: 1.25rem; }
    .toolbar { display: flex; justify-content: space-between; gap: 1rem; align-items: center; margin-bottom: 1rem; }
    .toolbar-detail { margin-left: .5rem; color: #60758f; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 1080px; }
    th, td { text-align: left; padding: .9rem .85rem; border-bottom: 1px solid #e3ebf4; vertical-align: top; }
    th { text-transform: uppercase; font-size: .82rem; color: #48617f; letter-spacing: .06em; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.primary { background: #143761; color: #fff; }
    .button.ghost { background: #edf3fa; color: #143761; }
    .status-pill { display: inline-flex; padding: .35rem .7rem; background: #eef5ff; color: #143761; border-radius: 999px; font-size: .85rem; font-weight: 700; }
    .actions-cell { display: flex; flex-direction: column; gap: .35rem; }
    .inline-link { color: #143761; font-weight: 600; text-decoration: none; }
    .loading, .empty, .error { margin: 1rem 0 0; }
    .error { color: #b03b2d; }
    .empty { color: #60758f; }
    @media (max-width: 1100px) {
      .dashboard-page { grid-template-columns: 1fr; }
      .dashboard-sidebar { padding-bottom: 1rem; }
    }
    @media (max-width: 768px) {
      .dashboard-topbar { padding: 1rem 1rem 0; }
      .dashboard-topbar-surface { margin: 1rem 1rem 0; padding: 1.25rem 1rem; flex-direction: column; align-items: stretch; }
      .dashboard-topbar-copy { align-items: flex-start; }
      .dashboard-topbar-copy-text { flex-direction: column; align-items: flex-start; gap: .35rem; }
      .dashboard-topbar-copy strong { font-size: 1.5rem; }
      .dashboard-topbar-actions { justify-content: space-between; }
      .recepciones-shell { padding: 1rem; }
      .recepciones-header, .toolbar { flex-direction: column; align-items: stretch; }
    }
  `],
})
export class FichasRecepcionPageComponent implements OnInit {
  private readonly service = inject(FichasRecepcionService);
  private readonly router = inject(Router);
  readonly session: AppSession | null = getStoredSession();

  items: FichaRecepcionListItem[] = [];
  isLoading = false;
  errorMessage = '';

  get role(): AppRole | null {
    return this.session?.role ?? null;
  }

  get accessDenied(): boolean {
    return this.role !== 'admin' && this.role !== 'secretaria' && this.role !== 'mecanico';
  }

  get canCreate(): boolean {
    return this.role === 'admin' || this.role === 'secretaria';
  }

  get canAccessReceptionModule(): boolean {
    return this.role === 'admin' || this.role === 'secretaria' || this.role === 'mecanico';
  }

  canAccessSection(section: 'mecanicos' | 'clients' | 'emergencies' | 'reports'): boolean {
    if (this.role === 'admin') {
      return true;
    }

    if (this.role === 'secretaria') {
      return section === 'mecanicos' || section === 'clients' || section === 'emergencies' || section === 'reports';
    }

    return false;
  }

  get userDisplayName(): string {
    return this.session?.fullName?.trim() || 'Panel interno';
  }

  get userInitials(): string {
    const parts = this.userDisplayName.split(' ').filter(Boolean);
    return parts.slice(0, 2).map((part) => part[0]?.toUpperCase() || '').join('') || 'PI';
  }

  openEmergencyNotifications(): void {
    void this.router.navigate(['/dashboard'], { queryParams: { section: 'emergencies', filter: 'pendiente' } });
  }

  logout(): void {
    const confirmed = typeof window === 'undefined' ? true : window.confirm('¿Quieres cerrar sesión?');

    if (!confirmed) {
      return;
    }

    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('acb_session');
      window.sessionStorage.removeItem('acb_session');
    }

    clearStoredSession();
    void this.router.navigate(['/login']);
  }


  ngOnInit(): void {
    if (this.accessDenied) {
      return;
    }
    this.isLoading = true;
    this.service.listar().subscribe({
      next: (items) => {
        this.items = items;
        this.isLoading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo cargar el listado.';
      },
    });
  }
}
