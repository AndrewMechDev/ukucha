---
name: aws_3d_expert
description: Directrices estrictas para el manejo, carga y visualización de modelos 3D (.glb) desde AWS CloudFront/S3 para optimizar métricas de rendimiento en móviles.
---

# Directrices de Integración 3D y AWS

Cuando trabajes con los modelos 3D y su conexión al backend/CDN, DEBES seguir estas reglas:

1. **Formatos**:
   - Utiliza siempre archivos `.glb` (binarios) en lugar de `.gltf` (json + binarios separados) para reducir los requests HTTP y el tamaño total.

2. **Políticas de AWS CloudFront**:
   - Las URLs de los modelos siempre deben servirse detrás de un CDN (CloudFront).
   - Asegúrate de indicar en los headers que el caché sea agresivo (`Cache-Control: public, max-age=31536000, immutable`).
   - El backend debe pre-firmar o servir las URLs optimizadas.

3. **Visualización en Flutter (`flutter_gl` / Visores)**:
   - Mantén los renders a 30 FPS. Si la malla es muy pesada, sugiere simplificar el poligonaje (LOD - Level of Detail).
   - Muestra siempre un loader o un skeleton (Shimmer) mientras se descarga el binario del modelo en el cliente.
   - Libera la memoria del contexto OpenGL cuando el widget del modelo se destruye para evitar memory leaks.
