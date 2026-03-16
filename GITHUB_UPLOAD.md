# Instrucciones para Subir a GitHub

## 📋 Checklist Previo

- [x] README.md actualizado
- [x] CHANGELOG.md actualizado
- [x] NEWS.md creado
- [x] RELEASE_NOTES.md creado
- [x] .gitignore configurado
- [x] .env no incluido (protegido en .gitignore)
- [x] __pycache__ no incluido (protegido en .gitignore)

---

## 🚀 Pasos para Subir a GitHub

### 1. Verificar el estado de Git

```bash
git status
```

Deberías ver los archivos nuevos/modificados:
- `README.md` (modificado)
- `CHANGELOG.md` (modificado)
- `NEWS.md` (nuevo)
- `RELEASE_NOTES.md` (nuevo)

### 2. Agregar los cambios

```bash
git add README.md CHANGELOG.md NEWS.md RELEASE_NOTES.md
```

O agregar todos los cambios:

```bash
git add .
```

### 3. Verificar los cambios a subir

```bash
git diff --cached
```

### 4. Hacer commit

```bash
git commit -m "docs: actualizar documentación para v1.2

- README.md: información completa y actualizada
- CHANGELOG.md: historial mejorado
- NEWS.md: novedades de la versión
- RELEASE_NOTES.md: notas técnicas de la versión"
```

### 5. Subir a GitHub

```bash
git push origin main
```

Si es la primera vez:

```bash
git push -u origin main
```

---

## 📝 Mensaje de Commit Recomendado

```
docs: actualizar documentación para v1.2

- README.md: información completa y actualizada con arquitectura, requisitos y guía de instalación
- CHANGELOG.md: historial mejorado con descripción de cambios
- NEWS.md: novedades y mejoras de la versión
- RELEASE_NOTES.md: notas técnicas, cambios de API y guía de actualización

Cambios principales:
- Correcciones críticas de estabilidad (HTTP 500, timeout de gunicorn, threads duplicados)
- Gestor de actualizaciones automáticas integrado con GitHub
- Nuevos comandos del bot (/help, /version, /key, /download)
- Interfaz web rediseñada con onboarding
- Mejoras de seguridad (bloqueo de plataformas, cookies seguras)
```

---

## 🏷️ Crear un Release en GitHub (Opcional pero Recomendado)

### 1. Ir a GitHub y crear un nuevo release

```
https://github.com/JesusQuijada34/ExplorerFrame/releases/new
```

### 2. Configurar el release

- **Tag version:** `v1.2-26.03-18.22`
- **Release title:** `ExplorerFrame v1.2 — Estabilidad y Actualizaciones Automáticas`
- **Description:** Copiar el contenido de `RELEASE_NOTES.md`

### 3. Adjuntar archivos (si aplica)

- `EF.zip` (ExplorerFrame.exe + Winverm.exe compilados)

### 4. Publicar

Hacer click en "Publish release"

---

## ✅ Verificación Post-Upload

Después de subir, verifica:

1. **GitHub muestra los cambios:**
   ```
   https://github.com/JesusQuijada34/ExplorerFrame/commits/main
   ```

2. **Los archivos están visibles:**
   - README.md
   - CHANGELOG.md
   - NEWS.md
   - RELEASE_NOTES.md

3. **El .env no está subido:**
   ```bash
   git ls-files | grep .env
   # No debería mostrar nada
   ```

4. **Los archivos de sesión no están subidos:**
   ```bash
   git ls-files | grep .flask_sessions
   # No debería mostrar nada
   ```

---

## 🔄 Próximas Actualizaciones

Para futuras versiones, repite estos pasos:

1. Actualizar `details.xml` con la nueva versión
2. Actualizar `CHANGELOG.md` con los cambios
3. Crear/actualizar `NEWS.md` si hay cambios significativos
4. Actualizar `RELEASE_NOTES.md` si es una versión mayor
5. Hacer commit y push
6. Crear un release en GitHub

---

## 📞 Notas Importantes

- **Nunca subas `.env`** — Contiene tokens y credenciales sensibles
- **Nunca subas `__pycache__`** — Se regenera automáticamente
- **Nunca subas `.flask_sessions`** — Contiene sesiones de usuarios activos
- **Nunca subas `ExplorerFrame.exe`** — Es muy grande, usa releases de GitHub

---

**Última actualización:** 16 de marzo de 2026
