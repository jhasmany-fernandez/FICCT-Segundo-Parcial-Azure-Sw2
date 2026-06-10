import { CommonModule, DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { AppRole, getStoredSession } from '../session';
import { RecepcionDetalle, RecepcionStatus, RecepcionesService } from '../services/recepciones.service';

@Component({
  selector: 'app-recepcion-detalle-page',
  standalone: true,
  imports: [CommonModule, RouterLink, DatePipe],
  template: `
    <main class='detalle-shell'>
      <section class='header'>
        <div>
          <p class='eyebrow'>Recepción de Vehículos</p>
          <h1>Detalle de recepción</h1>
          <p class='subtitle'>Consulta la ficha completa, diagnósticos, observaciones y el estado operativo del vehículo.</p>
        </div>

        <div class='header-actions'>
          <a class='button ghost' routerLink='/recepciones'>Volver al listado</a>
          <a class='button ghost' *ngIf='canEdit && recepcion' [routerLink]="['/recepciones', recepcion.id, 'editar']">Editar</a>
          <a class='button ghost' *ngIf='canDiagnose && recepcion' [routerLink]="['/recepciones', recepcion.id, 'diagnostico']">Diagnóstico</a>
          <a class='button ghost' *ngIf='canObserve && recepcion' [routerLink]="['/recepciones', recepcion.id, 'observaciones']">Observaciones</a>
          <button class='button primary' type='button' *ngIf='canGenerateFicha && recepcion' (click)='generateFicha()'>Generar ficha</button>
        </div>
      </section>

      <section class='card' *ngIf='isLoading'>
        <p>Cargando detalle de recepción...</p>
      </section>

      <section class='card' *ngIf='!isLoading && errorMessage'>
        <p class='error'>{{ errorMessage }}</p>
      </section>

      <ng-container *ngIf='!isLoading && recepcion'>
        <section class='card hero-card'>
          <div class='hero-grid'>
            <div>
              <p class='label'>Código ficha</p>
              <strong>{{ recepcion.codigo_ficha }}</strong>
            </div>
            <div>
              <p class='label'>Estado</p>
              <span class='status-pill' [class.is-finalized]='recepcion.status === "finalizada"' [class.is-delivered]='recepcion.status === "entregada"'>
                {{ recepcion.status }}
              </span>
            </div>
            <div>
              <p class='label'>Recepción</p>
              <strong>{{ recepcion.fecha_recepcion | date:'short' }}</strong>
            </div>
            <div>
              <p class='label'>Mecánico</p>
              <strong>{{ recepcion.ficha.assigned_mecanico_name || 'Sin asignar' }}</strong>
            </div>
          </div>

          <div class='status-actions' *ngIf='recepcion'>
            <button
              class='button action-button finalize'
              type='button'
              *ngIf='canFinalize'
              [disabled]='isSavingAction'
              (click)='transitionToStatus("finalizada")'
            >
              Finalizar
            </button>

            <button
              class='button action-button deliver'
              type='button'
              *ngIf='canManageDelivery'
              [disabled]='isSavingAction || !canDeliver'
              (click)='transitionToStatus("entregada")'
            >
              Entregar
            </button>
          </div>

          <p class='action-note' *ngIf='canManageDelivery && !canDeliver'>
            Para entregar, la recepción debe estar en estado finalizada.
          </p>
          <p class='action-success' *ngIf='actionMessage'>{{ actionMessage }}</p>
          <p class='action-error' *ngIf='actionError'>{{ actionError }}</p>
        </section>

        <section class='grid-two'>
          <article class='card'>
            <h2>Cliente</h2>
            <ul class='detail-list'>
              <li><strong>Nombre:</strong> {{ recepcion.cliente.full_name }}</li>
              <li><strong>Carnet:</strong> {{ recepcion.cliente.identity_card }}</li>
              <li><strong>Teléfono:</strong> {{ recepcion.cliente.phone }}</li>
              <li><strong>Email:</strong> {{ recepcion.cliente.email || 'No registrado' }}</li>
              <li><strong>Dirección:</strong> {{ recepcion.cliente.address || 'No registrada' }}</li>
              <li><strong>ID móvil:</strong> {{ recepcion.cliente.mobile_client_id || 'Sin vínculo' }}</li>
            </ul>
          </article>

          <article class='card'>
            <h2>Vehículo</h2>
            <ul class='detail-list'>
              <li><strong>Placa:</strong> {{ recepcion.vehiculo.plate }}</li>
              <li><strong>Marca:</strong> {{ recepcion.vehiculo.brand }}</li>
              <li><strong>Modelo:</strong> {{ recepcion.vehiculo.model }}</li>
              <li><strong>Año:</strong> {{ recepcion.vehiculo.year }}</li>
              <li><strong>Color:</strong> {{ recepcion.vehiculo.color }}</li>
              <li><strong>VIN:</strong> {{ recepcion.vehiculo.vin || 'No registrado' }}</li>
              <li><strong>Número de motor:</strong> {{ recepcion.vehiculo.engine_number || 'No registrado' }}</li>
            </ul>
          </article>
        </section>

        <section class='card'>
          <h2>Ficha</h2>
          <ul class='detail-list'>
            <li><strong>Kilometraje:</strong> {{ recepcion.ficha.kilometraje ?? 'No registrado' }}</li>
            <li><strong>Nivel combustible:</strong> {{ recepcion.ficha.nivel_combustible || 'No registrado' }}</li>
            <li><strong>Recepcionado por:</strong> {{ recepcion.ficha.recepcionado_por_role }} #{{ recepcion.ficha.recepcionado_por_user_id }}</li>
            <li><strong>Estado final:</strong> {{ recepcion.ficha.status }}</li>
            <li><strong>Finalizado el:</strong> {{ recepcion.ficha.finalized_at ? (recepcion.ficha.finalized_at | date:'short') : 'Sin registro' }}</li>
            <li><strong>Entregado el:</strong> {{ recepcion.ficha.delivered_at ? (recepcion.ficha.delivered_at | date:'short') : 'Sin registro' }}</li>
            <li><strong>Entregado por usuario ID:</strong> {{ recepcion.ficha.delivered_by_user_id ?? 'Sin registro' }}</li>
            <li><strong>Observaciones generales:</strong> {{ recepcion.ficha.observaciones_generales || 'Sin observaciones' }}</li>
          </ul>
        </section>

        <section class='grid-two'>
          <article class='card'>
            <h2>Accesorios</h2>
            <p class='empty' *ngIf='!recepcion.accesorios.length'>No se registraron accesorios.</p>
            <ul class='detail-list' *ngIf='recepcion.accesorios.length'>
              <li *ngFor='let item of recepcion.accesorios'>
                <strong>{{ item.name }}</strong> · {{ item.quantity }}<span *ngIf='item.notes'> · {{ item.notes }}</span>
              </li>
            </ul>
          </article>

          <article class='card'>
            <h2>Problemas reportados</h2>
            <p class='empty' *ngIf='!recepcion.problemas.length'>No se registraron problemas.</p>
            <ul class='detail-list' *ngIf='recepcion.problemas.length'>
              <li *ngFor='let item of recepcion.problemas'>
                <strong>{{ item.description }}</strong> · {{ item.priority || 'Sin prioridad' }} · {{ item.reported_by }}
              </li>
            </ul>
          </article>
        </section>

        <section class='grid-two'>
          <article class='card'>
            <h2>Diagnósticos</h2>
            <p class='empty' *ngIf='!recepcion.diagnosticos.length'>Aún no hay diagnósticos registrados.</p>
            <div class='timeline' *ngIf='recepcion.diagnosticos.length'>
              <article class='timeline-item' *ngFor='let item of recepcion.diagnosticos'>
                <strong>{{ item.mecanico_name || ('Mecánico #' + item.mecanico_id) }}</strong>
                <p>{{ item.diagnostic_text }}</p>
                <small>Trabajo estimado: {{ item.estimated_work || 'No especificado' }}</small>
                <small>Costo estimado: {{ item.estimated_cost ?? 'No especificado' }}</small>
              </article>
            </div>
          </article>

          <article class='card'>
            <h2>Observaciones</h2>
            <p class='empty' *ngIf='!recepcion.observaciones.length'>Aún no hay observaciones registradas.</p>
            <div class='timeline' *ngIf='recepcion.observaciones.length'>
              <article class='timeline-item' *ngFor='let item of recepcion.observaciones'>
                <strong>{{ item.mecanico_name || ('Mecánico #' + item.mecanico_id) }}</strong>
                <p>{{ item.observation_text }}</p>
                <small>Estado de trabajo: {{ item.work_status || 'No especificado' }}</small>
              </article>
            </div>
          </article>
        </section>
      </ng-container>
    </main>
  `,
  styles: [`
    .detalle-shell { min-height: 100vh; background: #f4f7fb; padding: 2rem; color: #15304f; }
    .header, .header-actions, .hero-grid, .grid-two, .status-actions { display: flex; gap: 1rem; }
    .header { justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; }
    .header-actions { flex-wrap: wrap; }
    .eyebrow { margin: 0 0 .35rem; text-transform: uppercase; letter-spacing: .12em; font-size: .78rem; color: #85711b; font-weight: 700; }
    h1, h2 { margin: 0; }
    .subtitle { margin: .5rem 0 0; color: #50667f; }
    .card { background: #fff; border-radius: 1.25rem; box-shadow: 0 18px 40px rgba(17, 48, 83, .08); padding: 1.25rem; margin-bottom: 1rem; }
    .hero-card { display: grid; gap: 1rem; }
    .hero-grid { justify-content: space-between; flex-wrap: wrap; }
    .grid-two { align-items: stretch; }
    .grid-two > * { flex: 1 1 0; }
    .label { margin: 0 0 .35rem; font-size: .82rem; text-transform: uppercase; letter-spacing: .08em; color: #60758f; }
    .status-pill { display: inline-flex; padding: .35rem .7rem; background: #eef5ff; color: #143761; border-radius: 999px; font-size: .85rem; font-weight: 700; }
    .status-pill.is-finalized { background: #e9f8ef; color: #17663a; }
    .status-pill.is-delivered { background: #f2f0ff; color: #4b3cb5; }
    .status-actions { flex-wrap: wrap; }
    .action-button.finalize { background: #1d6b42; color: #fff; }
    .action-button.deliver { background: #143761; color: #fff; }
    .action-note { margin: 0; color: #5f7289; }
    .action-success { margin: 0; color: #17663a; font-weight: 700; }
    .action-error { margin: 0; color: #b03b2d; font-weight: 700; }
    .detail-list { list-style: none; padding: 0; margin: 1rem 0 0; display: grid; gap: .55rem; }
    .timeline { display: grid; gap: .85rem; margin-top: 1rem; }
    .timeline-item { border: 1px solid #e1e9f3; border-radius: 1rem; padding: 1rem; display: grid; gap: .35rem; }
    .timeline-item p { margin: 0; }
    .timeline-item small { color: #5d738c; }
    .button { border: none; border-radius: .85rem; padding: .85rem 1.15rem; text-decoration: none; cursor: pointer; font-weight: 700; font: inherit; }
    .button.primary { background: #143761; color: #fff; }
    .button.ghost { background: #edf3fa; color: #143761; }
    .button:disabled { opacity: .55; cursor: not-allowed; }
    .error { color: #b03b2d; }
    .empty { color: #60758f; margin-top: 1rem; }
    @media (max-width: 768px) {
      .detalle-shell { padding: 1rem; }
      .header, .grid-two { flex-direction: column; }
    }
  `],
})
export class RecepcionDetallePageComponent implements OnInit {
  private readonly recepcionesService = inject(RecepcionesService);
  private readonly route = inject(ActivatedRoute);
  private readonly session = getStoredSession();

  recepcion: RecepcionDetalle | null = null;
  isLoading = false;
  isSavingAction = false;
  errorMessage = '';
  actionMessage = '';
  actionError = '';

  get role(): AppRole | null {
    return this.session?.role ?? null;
  }

  get currentUserId(): number | null {
    return this.session?.id ?? null;
  }

  get isAssignedMechanic(): boolean {
    return this.role === 'mecanico' && !!this.recepcion && this.currentUserId === this.recepcion.ficha.assigned_mecanico_id;
  }

  get canEdit(): boolean {
    return this.role === 'admin' || this.role === 'secretaria';
  }

  get canDiagnose(): boolean {
    return this.role === 'mecanico' && this.isAssignedMechanic;
  }

  get canObserve(): boolean {
    return this.role === 'mecanico' && this.isAssignedMechanic;
  }

  get canGenerateFicha(): boolean {
    return this.role === 'admin' || this.role === 'secretaria';
  }

  get canFinalize(): boolean {
    if (!this.recepcion) {
      return false;
    }

    return this.isAssignedMechanic && ['registrada', 'en_diagnostico', 'en_trabajo'].includes(this.recepcion.status);
  }


  get canManageDelivery(): boolean {
    return this.role === 'admin' || this.role === 'secretaria';
  }

  get canDeliver(): boolean {
    return !!this.recepcion && this.recepcion.status === 'finalizada';
  }

  ngOnInit(): void {
    const recepcionId = Number(this.route.snapshot.paramMap.get('id'));
    if (!recepcionId) {
      this.errorMessage = 'No se encontró la recepción solicitada.';
      return;
    }

    this.loadRecepcion(recepcionId);
  }

  generateFicha(): void {
    if (!this.recepcion) {
      return;
    }

    this.recepcionesService.obtenerFicha(this.recepcion.id).subscribe({
      next: (ficha) => {
        const printWindow = window.open('', '_blank', 'width=960,height=720');
        if (!printWindow) {
          return;
        }

        printWindow.document.write(`
          <html>
            <head>
              <title>Ficha ${ficha.codigo_ficha}</title>
              <style>
                body { font-family: Arial, sans-serif; padding: 24px; color: #18324d; }
                h1, h2 { margin-bottom: 8px; }
                section { margin-bottom: 20px; }
                ul { padding-left: 18px; }
              </style>
            </head>
            <body>
              <h1>Ficha de recepción ${ficha.codigo_ficha}</h1>
              <section>
                <h2>Cliente</h2>
                <p>${ficha.cliente.full_name} · ${ficha.cliente.identity_card} · ${ficha.cliente.phone}</p>
              </section>
              <section>
                <h2>Vehículo</h2>
                <p>${ficha.vehiculo.brand} ${ficha.vehiculo.model} ${ficha.vehiculo.year} · ${ficha.vehiculo.plate}</p>
              </section>
              <section>
                <h2>Problemas</h2>
                <ul>${ficha.problemas.map((item) => `<li>${item.description}</li>`).join('')}</ul>
              </section>
            </body>
          </html>
        `);
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
      },
      error: () => {
        this.errorMessage = 'No se pudo generar la ficha para impresión.';
      },
    });
  }

  transitionToStatus(nextStatus: RecepcionStatus): void {
    if (!this.recepcion || this.isSavingAction) {
      return;
    }

    if (nextStatus === 'finalizada' && !this.canFinalize) {
      this.actionError = 'Solo el mecánico asignado puede finalizar esta recepción.';
      return;
    }

    if (nextStatus === 'entregada' && !this.canDeliver) {
      this.actionError = 'La recepción debe estar finalizada antes de entregarla.';
      return;
    }

    this.isSavingAction = true;
    this.actionError = '';
    this.actionMessage = '';

    const request = nextStatus === 'finalizada'
      ? this.recepcionesService.finalizarRecepcion(this.recepcion.id)
      : this.recepcionesService.entregarRecepcion(this.recepcion.id);

    request.subscribe({
      next: (updated) => {
        this.recepcion = updated;
        this.isSavingAction = false;
        this.actionMessage = nextStatus === 'finalizada'
          ? 'La recepción quedó finalizada correctamente.'
          : 'La recepción quedó entregada correctamente.';
      },
      error: (error: HttpErrorResponse) => {
        this.isSavingAction = false;
        this.actionError = this.resolveErrorMessage(error);
      },
    });
  }

  private loadRecepcion(id: number): void {
    this.isLoading = true;
    this.errorMessage = '';

    this.recepcionesService.obtenerRecepcion(id).subscribe({
      next: (recepcion) => {
        this.recepcion = recepcion;
        this.isLoading = false;
      },
      error: (error: HttpErrorResponse) => {
        this.recepcion = null;
        this.isLoading = false;
        this.errorMessage = this.resolveErrorMessage(error);
      },
    });
  }

  private resolveErrorMessage(error: HttpErrorResponse): string {
    const detail = error.error?.detail;

    if (error.status === 403) {
      return 'No tienes permisos para ver o modificar esta recepción.';
    }

    if (typeof detail === 'string' && detail.trim()) {
      return detail;
    }

    return 'No se pudo cargar el detalle de la recepción.';
  }
}
