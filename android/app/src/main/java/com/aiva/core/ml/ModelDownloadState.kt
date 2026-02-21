package com.aiva.core.ml

/**
 * AIVA — Model Download State (Observable by UI)
 *
 * Sealed class representing the state of background model downloads.
 * Consumed by ViewModel/Composable for non-blocking, accessible progress UI.
 *
 * Usage:
 *     val downloadState: StateFlow<ModelDownloadState> = ...
 *     when (val state = downloadState.collectAsState().value) {
 *         is ModelDownloadState.Idle -> { /* Show "Download Models" button */ }
 *         is ModelDownloadState.Downloading -> { /* Show progress bar */ }
 *         is ModelDownloadState.Completed -> { /* Show checkmark */ }
 *         is ModelDownloadState.Failed -> { /* Show error + retry */ }
 *     }
 */
sealed class ModelDownloadState {

    /** No download in progress or requested. */
    data object Idle : ModelDownloadState()

    /**
     * Download in progress.
     * @param modelName Human-readable name of the model being downloaded
     * @param progressPercent Progress percentage (0-100)
     * @param bytesDownloaded Bytes downloaded so far
     * @param totalBytes Total bytes expected (-1 if unknown)
     */
    data class Downloading(
        val modelName: String,
        val progressPercent: Int,
        val bytesDownloaded: Long = 0,
        val totalBytes: Long = -1,
    ) : ModelDownloadState()

    /**
     * All models downloaded and verified.
     * @param modelCount Number of models successfully cached
     */
    data class Completed(
        val modelCount: Int
    ) : ModelDownloadState()

    /**
     * Download failed.
     * @param reason Human-readable error message
     * @param isRetryable Whether the user can retry the download
     */
    data class Failed(
        val reason: String,
        val isRetryable: Boolean = true,
    ) : ModelDownloadState()
}
