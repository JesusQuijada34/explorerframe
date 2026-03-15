# ExplorerFrame OAuth Platform

## Overview
Convertir ExplorerFrame en una plataforma OAuth 2.0 donde desarrolladores pueden crear apps y ofrecer login con ExplorerFrame a sus usuarios.

## Features

### 1. Developer Console
- Panel para crear/gestionar aplicaciones
- Generar Client ID y Client Secret
- Configurar redirect URIs
- Ver estadísticas de uso
- Revocar acceso

### 2. OAuth 2.0 Endpoints
- `GET /oauth/authorize` — Solicitar autorización del usuario
- `POST /oauth/token` — Intercambiar código por token
- `GET /oauth/userinfo` — Obtener datos del usuario autenticado
- `POST /oauth/revoke` — Revocar token

### 3. Database Schema
- `oauth_apps` — Aplicaciones registradas
- `oauth_authorizations` — Códigos de autorización (corta vida)
- `oauth_tokens` — Access tokens (larga vida)

## Implementation Tasks

- [ ] Crear modelos de datos en MongoDB
- [ ] Implementar endpoints OAuth
- [ ] Crear panel de desarrolladores
- [ ] Agregar UI para gestionar apps
- [ ] Documentación de API

