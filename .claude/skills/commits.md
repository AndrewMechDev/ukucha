# Skill: Commits — Convenciones del proyecto

## Formato de commit

Usa **Conventional Commits** en español con esta estructura:

```
<tipo>(<alcance>): <descripcion corta>

<cuerpo opcional>
```

## Tipos permitidos

| Tipo | Uso |
|------|-----|
| `feat` | Nueva funcionalidad |
| `fix` | Correccion de bug |
| `refactor` | Cambio de codigo sin alterar comportamiento |
| `docs` | Documentacion |
| `style` | Formato, espacios, puntos y comas (sin cambio logico) |
| `test` | Agregar o corregir tests |
| `chore` | Tareas de mantenimiento, configs, dependencias |
| `perf` | Mejora de rendimiento |
| `ci` | Cambios en CI/CD |

## Alcances del proyecto

| Alcance | Archivos |
|---------|----------|
| `detector` | ukucha_detector.py, detectors/*.py, webcam_fall.py |
| `server` | server.py — backend FastAPI |
| `backend` | backend/ — pipeline WiFi+deteccion+WS+Supabase (hardware ESP32) |
| `config` | .gitignore, requirements.txt, configs |
| `skills` | .claude/skills/ (incluye ukucha/backend-conexion.md, skills-sync.md) |

## Reglas

1. **Descripcion en español**, imperativo, minusculas, sin punto final
2. **Maximo 72 caracteres** en la primera linea
3. **Un commit por cambio logico** — no mezclar feat + fix
4. **Cuerpo opcional**: explicar el POR QUE, no el QUE (el diff ya muestra el que)
5. **No incluir** Co-Authored-By ni atribuciones AI
6. **Breaking changes**: agregar `!` despues del tipo: `feat!(detector): cambiar api de scoring`

## Ejemplos

```
feat(detector): agregar senal 3D de torso con world landmarks

Reemplaza el angulo 2D por coordenadas 3D de MediaPipe para
eliminar falsos negativos causados por perspectiva de camara.
```

```
fix(detector): corregir orden de argumentos en angulo del torso

dy calculaba hombro-cadera en vez de cadera-hombro, produciendo
angulos de ~180 grados para personas paradas.
```

```
chore(config): agregar .gitignore con exclusiones de venv y pesos
```

## Flujo antes de commitear

1. `git status` — revisar que archivos cambiaron
2. `git diff` — verificar que no hay secretos ni archivos no deseados
3. Agregar archivos especificos (`git add <archivo>`) — NO usar `git add .`
4. Commit con mensaje siguiendo este formato
5. NO hacer push automaticamente — esperar confirmacion del usuario
