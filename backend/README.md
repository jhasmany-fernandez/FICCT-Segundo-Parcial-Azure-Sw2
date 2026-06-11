# Backend NestJS + FastAPI Core

Esta estructura deja a NestJS como backend visible y mantiene FastAPI como core interno/legacy.

## Estructura

- `src/`: gateway principal en NestJS
- `core-service/`: copia del backend FastAPI actual
- `uploads/`: archivos compartidos
- `Dockerfile`: build de NestJS
- `docker-compose.yml`: levanta NestJS al frente y FastAPI detrás
- `Dockerfile.dev`: backend FastAPI legado original, conservado por compatibilidad
- `app/`: código FastAPI legado original, conservado por compatibilidad

## Flujo

1. Angular llama a NestJS en `http://localhost:8000`
2. NestJS reenvía `/api/*`, `/graphql`, `/api/graphql` y `/uploads/*` a FastAPI
3. FastAPI mantiene la lógica de negocio y los archivos existentes

## Arranque

```bash
cd backend
docker compose up -d --build
```

## Endpoints visibles en NestJS

- `GET /health`
- `GET /api/health`
- `POST /api/auth/login`
- `GET /api/emergencias`
- `GET /api/clientes`
- `GET /api/mecanicos`
- `GET /api/sucursales`
- `POST /graphql`

Además, cualquier llamada a `/api/*`, `/api/graphql`, `/graphql` y `/uploads/*` se proxya a FastAPI para no romper el frontend actual.
