# Plan de Implementación: ExplorerFrame

## Visión General

El código base ya está mayormente implementado. Las tareas se enfocan en:
corregir bugs identificados en la revisión del código, extraer funciones puras
testables, implementar mejoras de seguridad del diseño, y escribir los
property-based tests con `hypothesis` para las 8 propiedades de corrección.

## Tareas

- [~] 1. Extraer funciones puras para autorización y parsing
  - [ ] 1.1 Extraer `parse_authorized_ids(ids_str)` de `fetch_authorized_ids()` en `explorer.py`
    - Debe retornar `(set[int], set[int])` — (usuarios, grupos)
    - Manejar cadena vacía retornando dos conjuntos vacíos
    - _Requisitos: 1.3, 1.4, 1.5_

  - [ ] 1.2 Extraer `is_authorized_by_id(user_id, chat_id, authorized_users, authorized_groups)` en `explorer.py`
    - Función pura sin dependencia de `Update`; el handler `is_authorized` la llama internamente
    - _Requisitos: 1.1, 1.2_

  - [ ]* 1.3 Escribir property test P1 — ningún ID no autorizado pasa el filtro
    - **Propiedad P1: Autorización — ningún ID no autorizado pasa el filtro**
    - **Valida: Requisito 1.1, 1.2**
    - Usar `@given(st.integers())` con `assume` para excluir IDs autorizados

  - [ ]* 1.4 Escribir property test P2 — parsing de AUTHORIZED_IDS idempotente
    - **Propiedad P2: Parsing de AUTHORIZED_IDS — separación correcta**
    - **Valida: Requisito 1.3, 1.4**
    - Generar listas de user_ids y group_ids, construir cadena, parsear y verificar igualdad de conjuntos

- [ ] 2. Corregir header de autenticación en llamadas HTTP al Server
  - [ ] 2.1 Corregir `check_for_updates()` en `explorer.py`: cambiar `Authorization: Bearer` por `X-API-Key`
    - El endpoint `/api/v1/download/token` requiere header `X-API-Key`, no `Authorization: Bearer`
    - _Requisitos: 3.1, 14.2_

  - [ ] 2.2 Corregir `download_and_install()` en `winverm.py`: cambiar `Authorization: Bearer` por `X-API-Key`
    - Mismo problema que 2.1 pero en el script auxiliar
    - _Requisitos: 12.1, 12.3_

  - [ ] 2.3 Convertir `check_for_updates()` en `explorer.py` a función `async` y registrarla directamente en job_queue
    - Actualmente se envuelve con `asyncio.create_task(check_for_updates())` pero la función es síncrona
    - Renombrar a `check_for_updates_job(context)` con firma compatible con job_queue
    - _Requisitos: 14.1_

- [ ] 3. Extraer funciones puras de validación de tokens en `app.py`
  - [ ] 3.1 Extraer `is_token_valid(record, now=None)` en `app.py`
    - Retorna `True` si `record` no es `None` y `record["expires"] > now`
    - `now` por defecto es `utcnow()` para permitir inyección en tests
    - _Requisitos: 2.3, 3.3, 5.5_

  - [ ] 3.2 Extraer `consume_token(token_value, store)` como función pura para tests
    - `store` es un dict en memoria; retorna `"ok"` y elimina la clave, o `"forbidden"` si no existe
    - Solo para tests unitarios; la lógica real en MongoDB permanece en los endpoints
    - _Requisitos: 3.2_

  - [ ]* 3.3 Escribir property test P4 — token de descarga de un solo uso
    - **Propiedad P4: Download_Token — un solo uso**
    - **Valida: Requisito 3.2**
    - Verificar que tras consumir el token, el segundo intento retorna `"forbidden"`

  - [ ]* 3.4 Escribir property test P5 — tokens expirados son rechazados
    - **Propiedad P5: Expiración de tokens — tokens vencidos rechazados**
    - **Valida: Requisitos 2.3, 3.3**
    - Usar `@given(st.timedeltas(max_value=timedelta(seconds=-1)))` para generar fechas pasadas

