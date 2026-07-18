import 'package:flutter/material.dart';

class AppTheme {
  // Colores principales (Crema/Claro)
  static const Color primaryCream = Color(0xFFF9F6F0);
  static const Color secondaryCream = Color(0xFFEFEBE1);
  static const Color accentTeal = Color(0xFF2A9D8F);
  static const Color textDark = Color(0xFF264653);
  static const Color textLight = Color(0xFF6B705C);

  static ThemeData get lightTheme {
    return ThemeData(
      brightness: Brightness.light,
      scaffoldBackgroundColor: primaryCream,
      colorScheme: const ColorScheme.light(
        primary: accentTeal,
        secondary: accentTeal,
        surface: secondaryCream,
        onSurface: textDark,
      ),
      fontFamily: 'Roboto', // Modern typography
      appBarTheme: const AppBarTheme(
        backgroundColor: primaryCream,
        elevation: 0,
        iconTheme: IconThemeData(color: textDark),
        titleTextStyle: TextStyle(
          color: textDark,
          fontSize: 20,
          fontWeight: FontWeight.bold,
        ),
      ),
      textTheme: const TextTheme(
        headlineSmall: TextStyle(color: textDark, fontWeight: FontWeight.w700),
        bodyLarge: TextStyle(color: textDark, fontSize: 16),
        bodyMedium: TextStyle(color: textLight, fontSize: 14),
      ),
    );
  }
}
