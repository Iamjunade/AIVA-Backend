package com.aiva.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import com.aiva.feature.vision.VisionViewModel

@Composable
fun DebugOverlay(viewModel: VisionViewModel) {
    val state by viewModel.uiState.collectAsState()
    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black) // Save battery, high contrast
    ) {
        Column(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(16.dp)
        ) {
            DebugText("STATUS: ${state.connectionState}", 
                if (state.connectionState == "CONNECTED") Color.Green else Color.Red)
            
            DebugText("RTT: ${state.latencyMs}ms")
            DebugText("FRAME ID: ${state.frameId}")
            DebugText("DROPS: ${state.droppedFrames}")
        }

        Column(
            modifier = Modifier
                .align(Alignment.Center)
                .padding(16.dp)
        ) {
            if (state.warningLevel != "NONE") {
                Text(
                    text = state.warningLevel,
                    color = if (state.warningLevel == "DANGER") Color.Red else Color.Yellow,
                    fontSize = 48.sp,
                    modifier = Modifier.align(Alignment.CenterHorizontally)
                )
                Text(
                    text = state.lastAction,
                    color = Color.White,
                    fontSize = 24.sp,
                    modifier = Modifier.align(Alignment.CenterHorizontally)
                )
            }
        }
        
        Text(
            text = "AIVA BETA v1.0",
            color = Color.Gray,
            fontSize = 12.sp,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(16.dp)
        )
    }
}

@Composable
fun DebugText(text: String, color: Color = Color.White) {
    Text(
        text = text,
        color = color,
        fontSize = 16.sp,
        modifier = Modifier.padding(vertical = 4.dp)
    )
}
