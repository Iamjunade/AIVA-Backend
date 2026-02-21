package com.aiva.ui

import androidx.compose.runtime.Composable
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.aiva.feature.vision.VisionViewModel
import com.aiva.ui.screens.HomeScreen
import com.aiva.ui.screens.SettingsScreen

@Composable
fun AppNavigation(viewModel: VisionViewModel) {
    val navController = rememberNavController()
    
    NavHost(
        navController = navController,
        startDestination = "home"
    ) {
        composable("home") {
            HomeScreen(
                viewModel = viewModel,
                onSettingsClick = { navController.navigate("settings") }
            )
        }
        
        composable("settings") {
            SettingsScreen(
                viewModel = viewModel,
                onBack = { navController.popBackStack() }
            )
        }
    }
}
