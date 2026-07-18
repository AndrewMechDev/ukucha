import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'core/theme/app_theme.dart';
import 'presentation/specimen/screens/specimen_list_screen.dart';
import 'presentation/specimen/screens/specimen_profile_screen.dart';

import 'presentation/main_navigation_screen.dart';
import 'presentation/calendar/screens/calendar_screen.dart';

void main() {
  runApp(
    const ProviderScope(
      child: AppFloresMobile(),
    ),
  );
}

final _rootNavigatorKey = GlobalKey<NavigatorState>();
final _shellNavigatorKey = GlobalKey<NavigatorState>();

final _router = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: '/',
  routes: [
    ShellRoute(
      navigatorKey: _shellNavigatorKey,
      builder: (context, state, child) {
        return MainNavigationScreen(child: child);
      },
      routes: [
        GoRoute(
          path: '/',
          builder: (context, state) => const SpecimenListScreen(),
        ),
        GoRoute(
          path: '/calendar',
          builder: (context, state) => const CalendarScreen(),
        ),
      ],
    ),
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/toro/:id',
      builder: (context, state) {
        final id = state.pathParameters['id']!;
        return SpecimenProfileScreen(specimenId: id);
      },
    ),
  ],
);

class AppFloresMobile extends StatelessWidget {
  const AppFloresMobile({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'AppFlores - Ecosistema Digital',
      theme: AppTheme.lightTheme,
      routerConfig: _router,
      debugShowCheckedModeBanner: false,
    );
  }
}
