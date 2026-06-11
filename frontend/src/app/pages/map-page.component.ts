import { CommonModule } from '@angular/common';
import { HttpClient, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { AfterViewInit, Component, ElementRef, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { API_BASE_URL } from '../api-base';
import { getStoredSession } from '../session';

declare const L: any;

type WorkshopMapApiItem = {
  id?: number | string | null;
  nombre?: string | null;
  workshop_name?: string | null;
  contact_name?: string | null;
  responsable?: string | null;
  phone?: string | null;
  telefono?: string | null;
  email?: string | null;
  zone?: string | null;
  zona?: string | null;
  specialty?: string | null;
  especialidad?: string | null;
  latitud?: number | string | null;
  longitud?: number | string | null;
  latitude?: number | string | null;
  longitude?: number | string | null;
  lat?: number | string | null;
  lng?: number | string | null;
  timezone?: string | null;
  utc_offset_minutes?: number | null;
  created_at?: string | null;
  fecha_registro?: string | null;
};

const SKIP_AUTH_REDIRECT_HEADER = 'X-Skip-Auth-Redirect';

type WorkshopMapItem = {
  id: number;
  workshop_name: string;
  contact_name: string;
  phone: string;
  email: string;
  zone: string;
  specialty: string;
  latitude: number | null;
  longitude: number | null;
  timezone: string | null;
  utc_offset_minutes: number | null;
  created_at: string;
};

@Component({
  selector: 'app-map-page',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="page">
      <section class="section-hero map-hero">
        <div>
          <p class="eyebrow">Mapa</p>
          <h1>Sucursales registradas en el mapa</h1>
          <p class="lead">
            Mostramos los puntos guardados en la ubicacion registrada de cada sucursal y destacamos
            la especialidad principal de cada una.
          </p>
        </div>

        <div class="map-hero-card">
          <span>Cobertura real</span>
          <strong>{{ mappedWorkshops.length }} puntos con coordenadas</strong>
          <p>
            Cada marcador usa la ubicacion registrada y muestra la especialidad de la sucursal al hacer
            clic.
          </p>
        </div>
      </section>

      <section class="map-layout">
        <div class="map-frame">
          <div #mapCanvas class="map-canvas" aria-label="Mapa de sucursales registradas"></div>

          <div class="map-overlay-message" *ngIf="isLoading">
            Cargando ubicaciones de sucursales...
          </div>

          <div class="map-overlay-message error" *ngIf="!isLoading && loadError">
            {{ loadError }}
          </div>

          <div class="map-overlay-message" *ngIf="!isLoading && !loadError && !mappedWorkshops.length">
            No hay sucursales con coordenadas registradas para mostrar en el mapa.
          </div>
        </div>

        <aside class="map-sidebar">
          <article class="map-note">
            <p class="eyebrow">Referencia</p>
            <h2>Puntos desde el registro de sucursales</h2>
            <p>
              El mapa consume los datos actuales de la API y pinta solo los registros que tienen
              latitud y longitud validas.
            </p>
          </article>

          <article class="map-stat">
            <span>Especialidades</span>
            <strong>{{ specialtiesCount }}</strong>
          </article>

          <article class="map-stat">
            <span>Último punto</span>
            <strong>{{ selectedWorkshop?.specialty || 'Sin selección' }}</strong>
            <p *ngIf="selectedWorkshop">
              {{ selectedWorkshop.workshop_name }} · {{ selectedWorkshop.zone }}
            </p>
          </article>

          <article class="map-stat">
            <span>Acción</span>
            <a class="button primary" routerLink="/dashboard">Ver registros</a>
          </article>

          <article class="map-list-card" *ngIf="mappedWorkshops.length">
            <div class="map-list-head">
              <span>Sucursales ubicadas</span>
              <strong>{{ mappedWorkshops.length }}</strong>
            </div>

            <button
              class="map-list-item"
              type="button"
              *ngFor="let workshop of mappedWorkshops"
              (click)="focusWorkshop(workshop)"
            >
              <strong>{{ workshop.specialty }}</strong>
              <span>{{ workshop.workshop_name }}</span>
              <small>{{ workshop.latitude | number: '1.4-4' }}, {{ workshop.longitude | number: '1.4-4' }}</small>
            </button>
          </article>
        </aside>
      </section>
    </main>
  `,
  styleUrl: './shared-pages.css',
})
export class MapPageComponent implements AfterViewInit {
  private readonly http = inject(HttpClient);
  private readonly workshopsApiUrl = `${API_BASE_URL}/sucursales`;

  @ViewChild('mapCanvas', { static: true })
  private readonly mapCanvasRef?: ElementRef<HTMLDivElement>;

  workshops: WorkshopMapItem[] = [];
  isLoading = true;
  loadError = '';
  selectedWorkshop: WorkshopMapItem | null = null;

  private map?: any;
  private markersLayer?: any;

  get mappedWorkshops(): WorkshopMapItem[] {
    return this.workshops.filter(
      (workshop) => typeof workshop.latitude === 'number' && typeof workshop.longitude === 'number',
    );
  }

  get specialtiesCount(): number {
    return new Set(this.mappedWorkshops.map((workshop) => workshop.specialty).filter(Boolean)).size;
  }

  ngAfterViewInit(): void {
    this.initializeMap();
    this.loadWorkshops();
    this.scheduleMapResize();
  }

  focusWorkshop(workshop: WorkshopMapItem): void {
    if (!this.map || workshop.latitude === null || workshop.longitude === null) {
      return;
    }

    this.selectedWorkshop = workshop;
    this.map.setView([workshop.latitude, workshop.longitude], 15, { animate: true });
    this.scheduleMapResize();
  }

  private initializeMap(): void {
    const element = this.mapCanvasRef?.nativeElement;

    if (!element || typeof L === 'undefined') {
      this.loadError = 'No se pudo inicializar el mapa.';
      this.isLoading = false;
      return;
    }

    this.map = L.map(element, {
      zoomControl: true,
      scrollWheelZoom: true,
    }).setView([-17.7833, -63.1821], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(this.map);

    this.markersLayer = L.layerGroup().addTo(this.map);
    this.scheduleMapResize();
  }

  private loadWorkshops(): void {
    this.isLoading = true;
    this.loadError = '';

    this.http.get<WorkshopMapApiItem[]>(this.workshopsApiUrl, { headers: this.getRequestHeaders() }).subscribe({
      next: (workshops) => {
        this.workshops = workshops.map((item, index) => this.normalizeWorkshop(item, index));
        this.renderWorkshopMarkers();
        this.isLoading = false;
        this.scheduleMapResize();
      },
      error: (error: HttpErrorResponse) => {
        this.isLoading = false;
        this.loadError = this.resolveLoadError(error);
        console.error('MapPageComponent: error al cargar sucursales desde la API', {
          endpoint: this.workshopsApiUrl,
          status: error.status,
          statusText: error.statusText,
          detail: error.error,
          message: error.message,
        });
      },
    });
  }

  private renderWorkshopMarkers(): void {
    if (!this.map || !this.markersLayer) {
      return;
    }

    this.markersLayer.clearLayers();

    const workshops = this.mappedWorkshops;

    if (!workshops.length) {
      this.selectedWorkshop = null;
      this.map.setView([-17.7833, -63.1821], 12);
      this.scheduleMapResize();
      return;
    }

    const bounds: [number, number][] = [];

    workshops.forEach((workshop) => {
      const { latitude, longitude } = workshop;

      if (latitude === null || longitude === null) {
        return;
      }

      bounds.push([latitude, longitude]);

      const marker = L.marker([latitude, longitude]).addTo(this.markersLayer);
      marker.bindPopup(`
        <strong>${this.escapeHtml(workshop.workshop_name)}</strong><br>
        ${this.escapeHtml(workshop.zone)}<br>
        ${this.escapeHtml(workshop.specialty)}
      `);

      marker.on('click', () => {
        this.selectedWorkshop = workshop;
      });
    });

    this.selectedWorkshop = workshops[0];

    if (bounds.length === 1) {
      this.map.setView(bounds[0], 15);
      this.scheduleMapResize();
      return;
    }

    this.map.fitBounds(bounds, {
      padding: [30, 30],
      maxZoom: 15,
    });
    this.scheduleMapResize();
  }

  private normalizeWorkshop(item: WorkshopMapApiItem, index: number): WorkshopMapItem {
    const latitude = this.normalizeCoordinate(item.latitud, item.latitude, item.lat);
    const longitude = this.normalizeCoordinate(item.longitud, item.longitude, item.lng);
    const workshopName = this.pickFirstString(item.nombre, item.workshop_name) || `Sucursal ${index + 1}`;
    const zone = this.pickFirstString(item.zona, item.zone) || 'Sin zona';
    const specialty =
      this.pickFirstString(item.especialidad, item.specialty) ||
      this.pickFirstString(item.responsable, item.contact_name) ||
      'Sucursal registrada';

    return {
      id: this.normalizeId(item.id, index),
      workshop_name: workshopName,
      contact_name: this.pickFirstString(item.responsable, item.contact_name) || 'Sin responsable',
      phone: this.pickFirstString(item.telefono, item.phone) || 'Sin teléfono',
      email: this.pickFirstString(item.email) || 'Sin correo',
      zone,
      specialty,
      latitude,
      longitude,
      timezone: this.pickFirstString(item.timezone),
      utc_offset_minutes: typeof item.utc_offset_minutes === 'number' ? item.utc_offset_minutes : null,
      created_at: this.pickFirstString(item.fecha_registro, item.created_at) || '',
    };
  }

  private normalizeCoordinate(...values: Array<number | string | null | undefined>): number | null {
    for (const value of values) {
      if (typeof value === 'number' && Number.isFinite(value)) {
        return value;
      }

      if (typeof value === 'string' && value.trim()) {
        const parsed = Number(value);
        if (Number.isFinite(parsed)) {
          return parsed;
        }
      }
    }

    return null;
  }

  private normalizeId(value: number | string | null | undefined, index: number): number {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }

    if (typeof value === 'string' && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }

    return index + 1;
  }

  private pickFirstString(...values: Array<string | null | undefined>): string | null {
    for (const value of values) {
      if (typeof value === 'string' && value.trim()) {
        return value.trim();
      }
    }

    return null;
  }

  private getRequestHeaders(): HttpHeaders {
    const token = getStoredSession()?.accessToken?.trim();
    const headers: Record<string, string> = {
      [SKIP_AUTH_REDIRECT_HEADER]: 'true',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    return new HttpHeaders(headers);
  }

  private resolveLoadError(error: HttpErrorResponse): string {
    if (error.status === 401) {
      return 'Inicia sesión para ver las sucursales registradas en el mapa.';
    }

    const detail = typeof error.error?.detail === 'string' ? error.error.detail.trim() : '';
    if (detail) {
      return detail;
    }

    return 'No se pudieron cargar las sucursales registradas desde la API.';
  }

  private escapeHtml(value: string): string {
    return value
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  private scheduleMapResize(): void {
    if (!this.map) {
      return;
    }

    requestAnimationFrame(() => {
      this.map?.invalidateSize();

      setTimeout(() => {
        this.map?.invalidateSize();
      }, 150);
    });
  }
}
