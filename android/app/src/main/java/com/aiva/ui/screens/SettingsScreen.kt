package com.aiva.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.unit.dp
import com.aiva.feature.vision.VisionViewModel
import com.aiva.ui.theme.*
import kotlinx.coroutines.flow.collectLatest

@Composable
fun SettingsScreen(
    viewModel: VisionViewModel,
    onBack: () -> Unit
) {
    // Local state for text field
    var urlText by remember { mutableStateOf(TextFieldValue("")) }
    
    // Load initial value from repo (hacky direct access or expose flow)
    // Since VM exposes connection logic, we should probably expose the current URL config flow.
    // For now, let's just default to empty and let user type, or better:
    // We need to know the current URL to show it.
    // VM doesn't expose it in UiState. Let's add it? 
    // Or just accept we type it new.
    
    // Better: Add `serverUrl` to UiState or expose flow.
    // Let's assume user knows what they are doing or types fresh. 
    // Actually, persistence means we want to see what is saved.
    // I will add `serverUrl` to UiState in next step if needed. 
    // For now, let's just make the field.

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(HighContrastBackground)
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "SETTINGS",
            style = Typography.headlineLarge,
            color = HighContrastText
        )
        
        Spacer(modifier = Modifier.height(32.dp))
        
        Text(
            text = "Server Connection",
            style = Typography.headlineSmall,
            color = HighContrastText,
            modifier = Modifier.align(Alignment.Start)
        )
        
        Spacer(modifier = Modifier.height(16.dp))

        OutlinedTextField(
            value = urlText,
            onValueChange = { urlText = it },
            label = { Text("WebSocket URL (ws://...)") },
            colors = TextFieldDefaults.colors(
                focusedContainerColor = Black,
                unfocusedContainerColor = Black,
                focusedTextColor = White,
                unfocusedTextColor = White,
                focusedLabelColor = Yellow,
                unfocusedLabelColor = Color.Gray,
                cursorColor = Yellow,
                focusedIndicatorColor = Yellow,
                unfocusedIndicatorColor = Color.Gray
            ),
            modifier = Modifier.fillMaxWidth()
        )
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Button(
            onClick = { 
                if (urlText.text.isNotBlank()) {
                    viewModel.saveServerUrl(urlText.text)
                    onBack()
                }
            },
            colors = ButtonDefaults.buttonColors(containerColor = HighContrastAction),
            modifier = Modifier.fillMaxWidth().height(56.dp)
        ) {
            Text("SAVE", color = Black, style = Typography.headlineSmall)
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        Button(
            onClick = onBack,
            colors = ButtonDefaults.buttonColors(containerColor = Color.Gray),
            modifier = Modifier.fillMaxWidth().height(56.dp)
        ) {
            Text("CANCEL", color = White, style = Typography.headlineSmall)
        }
    }
}
