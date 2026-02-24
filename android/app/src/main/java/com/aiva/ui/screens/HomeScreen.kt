package com.aiva.ui.screens

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.camera.view.PreviewView
import com.aiva.feature.vision.VisionViewModel
import com.aiva.ui.theme.*

@Composable
fun HomeScreen(
    viewModel: VisionViewModel,
    onSettingsClick: () -> Unit
) {
    val uiState by viewModel.uiState.collectAsState()
    val lifecycleOwner = LocalLifecycleOwner.current

    // Infinite pulsing animation when active
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseScale by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = if (uiState.isStreaming) 1.2f else 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseScale"
    )

    Box(modifier = Modifier.fillMaxSize()) {
        // Camera Preview Layer
        AndroidView(
            factory = { ctx ->
                val previewView = PreviewView(ctx)
                previewView.scaleType = PreviewView.ScaleType.FILL_CENTER
                viewModel.setSurfaceProvider(previewView.surfaceProvider)
                previewView
            },
            modifier = Modifier.fillMaxSize()
        )

        // UI Overlay Layer
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.5f))
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
        // Top Bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(vertical = 12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "AIVA",
                style = Typography.displaySmall.copy(fontWeight = FontWeight.Bold),
                color = HighContrastText
            )
            
            // Settings Button
            IconButton(
                onClick = onSettingsClick,
                modifier = Modifier
                    .size(48.dp)
                    .background(Color(0xFF222222), CircleShape)
            ) {
                Icon(
                    imageVector = Icons.Default.Settings,
                    contentDescription = "Settings",
                    tint = HighContrastText,
                    modifier = Modifier.size(28.dp)
                )
            }
        }

        Spacer(modifier = Modifier.weight(0.2f))

        // Connection Status Badge
        val statusColor = when (uiState.connectionState) {
            "CONNECTED" -> Green
            "CONNECTING" -> Yellow
            else -> Red
        }
        
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(16.dp))
                .background(statusColor.copy(alpha = 0.2f))
                .padding(horizontal = 16.dp, vertical = 8.dp)
        ) {
            Text(
                text = uiState.connectionState,
                style = Typography.labelLarge.copy(fontWeight = FontWeight.Bold),
                color = statusColor
            )
        }
        
        // Telemetry Dashboard (RTT, Frames, Drops)
        if (uiState.connectionState == "CONNECTED") {
            Spacer(modifier = Modifier.height(16.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                TelemetryPill("RTT", "${uiState.latencyMs}ms", if (uiState.latencyMs < 100) Green else if (uiState.latencyMs < 300) Yellow else Red)
                TelemetryPill("FRAME", "${uiState.frameId}", Color.Gray)
                TelemetryPill("DROPS", "${uiState.droppedFrames}", if (uiState.droppedFrames == 0) Green else Red)
            }
        }

        Spacer(modifier = Modifier.weight(0.3f))

        // Main Toggle Button with Pulsing Ring
        Box(
            contentAlignment = Alignment.Center,
            modifier = Modifier.size(300.dp)
        ) {
            // Pulsing Ring
            if (uiState.isStreaming) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .scale(pulseScale)
                        .background(Green.copy(alpha = 0.2f), CircleShape)
                )
                Box(
                    modifier = Modifier
                        .fillMaxSize(0.85f)
                        .scale(pulseScale * 1.05f)
                        .background(Green.copy(alpha = 0.4f), CircleShape)
                )
            }

            // Core Button
            Button(
                onClick = { viewModel.toggleStreaming(lifecycleOwner) },
                modifier = Modifier.fillMaxSize(0.7f),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (uiState.isStreaming) Green else HighContrastAction,
                    contentColor = Black
                ),
                shape = CircleShape,
                elevation = ButtonDefaults.buttonElevation(
                    defaultElevation = 8.dp,
                    pressedElevation = 2.dp
                )
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center
                ) {
                    Text(
                        text = if (uiState.isStreaming) "SCANNING" else "START",
                        style = Typography.headlineMedium.copy(fontWeight = FontWeight.ExtraBold),
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = if (uiState.isStreaming) "Tap to Pause" else "Tap to Listen",
                        style = Typography.bodyLarge,
                        textAlign = TextAlign.Center
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(32.dp))

        // Push To Talk Button
        val micColor = if (uiState.isMicRecording) Red else Color.DarkGray
        val micLabel = if (uiState.isMicRecording) "RECORDING..." else "HOLD TO SPEAK"
        
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier
                    .size(80.dp)
                    .clip(CircleShape)
                    .background(micColor)
                    .pointerInput(Unit) {
                        detectTapGestures(
                            onPress = {
                                viewModel.startVoiceCommand()
                                tryAwaitRelease()
                                viewModel.stopVoiceCommand()
                            }
                        )
                    },
                contentAlignment = Alignment.Center
            ) {
                if (uiState.isMicRecording) {
                    // Pulsing effect for mic
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .scale(pulseScale)
                            .background(Red.copy(alpha = 0.5f), CircleShape)
                    )
                }
                Icon(
                    imageVector = Icons.Default.PlayArrow,
                    contentDescription = "Push To Talk",
                    modifier = Modifier.size(40.dp),
                    tint = White
                )
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = micLabel,
                style = Typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                color = micColor
            )
        }

        Spacer(modifier = Modifier.weight(1f))
        
        // Warnings Banner
        if (uiState.warningLevel != "NONE" && uiState.lastAction.isNotBlank()) {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = Yellow,
                    contentColor = Black
                ),
                elevation = CardDefaults.cardElevation(defaultElevation = 6.dp),
                shape = RoundedCornerShape(16.dp)
            ) {
                Row(
                    modifier = Modifier.padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.Warning,
                        contentDescription = "Warning Indicator",
                        modifier = Modifier.size(36.dp)
                    )
                    Spacer(modifier = Modifier.width(16.dp))
                    Text(
                        text = uiState.lastAction,
                        style = Typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                    )
                }
            }
        } else {
            // Reserve space so UI doesn't jump
            Spacer(modifier = Modifier.height(84.dp))
        }
    }
    }
}

@Composable
fun TelemetryPill(label: String, value: String, accentColor: Color) {
    Row(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFF1E1E1E))
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Colored dot
        Box(
            modifier = Modifier
                .size(8.dp)
                .background(accentColor, CircleShape)
        )
        Spacer(modifier = Modifier.width(6.dp))
        Column(horizontalAlignment = Alignment.Start) {
            Text(
                text = label,
                color = Color.Gray,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold
            )
            Text(
                text = value,
                color = White,
                fontSize = 12.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Medium
            )
        }
    }
}

