import 'package:flutter/material.dart';
import '../../widgets/glass_card.dart';

class CalendarScreen extends StatelessWidget {
  const CalendarScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final events = [
      {'title': 'Gran Torneo de Verano', 'date': '15 Ago 2026', 'location': 'Plaza Central'},
      {'title': 'Exhibición de Sementales', 'date': '02 Sep 2026', 'location': 'Hacienda San Marcos'},
      {'title': 'Feria Tecnológica Ganadera', 'date': '20 Oct 2026', 'location': 'Predio Ferial'},
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Calendario de Eventos'),
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [theme.scaffoldBackgroundColor, theme.colorScheme.surface],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: ListView.builder(
          padding: const EdgeInsets.all(16.0),
          itemCount: events.length,
          itemBuilder: (context, index) {
            final event = events[index];
            return Padding(
              padding: const EdgeInsets.only(bottom: 16.0),
              child: GlassCard(
                height: 100,
                child: Row(
                  children: [
                    Icon(Icons.event, color: theme.colorScheme.primary, size: 40),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Text(
                            event['title']!,
                            style: theme.textTheme.headlineSmall?.copyWith(fontSize: 16),
                          ),
                          const SizedBox(height: 4),
                          Text('${event['date']} • ${event['location']}', style: theme.textTheme.bodyMedium),
                        ],
                      ),
                    )
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
