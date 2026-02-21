package com.aiva.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

private val DarkColorScheme = darkColorScheme(
    primary = Yellow,
    secondary = Green,
    tertiary = Red,
    background = Black,
    surface = Black,
    onPrimary = Black,
    onSecondary = Black,
    onTertiary = White,
    onBackground = White,
    onSurface = White,
)

private val LightColorScheme = lightColorScheme(
    primary = Yellow,
    secondary = Green,
    tertiary = Red,
    background = Black, // Force Dark Mode look even in Light theme for contrast? 
                        // Actually, blind users might prefer inverted. 
                        // For now, consistent High Contrast Dark.
    surface = Black,
    onPrimary = Black,
    onSecondary = Black,
    onTertiary = White,
    onBackground = White,
    onSurface = White,
)

@Composable
fun AivaTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color is available on Android 12+
    dynamicColor: Boolean = false, // Disable dynamic color to enforce High Contrast
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme // Use Dark/High Contrast always? Let's respect system but default to High Contrast Dark.
    }
    
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.background.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = Typography,
        content = content
    )
}
