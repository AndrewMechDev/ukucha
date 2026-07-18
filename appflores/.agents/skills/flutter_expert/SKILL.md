---
name: flutter_expert
description: Te obliga a utilizar Clean Architecture, inyección de dependencias estricta y Riverpod en todos los desarrollos de Flutter para asegurar un nivel máximo de profesionalismo.
---

# Directrices de Desarrollo en Flutter

Cuando se te pida crear o modificar código en Flutter dentro de este proyecto, DEBES adherirte estrictamente a las siguientes reglas:

1. **Clean Architecture**: 
   - Estructura las capas en `core`, `domain`, `data`, y `presentation`.
   - Ninguna lógica de negocio debe residir en la capa `presentation`.
   - Usa repositorios abstractos (Interfaces/Clases Abstractas en Dart) en `domain` e impleméntalos en `data`.

2. **State Management (Riverpod)**:
   - Utiliza Riverpod V2 (generadores de código `@riverpod` si es posible o `NotifierProvider` base).
   - Prohibido el uso de `setState` o `StatefulWidget` para estados globales o complejos. Solo úsalo para animaciones puras locales.

3. **Inyección de Dependencias**:
   - Usa los proveedores de Riverpod para inyectar los repositorios en los casos de uso o controladores.

4. **UI y Diseño**:
   - Aplica principios de Glassmorphism si el diseño lo requiere, utilizando `BackdropFilter` con `ImageFilter.blur`.
   - Separa los componentes visuales en `widgets` dedicados. No hagas archivos con miles de líneas.

5. **Profesionalismo y Código Limpio**:
   - Tipado fuerte SIEMPRE. No utilices `dynamic` a menos que sea absolutamente inevitable (ej. parseo de JSON inestable).
   - Documenta las funciones y clases más importantes.
