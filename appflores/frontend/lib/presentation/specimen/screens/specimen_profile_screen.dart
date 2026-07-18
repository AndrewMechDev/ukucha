import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import '../../widgets/glass_card.dart';
import '../providers/specimen_provider.dart';

class SpecimenProfileScreen extends ConsumerWidget {
  final String specimenId;
  const SpecimenProfileScreen({super.key, required this.specimenId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final specimen = ref.watch(specimenProvider(specimenId));
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: Text(specimen.name),
        actions: const [
          Padding(
            padding: EdgeInsets.all(16.0),
            child: Icon(Icons.nfc, color: Colors.green), // Simula NFC validado
          )
        ],
      ),
      body: Stack(
        children: [
          // Fondo base decorativo
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  theme.scaffoldBackgroundColor,
                  theme.colorScheme.surface,
                ],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
          ),
          
          Column(
            children: [
              // Canvas 3D (Ocupa la mitad superior)
              Expanded(
                flex: 5,
                child: Container(
                  width: double.infinity,
                  margin: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(24),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.05),
                        blurRadius: 10,
                        offset: const Offset(0, 5),
                      )
                    ],
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(24),
                    child: ModelViewer(
                      src: specimen.glbUrl,
                      alt: 'Modelo 3D del Ejemplar',
                      ar: true, // Soporte Realidad Aumentada si está disponible
                      autoRotate: true,
                      cameraControls: true,
                      backgroundColor: const Color(0xFFF9F6F0), // Crema
                      disableZoom: false,
                    ),
                  ),
                ),
              ),
              
              // Datos Morfológicos (Glassmorphism)
              Expanded(
                flex: 4,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0),
                  child: ListView(
                    children: [
                      GlassCard(
                        height: 120,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'Biometría y Morfología',
                              style: theme.textTheme.headlineSmall,
                            ),
                            const SizedBox(height: 8),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                _DataColumn('Peso', '${specimen.weightKg} kg'),
                                _DataColumn('Altura', '${specimen.heightCm} cm'),
                                _DataColumn('Línea', specimen.geneticLine),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      GlassCard(
                        height: 100,
                        child: Row(
                          children: [
                            Icon(Icons.verified, color: theme.colorScheme.primary, size: 40),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text('Autenticidad Verificada', style: theme.textTheme.bodyLarge?.copyWith(fontWeight: FontWeight.bold)),
                                  Text('Tag NTAG213 SUN Valido', style: theme.textTheme.bodyMedium),
                                ],
                              ),
                            )
                          ],
                        ),
                      ),
                      const SizedBox(height: 24), // Margen inferior
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DataColumn extends StatelessWidget {
  final String label;
  final String value;

  const _DataColumn(this.label, this.value);

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 12)),
        const SizedBox(height: 4),
        Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
      ],
    );
  }
}