- [ ] 4. Implementar property tests para el módulo de backup
  - [ ] 4.1 Extraer `is_new_file_with_registry(file_path, current_hash, registry)` de `is_new_file()` en `explorer.py`
    - Función pura que compara hash con el registry sin acceder al disco
    - _Requisitos: 5.2, 5.4_

  - [ ]* 4.2 Escribir property test P3 — backup registry detecta cambios correctamente
    - **Propiedad P3: Backup Registry — solo archivos modificados se incluyen**
    - **Valida: Requisito 5.2**
    - Verificar que mismo hash → `False`, hash distinto → `True`

  - [ ]* 4.3 Escribir property test P7 — SHA-256 es determinista
    - **Propiedad P7: Hashing SHA-256 — determinismo**
    - **Valida: Requisito 5.2**
    - `@given(st.binary())` — mismo contenido siempre produce mismo hexdigest

- [ ] 5. Implementar property tests para detección de cambios en pantalla y API keys
  - [ ]* 5.1 Escribir property test P6 — imágenes idénticas no superan umbral
    - **Propiedad P6: Detección de cambios — umbral consistente**
    - **Valida: Requisito 6.2**
    - `@given(st.integers(1,200), st.integers(1,200))` — array de ceros comparado consigo mismo

  - [ ]* 5.2 Escribir property test P8 — API Key tiene formato correcto
    - **Propiedad P8: API Key — formato 64 chars hex**
    - **Valida: Requisito 2.2 (asignación de api_key)**
    - Verificar longitud 64 y que todos los caracteres estén en `0-9a-f`

- [ ] 6. Checkpoint — Verificar que todos los tests pasen
  - Ejecutar `pytest tests/ -v` y confirmar que todas las propiedades pasan.
  - Asegurarse de que no hay errores de importación en `explorer.py` ni `app.py`.

- [ ] 7. Mejoras de seguridad: verificación de firma en parches
  - [ ] 7.1 Agregar verificación de hash SHA-256 del `patch.zip` antes de aplicarlo en `handle_document()` de `explorer.py`
    - El operador debe enviar un mensaje previo con el hash esperado, o incluir un archivo `patch.sha256` dentro del ZIP
    - Si el hash no coincide, responder con error y no aplicar el parche
    - _Requisitos: 11.1, 11.5_

  - [ ] 7.2 Agregar `SESSION_COOKIE_SECURE = True` en la configuración de `app.py`
    - Solo activar si `FLASK_ENV == "production"` para no romper desarrollo local
    - _Requisitos: 2.6_

- [ ] 8. Corrección: vaciar keylog solo si el envío fue exitoso
  - En `send_keylog()` de `explorer.py`, el archivo se vacía incluso si todos los envíos fallan
  - Mover `open(KEYLOG_FILE, 'w').close()` dentro del bloque `try` después del `break` exitoso
  - _Requisitos: 7.4_

- [ ] 9. Corrección: mensaje de inicio enviado a todos los usuarios autorizados
  - En `post_init()`, el mensaje "ExplorerFrame iniciado" ya se envía a `authorized_users`
  - Verificar que también se envía cuando `authorized_users` se carga correctamente antes del polling
  - Agregar log de advertencia si `authorized_users` está vacío al iniciar
  - _Requisitos: 13.1_

- [ ] 10. Checkpoint final — Revisión de integración
  - Ejecutar `pytest tests/ -v --tb=short` y confirmar que todos los tests pasan.
  - Verificar que `explorer.py` importa sin errores en entorno sin Windows (usando mocks para `win32api`, `keyboard`, `PIL`).

## Notas

- Las tareas marcadas con `*` son opcionales y pueden omitirse para un MVP más rápido
- Los property tests usan `hypothesis`; instalar con `pip install hypothesis pytest`
- El archivo de tests debe crearse en `tests/test_properties.py`
- Las funciones puras extraídas no deben romper la lógica existente; los handlers las llaman internamente
