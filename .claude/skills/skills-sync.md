# Skill: Skills Sync — Mantener las skills sincronizadas con el codigo

## Objetivo

Evitar que las skills en `.claude/skills/` queden desactualizadas respecto
al codigo real. Ya paso una vez (ver Contexto historico abajo): las skills
de deteccion se desviaron del codigo hasta requerir una auditoria completa.
Esta skill define CUANDO proponer una actualizacion de skills y COMO
hacerla — **nunca edita nada sin confirmacion explicita del usuario**.

## Disparadores — cuando PROPONER una actualizacion

- Se agrega, actualiza, o quita una dependencia en `requirements.txt`
- Se agrega un modulo/archivo nuevo que alguien necesitaria conocer para
  reconstruir el sistema (nueva clase, detector, servicio, endpoint, adapter)
- Cambia una constante, umbral, formato de paquete, o comportamiento que
  YA esta documentado en una skill existente (ej: un umbral de confianza,
  un color BGR, la forma de un dict de retorno)
- Se agregan o cambian variables de entorno (`.env` / `env.example`)
- Cambia `.gitignore` de forma que afecta que se versiona
- Termina una fase o feature grande (cierre de un plan multi-fase)

## Cuando NO disparar

- Cambios triviales de estilo/formato sin impacto en comportamiento
- Fixes de bugs que no alteran la interfaz publica ni las constantes
  documentadas
- Cambios dentro de `.claude/skills/` en si (evitar recursion)

## Protocolo — siempre preguntar antes de editar

1. Al detectar un disparador, resumir en 1-2 lineas QUE cambio (que se
   agrego/modifico/elimino).
2. Mapear que skill(s) se ven afectadas por tema — no adivinar, cruzar
   contra el codigo real:
   - Cambios en `server.py` → `ukucha/server.md`
   - Cambios en `detectors/fall_detector.py` o `webcam_fall.py` → `ukucha/fall-detector.md`
   - Cambios en `detectors/epp_detector.py` → `ukucha/epp-detector.md`
   - Cambios en `detectors/rescue_detector.py` → `ukucha/rescue-detector.md`
   - Cambios en `ukucha_detector.py`, arquitectura general, stack, hardware → `ukucha/sistema.md`
   - Cambios en `backend/` (pipeline WiFi+deteccion+WS+Supabase) → `ukucha/backend-conexion.md`
   - Cambios en convenciones de commits → `commits.md`
   - Modulo nuevo sin skill dueña → proponer crear una skill nueva, no
     forzarlo dentro de una existente
3. Preguntar explicitamente: "Detecte estos cambios: [...]. Afectan estas
   skills: [...]. ¿Las actualizo ahora?" — esperar confirmacion antes de
   tocar archivos.
4. Si confirma: editar quirurgicamente (Edit, nunca reescribir el archivo
   completo con Write salvo que sea una skill nueva) solo las secciones
   afectadas.
5. Verificar SIEMPRE contra el codigo fuente real antes de escribir —
   nunca confiar en memoria de la conversacion para constantes, firmas de
   funciones, o formatos de datos. Leer el archivo actual primero.

## Contexto historico

- Auditoria completa que motivo esta skill: commit `4b660ff` (2026-07-18) —
  revision detallada de las 5 skills de deteccion contra el codigo real,
  encontrando gaps en `server.py` (sin skill), divergencias no
  documentadas entre `webcam_fall.py` y `detectors/fall_detector.py`, y
  constantes/helpers sin listar.
- Esta skill se creo al cerrar `feature/conexion` (backend serial + WS +
  Supabase, 5 fases), como practica preventiva para que el proximo modulo
  grande no repita el mismo problema.

## Skills actuales del proyecto

| Skill | Cubre |
|---|---|
| `ukucha/sistema.md` | Arquitectura general, pipeline unificado, hardware, stack |
| `ukucha/fall-detector.md` | Deteccion de caidas (FallDetector + webcam_fall.py) |
| `ukucha/epp-detector.md` | EPP y clasificacion victima/rescatista |
| `ukucha/rescue-detector.md` | Entorno/escombros (DRespNeT) |
| `ukucha/server.md` | Backend FastAPI original (telemetria de gases) |
| `ukucha/backend-conexion.md` | Backend WiFi+deteccion+WS+Supabase (`backend/`) |
| `commits.md` | Convenciones de commits |
