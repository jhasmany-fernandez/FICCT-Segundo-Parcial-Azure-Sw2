import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { map } from 'rxjs/operators';

import { API_BASE_URL } from '../api-base';

// ── Tipos del contrato REST existente (snake_case) ──────────────────────────
export type SucursalEstado = 'ACTIVO' | 'INACTIVO';

export type Sucursal = {
  id: number;
  nombre: string;
  direccion: string;
  zona: string | null;
  telefono: string | null;
  email: string | null;
  latitud: number | null;
  longitud: number | null;
  horario_atencion: string | null;
  responsable: string | null;
  estado: SucursalEstado;
  fecha_registro: string;
  fecha_modificacion: string | null;
};

// Input en snake_case: lo que viene del formulario del dashboard
export type SucursalInputPayload = {
  nombre: string;
  direccion: string;
  zona?: string | null;
  telefono?: string | null;
  email?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  horario_atencion?: string | null;
  responsable?: string | null;
  estado?: string;
};

// ── Tipos internos del response GraphQL (snake_case real del schema) ─────────
type GqlSucursal = {
  id: number;
  nombre: string;
  direccion: string;
  zona: string | null;
  telefono: string | null;
  email: string | null;
  latitud: number | null;
  longitud: number | null;
  horario_atencion: string | null;
  responsable: string | null;
  estado: string;
  fecha_registro: string;
  fecha_modificacion: string | null;
};

type GqlResponse<T> = {
  data: T | null;
  errors?: Array<{ message: string; locations?: unknown; path?: unknown }>;
};

// Fragmento reutilizable con todos los campos
const SUCURSAL_FIELDS = `
  id nombre direccion zona telefono email
  latitud longitud horario_atencion responsable
  estado fecha_registro fecha_modificacion
`;

const SUCURSAL_FIELDS_SHORT = `id nombre estado`;

// ── Mapeo snake_case GQL → snake_case Sucursal ───────────────────────────────
function gqlToSucursal(g: GqlSucursal): Sucursal {
  return {
    id: g.id,
    nombre: g.nombre,
    direccion: g.direccion,
    zona: g.zona ?? null,
    telefono: g.telefono ?? null,
    email: g.email ?? null,
    latitud: g.latitud ?? null,
    longitud: g.longitud ?? null,
    horario_atencion: g.horario_atencion ?? null,
    responsable: g.responsable ?? null,
    estado: g.estado as SucursalEstado,
    fecha_registro: g.fecha_registro ?? '',
    fecha_modificacion: g.fecha_modificacion ?? null,
  };
}

// ── Mapeo snake_case payload → snake_case GQL input ───────────────────────────
function payloadToGqlInput(p: SucursalInputPayload): Record<string, unknown> {
  return {
    nombre: p.nombre,
    direccion: p.direccion,
    zona: p.zona ?? null,
    telefono: p.telefono ?? null,
    email: p.email ?? null,
    latitud: p.latitud ?? null,
    longitud: p.longitud ?? null,
    horario_atencion: p.horario_atencion ?? null,
    responsable: p.responsable ?? null,
    estado: p.estado ?? 'ACTIVO',
  };
}

// ── Servicio ─────────────────────────────────────────────────────────────────
@Injectable({ providedIn: 'root' })
export class SucursalGraphqlService {
  private readonly http = inject(HttpClient);
  private readonly graphqlUrl = `${API_BASE_URL}/graphql`;

  // Envía la petición GraphQL y lanza un Error si hay errores en la respuesta
  private post<T>(body: {
    query: string;
    variables?: Record<string, unknown>;
  }): Observable<T> {
    return this.http.post<GqlResponse<T>>(this.graphqlUrl, body).pipe(
      map((response) => {
        if (response.errors?.length) {
          throw new Error(response.errors[0].message);
        }
        if (response.data === null || response.data === undefined) {
          throw new Error('Respuesta vacía del servidor GraphQL');
        }
        return response.data;
      }),
    );
  }

  // ── Queries ────────────────────────────────────────────────────────────────

  listarSucursales(estado?: string | null): Observable<Sucursal[]> {
    return this.post<{ sucursales: GqlSucursal[] }>({
      query: `
        query ListarSucursales($estado: String) {
          sucursales(estado: $estado) { ${SUCURSAL_FIELDS} }
        }
      `,
      variables: { estado: estado ?? null },
    }).pipe(map((data) => data.sucursales.map(gqlToSucursal)));
  }

  obtenerSucursal(id: number): Observable<Sucursal | null> {
    return this.post<{ sucursal: GqlSucursal | null }>({
      query: `
        query ObtenerSucursal($id: Int!) {
          sucursal(id: $id) { ${SUCURSAL_FIELDS} }
        }
      `,
      variables: { id },
    }).pipe(map((data) => (data.sucursal ? gqlToSucursal(data.sucursal) : null)));
  }

  // ── Mutations ──────────────────────────────────────────────────────────────

  crearSucursal(input: SucursalInputPayload): Observable<Sucursal> {
    return this.post<{ crear_sucursal: GqlSucursal }>({
      query: `
        mutation CrearSucursal($input: SucursalInput!) {
          crear_sucursal(input: $input) { ${SUCURSAL_FIELDS} }
        }
      `,
      variables: { input: payloadToGqlInput(input) },
    }).pipe(map((data) => gqlToSucursal(data.crear_sucursal)));
  }

  actualizarSucursal(id: number, input: SucursalInputPayload): Observable<Sucursal> {
    return this.post<{ actualizar_sucursal: GqlSucursal }>({
      query: `
        mutation ActualizarSucursal($id: Int!, $input: SucursalInput!) {
          actualizar_sucursal(id: $id, input: $input) { ${SUCURSAL_FIELDS} }
        }
      `,
      variables: { id, input: payloadToGqlInput(input) },
    }).pipe(map((data) => gqlToSucursal(data.actualizar_sucursal)));
  }

  cambiarEstadoSucursal(id: number, estado: string): Observable<Sucursal> {
    return this.post<{ cambiar_estado_sucursal: GqlSucursal }>({
      query: `
        mutation CambiarEstadoSucursal($id: Int!, $estado: String!) {
          cambiar_estado_sucursal(id: $id, estado: $estado) { ${SUCURSAL_FIELDS_SHORT} }
        }
      `,
      variables: { id, estado },
    }).pipe(map((data) => gqlToSucursal(data.cambiar_estado_sucursal)));
  }

  eliminarSucursal(id: number): Observable<boolean> {
    return this.post<{ eliminar_sucursal: boolean }>({
      query: `
        mutation EliminarSucursal($id: Int!) {
          eliminar_sucursal(id: $id)
        }
      `,
      variables: { id },
    }).pipe(map((data) => data.eliminar_sucursal));
  }
}
