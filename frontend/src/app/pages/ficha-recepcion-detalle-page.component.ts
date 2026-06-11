import { CommonModule, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink, RouterLinkActive } from '@angular/router';

import { AppRole, AppSession, clearStoredSession, getStoredSession } from '../session';
import { FichaRecepcionDetail, FichasRecepcionService } from '../services/fichas-recepcion.service';

@Component({
  selector: 'app-ficha-recepcion-detalle-page',
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
            <a class="dashboard-menu-link" routerLink="/fichas-recepcion" routerLinkActive="is-active">
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
              <strong>Detalle de ficha</strong>
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
              <h1>Detalle de ficha</h1>
              <p class="subtitle">Revisa la información registrada con el mismo formato visual del resto del panel.</p>
            </div>

            <div class="header-actions">
              <a class="button ghost" routerLink="/dashboard">Volver al dashboard</a>
              <a class="button ghost" routerLink="/fichas-recepcion">Volver al listado</a>
            </div>
          </section>

          <section class="recepciones-card" *ngIf="accessDenied">
            <p class="error">Solo admin, secretaria y mecanico pueden ver el detalle de fichas.</p>
          </section>

          <section class="recepciones-card" *ngIf="!accessDenied && isLoading">
            <p class="loading">Cargando detalle...</p>
          </section>

          <section class="recepciones-card" *ngIf="!accessDenied && !isLoading && errorMessage">
            <p class="error">{{ errorMessage }}</p>
          </section>

          <section class="recepciones-card" *ngIf="!accessDenied && !isLoading && detail">
            <div class="detail-grid">
              <article class="detail-panel">
                <h2>Resumen</h2>
                <ul class="detail-list">
                  <li><strong>Codigo:</strong> {{ detail.codigo_ficha }}</li>
                  <li><strong>Estado:</strong> <span class="status-pill">{{ detail.estado }}</span></li>
                  <li><strong>Vehiculo:</strong> {{ detail.vehiculo }}</li>
                  <li><strong>Placa:</strong> {{ detail.placa || '-' }}</li>
                  <li><strong>Problema reportado:</strong> {{ detail.problema_reportado }}</li>
                  <li><strong>Fecha de ingreso:</strong> {{ detail.fecha_ingreso | date:'short' }}</li>
                </ul>
              </article>

              <article class="detail-panel">
                <h2>Datos complementarios</h2>
                <ul class="detail-list">
                  <li><strong>Cliente ID:</strong> {{ detail.cliente_id ?? '-' }}</li>
                  <li><strong>Emergencia ID:</strong> {{ detail.emergencia_id ?? '-' }}</li>
                  <li><strong>Recibido por:</strong> {{ detail.recibido_por_id ?? '-' }}</li>
                  <li><strong>Marca:</strong> {{ detail.marca || '-' }}</li>
                  <li><strong>Modelo:</strong> {{ detail.modelo || '-' }}</li>
                  <li><strong>Ano:</strong> {{ detail.anio ?? '-' }}</li>
                  <li><strong>Mecanico asignado:</strong> {{ detail.assigned_mechanic_name || detail.assigned_mechanic_id || 'Sin asignar' }}</li>
                  <li><strong>Accesorios recibidos:</strong> {{ detail.accesorios_recibidos || 'Sin registro' }}</li>
                  <li><strong>Observaciones:</strong> {{ detail.observaciones || 'Sin observaciones' }}</li>
                </ul>
              </article>
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
    .subtitle { margin: .5rem 0 0; max-width: 46rem; color: #4b617d; }
    .header-actions { display: flex; gap: .75rem; flex-wrap: wrap; }
    .recepciones-card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; margin-bottom: 1.25rem; }
    .detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; }
    .detail-panel { border: 1px solid #e3ebf4; border-radius: 1rem; padding: 1rem; background: #fbfdff; }
    .detail-panel h2 { margin: 0 0 1rem; font-size: 1rem; color: #15304f; }
    .detail-list { list-style: none; padding: 0; margin: 0; display: grid; gap: .7rem; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.ghost { background: #edf3fa; color: #143761; }
    .status-pill { display: inline-flex; padding: .35rem .7rem; background: #eef5ff; color: #143761; border-radius: 999px; font-size: .85rem; font-weight: 700; }
    .loading { margin: 0; }
    .error { color: #b03b2d; }
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
      .recepciones-header { flex-direction: column; align-items: stretch; }
    }
  `],
})
export class FichaRecepcionDetallePageComponent implements OnInit {
  private readonly service = inject(FichasRecepcionService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly session: AppSession | null = getStoredSession();

  detail: FichaRecepcionDetail | null = null;
  isLoading = false;
  errorMessage = '';

  get role(): AppRole | null {
    return this.session?.role ?? null;
  }

  get accessDenied(): boolean {
    return this.role !== 'admin' && this.role !== 'secretaria' && this.role !== 'mecanico';
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

    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) {
      this.errorMessage = 'No se encontro la ficha solicitada.';
      return;
    }

    this.isLoading = true;
    this.service.obtener(id).subscribe({
      next: (detail) => {
        this.detail = detail;
        this.isLoading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo cargar el detalle.';
      },
    });
  }
}
