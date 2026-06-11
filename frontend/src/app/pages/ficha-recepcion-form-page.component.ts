import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { catchError, forkJoin, of } from 'rxjs';

import { AppRole, getStoredSession } from '../session';
import {
  FichaRecepcionClientOption,
  FichaRecepcionEmergencyOption,
  FichaRecepcionPayload,
  FichasRecepcionService,
} from '../services/fichas-recepcion.service';

@Component({
  selector: 'app-ficha-recepcion-form-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <main class="shell">
      <section class="header">
        <div>
          <p class="eyebrow">Ficha de Recepcion Vehicular</p>
          <h1>Nueva ficha</h1>
          <p class="subtitle">Registro limpio para recepcion vehicular con asociacion opcional a una emergencia.</p>
        </div>
        <a class="button ghost" routerLink="/fichas-recepcion">Volver al listado</a>
      </section>

      <section class="card" *ngIf="accessDenied">
        <p class="error">{{ accessDeniedMessage }}</p>
      </section>

      <section class="card" *ngIf="!accessDenied">
        <div class="context-head">
          <div>
            <h2>Contexto de recepcion</h2>
            <p>La ficha toma cliente y emergencia desde una seleccion controlada. Ya no se ingresan IDs internos manualmente.</p>
          </div>
        </div>

        <div class="grid context-grid">
          <label class="field field-wide">
            <span>Emergencia asociada</span>
            <select
              [ngModel]="selectedEmergencyId"
              (ngModelChange)="onEmergencyChange($event)"
              name="selected_emergency_id"
              [disabled]="isLoadingContext || isLoading"
            >
              <option [ngValue]="null">Recepcion manual sin emergencia</option>
              <option *ngFor="let emergency of availableEmergencies" [ngValue]="emergency.id">
                #{{ emergency.id }} · {{ emergency.vehicle_name }} · {{ emergency.vehicle_plate }} · {{ emergency.problem_type }}
              </option>
            </select>
          </label>

          <label class="field field-wide" *ngIf="!selectedEmergencyId">
            <span>Cliente asociado</span>
            <select
              [ngModel]="selectedClientId"
              (ngModelChange)="onClientChange($event)"
              name="selected_client_id"
              [disabled]="isLoadingContext || isLoading"
            >
              <option [ngValue]="null">Selecciona un cliente para la recepcion manual</option>
              <option *ngFor="let client of availableClients" [ngValue]="client.id">
                {{ client.full_name }} · CI {{ client.identity_card }} · {{ client.email }}
              </option>
            </select>
          </label>
        </div>

        <p *ngIf="isLoadingContext">Cargando clientes y emergencias...</p>
        <p class="error" *ngIf="contextErrorMessage">{{ contextErrorMessage }}</p>

        <div class="auto-grid" *ngIf="selectedClient || selectedEmergency">
          <article class="auto-card" *ngIf="selectedClient">
            <p class="auto-label">Cliente resuelto</p>
            <strong>{{ selectedClient.full_name }}</strong>
            <span>CI {{ selectedClient.identity_card }}</span>
            <span>{{ selectedClient.phone }}</span>
            <span>{{ selectedClient.email }}</span>
          </article>

          <article class="auto-card" *ngIf="selectedEmergency">
            <p class="auto-label">Emergencia asociada</p>
            <strong>#{{ selectedEmergency.id }} · {{ selectedEmergency.problem_type }}</strong>
            <span>{{ selectedEmergency.vehicle_name }}</span>
            <span>{{ selectedEmergency.vehicle_plate }}</span>
            <span>{{ selectedEmergency.emergency_status || 'Sin estado' }}</span>
          </article>
        </div>
      </section>

      <form class="card form-grid" *ngIf="!accessDenied" (ngSubmit)="submit()">
        <div class="grid">
          <label class="field">
            <span>Vehiculo</span>
            <input [(ngModel)]="form.vehiculo" name="vehiculo" [readonly]="vehicleLockedByEmergency" />
          </label>

          <label class="field">
            <span>Placa</span>
            <input [(ngModel)]="form.placa" name="placa" [readonly]="vehicleLockedByEmergency" />
          </label>

          <label class="field">
            <span>Marca</span>
            <input [(ngModel)]="form.marca" name="marca" />
          </label>

          <label class="field">
            <span>Modelo</span>
            <input [(ngModel)]="form.modelo" name="modelo" />
          </label>

          <label class="field">
            <span>Ano</span>
            <input [(ngModel)]="form.anio" name="anio" type="number" min="1900" max="2100" />
          </label>

          <label class="field field-wide">
            <span>Problema reportado</span>
            <textarea [(ngModel)]="form.problema_reportado" name="problema_reportado" required [readonly]="problemLockedByEmergency"></textarea>
          </label>

          <label class="field field-wide">
            <span>Accesorios recibidos</span>
            <textarea [(ngModel)]="form.accesorios_recibidos" name="accesorios_recibidos"></textarea>
          </label>

          <label class="field field-wide">
            <span>Observaciones</span>
            <textarea [(ngModel)]="form.observaciones" name="observaciones"></textarea>
          </label>
        </div>

        <p class="field-hint" *ngIf="selectedEmergency">El cliente, la emergencia y los datos base del vehiculo se vincularan automaticamente desde la emergencia seleccionada.</p>
        <p class="field-hint" *ngIf="!selectedEmergency">La ficha se registrara como recepcion manual usando el cliente seleccionado arriba.</p>
        <p *ngIf="isLoading">Guardando ficha...</p>
        <p class="error" *ngIf="errorMessage">{{ errorMessage }}</p>

        <div class="actions">
          <button class="button primary" type="submit" [disabled]="isLoading || isLoadingContext || !canSubmit">Crear ficha</button>
        </div>
      </form>
    </main>
  `,
  styles: [`
    .shell { padding: 2rem; background: #f4f7fb; min-height: 100vh; color: #15304f; }
    .header, .actions { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; }
    .header { margin-bottom: 1.5rem; }
    .eyebrow { margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .12em; font-size: .78rem; color: #85711b; font-weight: 700; }
    .subtitle { margin: .5rem 0 0; color: #50667f; }
    .card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; }
    .context-head h2 { margin: 0 0 .25rem; }
    .context-head p { margin: 0; color: #50667f; }
    .form-grid { display: grid; gap: 1rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; }
    .context-grid { margin-top: 1rem; }
    .field { display: flex; flex-direction: column; gap: .45rem; }
    .field span { font-weight: 600; color: #284c73; }
    .field input, .field textarea, .field select { border: 1px solid #c8d5e6; border-radius: .85rem; padding: .8rem .95rem; font: inherit; background: #fff; }
    .field input[readonly], .field textarea[readonly] { background: #f5f8fc; color: #46607d; }
    .field textarea { min-height: 110px; resize: vertical; }
    .field-wide { grid-column: 1 / -1; }
    .field-hint { margin: 0; color: #50667f; font-size: .95rem; }
    .auto-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-top: 1rem; }
    .auto-card { display: grid; gap: .3rem; border: 1px solid #d6e0ee; background: linear-gradient(180deg, #f9fbff 0%, #f0f5fb 100%); border-radius: 1rem; padding: 1rem; color: #27476b; }
    .auto-label { margin: 0; text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; color: #85711b; font-weight: 700; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.primary { background: #143761; color: #fff; }
    .button.ghost { background: #edf3fa; color: #143761; }
    .error { color: #b03b2d; }
    @media (max-width: 768px) { .shell { padding: 1rem; } .header, .actions { flex-direction: column; align-items: stretch; } }
  `],
})
export class FichaRecepcionFormPageComponent implements OnInit {
  private static readonly ACTIVE_FICHA_STATUSES = new Set(['registrada', 'en_diagnostico', 'en_trabajo', 'finalizada']);
  private readonly service = inject(FichasRecepcionService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly session = getStoredSession();

  isLoading = false;
  isLoadingContext = false;
  errorMessage = '';
  contextErrorMessage = '';
  availableClients: FichaRecepcionClientOption[] = [];
  availableEmergencies: FichaRecepcionEmergencyOption[] = [];
  selectedClientId: number | null = null;
  selectedEmergencyId: number | null = null;

  form: FichaRecepcionPayload = {
    cliente_id: null,
    emergencia_id: null,
    vehiculo: '',
    placa: '',
    marca: '',
    modelo: '',
    anio: null,
    problema_reportado: '',
    accesorios_recibidos: '',
    observaciones: '',
    assigned_mechanic_id: null,
  };

  ngOnInit(): void {
    if (this.accessDenied) {
      return;
    }

    this.loadContext();
  }

  get role(): AppRole | null {
    return this.session?.role ?? null;
  }

  get accessDenied(): boolean {
    return this.role !== 'admin' && this.role !== 'secretaria';
  }

  get accessDeniedMessage(): string {
    return 'Solo admin y secretaria pueden crear fichas.';
  }

  get selectedClient(): FichaRecepcionClientOption | null {
    return this.availableClients.find((client) => client.id === this.selectedClientId) ?? null;
  }

  get selectedEmergency(): FichaRecepcionEmergencyOption | null {
    return this.availableEmergencies.find((emergency) => emergency.id === this.selectedEmergencyId) ?? null;
  }

  get vehicleLockedByEmergency(): boolean {
    return !!this.selectedEmergency;
  }

  get problemLockedByEmergency(): boolean {
    return !!this.selectedEmergency && !!this.form.problema_reportado?.trim();
  }

  get canSubmit(): boolean {
    return !!this.selectedEmergencyId || !!this.selectedClientId;
  }

  onEmergencyChange(value: number | null): void {
    this.selectedEmergencyId = value ? Number(value) : null;
    this.syncContextIntoForm();
  }

  onClientChange(value: number | null): void {
    this.selectedClientId = value ? Number(value) : null;
    this.form.cliente_id = this.selectedClientId;
  }

  submit(): void {
    if (this.accessDenied || this.isLoading) {
      return;
    }

    if (!this.canSubmit) {
      this.errorMessage = 'Selecciona un cliente o una emergencia antes de crear la ficha.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';
    this.service.crear({
      ...this.form,
      cliente_id: this.selectedEmergency ? null : this.selectedClientId,
      emergencia_id: this.selectedEmergencyId,
      assigned_mechanic_id: null,
      vehiculo: this.form.vehiculo?.trim() || null,
      placa: this.form.placa?.trim() || null,
      marca: this.form.marca?.trim() || null,
      modelo: this.form.modelo?.trim() || null,
      problema_reportado: this.form.problema_reportado.trim(),
      accesorios_recibidos: this.form.accesorios_recibidos?.trim() || null,
      observaciones: this.form.observaciones?.trim() || null,
    }).subscribe({
      next: async (detail) => {
        this.isLoading = false;
        await this.router.navigate(['/fichas-recepcion', detail.id]);
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo crear la ficha.';
      },
    });
  }

  private loadContext(): void {
    this.isLoadingContext = true;
    this.contextErrorMessage = '';

    forkJoin({
      clients: this.service.listarClientes(),
      fichas: this.service.listar(),
      emergencies: this.service.listarEmergencias().pipe(
        catchError(() => {
          this.contextErrorMessage = 'No se pudieron cargar las emergencias. Puedes continuar creando una recepcion manual.';
          return of([]);
        }),
      ),
    }).subscribe({
      next: ({ clients, fichas, emergencies }) => {
        this.availableClients = clients.filter((client) => client.role === 'client' && client.status === 'active');
        const blockedEmergencyIds = new Set(
          fichas
            .filter((item) => item.emergencia_id && FichaRecepcionFormPageComponent.ACTIVE_FICHA_STATUSES.has(item.estado))
            .map((item) => item.emergencia_id as number),
        );
        this.availableEmergencies = emergencies.filter(
          (emergency) => !!emergency.client_id && !blockedEmergencyIds.has(emergency.id),
        );

        if (!this.availableEmergencies.length) {
          this.contextErrorMessage = emergencies.length
            ? 'No hay emergencias listas para recepcionar. Solo se muestran emergencias con cliente asociado y sin ficha activa.'
            : 'No hay emergencias disponibles para asociar en este momento. Puedes continuar con una recepcion manual.';
        }

        const emergencyIdParam = Number(this.route.snapshot.queryParamMap.get('emergencyId') || this.route.snapshot.queryParamMap.get('emergenciaId') || 0);
        const clientIdParam = Number(this.route.snapshot.queryParamMap.get('clientId') || this.route.snapshot.queryParamMap.get('clienteId') || 0);

        if (emergencyIdParam && this.availableEmergencies.some((item) => item.id === emergencyIdParam)) {
          this.selectedEmergencyId = emergencyIdParam;
        }

        if (!this.selectedEmergencyId && clientIdParam && this.availableClients.some((item) => item.id === clientIdParam)) {
          this.selectedClientId = clientIdParam;
        }

        this.syncContextIntoForm();
        this.isLoadingContext = false;
      },
      error: () => {
        this.isLoadingContext = false;
        this.contextErrorMessage = 'No se pudo cargar el contexto de clientes y emergencias.';
      },
    });
  }

  private syncContextIntoForm(): void {
    const emergency = this.selectedEmergency;

    if (emergency) {
      this.selectedClientId = emergency.client_id ?? null;
      this.form.cliente_id = null;
      this.form.emergencia_id = emergency.id;
      this.form.vehiculo = emergency.vehicle_name?.trim() || '';
      this.form.placa = emergency.vehicle_plate?.trim() || '';
      this.form.problema_reportado = emergency.problem_type?.trim() || emergency.description?.trim() || '';
      this.autofillVehicleBreakdown(this.form.vehiculo || '');
      return;
    }

    this.form.emergencia_id = null;
    this.form.cliente_id = this.selectedClientId;
  }

  private autofillVehicleBreakdown(vehicleLabel: string): void {
    const parts = vehicleLabel.trim().split(/\s+/).filter(Boolean);
    if (!parts.length) {
      return;
    }

    const maybeYear = Number(parts[parts.length - 1]);
    if (Number.isInteger(maybeYear) && maybeYear >= 1900 && maybeYear <= 2100) {
      this.form.anio = maybeYear;
      parts.pop();
    }

    this.form.marca = parts[0] ?? this.form.marca ?? '';
    this.form.modelo = parts.slice(1).join(' ') || this.form.modelo || '';
  }
}
