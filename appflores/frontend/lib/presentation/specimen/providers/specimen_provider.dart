import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../domain/entities/specimen.dart';

// Lista de toros simulada para el Directorio
final specimenListProvider = Provider<List<Specimen>>((ref) {
  return [
    const Specimen(
      id: 'toro-001',
      name: 'Bravío (Semental)',
      weightKg: 850.5,
      heightCm: 175.0,
      geneticLine: 'Línea Tradicional C1',
      glbUrl: 'assets/model.glb',
    ),
    const Specimen(
      id: 'toro-002',
      name: 'Relámpago',
      weightKg: 790.0,
      heightCm: 168.0,
      geneticLine: 'Línea Moderna X',
      glbUrl: 'assets/model.glb',
    ),
  ];
});

// Proveedor para obtener un toro específico dado su ID
final specimenProvider = Provider.family<Specimen, String>((ref, id) {
  final list = ref.watch(specimenListProvider);
  return list.firstWhere((element) => element.id == id, orElse: () => list.first);
});
