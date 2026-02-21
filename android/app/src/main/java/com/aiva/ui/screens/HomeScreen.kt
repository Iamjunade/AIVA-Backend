package com.aiva.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.aiva.feature.vision.VisionViewModel
import com.aiva.ui.theme.*

@Composable
fun HomeScreen(
    viewModel: VisionViewModel,
    onSettingsClick: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val lifecycleOwner = LocalLifecycleOwner.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(HighContrastBackground)
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Top Bar
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "AIVA",
                style = Typography.headlineLarge,
                color = HighContrastText
            )
            
            // Settings Button (Accessible Tap Target)
            Box(
                modifier = Modifier
                    .clickable(onClickLabel = "Open Settings") { onSettingsClick() }
                    .padding(16.dp)
            ) {
                Text(
                    text = "⚙️", 
                    style = Typography.headlineLarge,
                    color = HighContrastText
                )
            }
        }

        Spacer(modifier = Modifier.weight(0.5f))

        // Large Status/Action Display
        Text(
            text = if (uiState.isStreaming) "ACTIVE" else "READY",
            style = Typography.displayLarge,
            color = if (uiState.isStreaming) Green else Color.Gray,
            modifier = Modifier.padding(bottom = 24.dp)
        )

        // Main Toggle Button (Huge Touch Target)
        Button(
            onClick = { viewModel.toggleStreaming(lifecycleOwner) },
            modifier = Modifier
                .fillMaxWidth(0.9f)
                .aspectRatio(1f), // Square Button
            colors = ButtonDefaults.buttonColors(
                containerColor = if (uiState.isStreaming) HighContrastAction else Color.DarkGray,
                contentColor = Black
            ),
            shape = MaterialTheme.shapes.extraLarge
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = if (uiState.isStreaming) "STOP" else "START",
                    style = Typography.displayLarge
                )
                Text(
                    text = if (uiState.isStreaming) "Tap to pause" else "Tap to scan",
                    style = Typography.bodyLarge
                )
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        // Connection Status
        Text(
            text = "Network: ${uiState.connectionState}",
            style = Typography.headlineSmall,
            color = when (uiState.connectionState) {
                "CONNECTED" -> Green
                "CONNECTING" -> Yellow
                else -> Red
            },
            textAlign = TextAlign.Center
        )

        Spacer(modifier = Modifier.weight(1f))
        
        // Warnings (if any)
        if (uiState.warningLevel != "NONE") {
            Text(
                text = "⚠️ ${uiState.lastAction}",
                style = Typography.headlineLarge,
                color = Red,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Yellow)
                    .padding(8.dp)
            )
        }
    }
}
