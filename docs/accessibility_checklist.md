# AIVA — Play Store Accessibility Compliance Checklist
=========================================================

To prevent rejection during Google Play review, AIVA must adhere to strict accessibility standards.
Verify each item below before submission.

## 1. TalkBack Integration
- [ ] **Content Descriptions**: All valid `Image`, `Icon`, and `IconButton` composables have meaningful `contentDescription`.
    - *Good*: `contentDescription = "Start object detection"`
    - *Bad*: `contentDescription = "Button"` or `null`
- [ ] **State Announcements**: Custom toggles (e.g., "Mute Warnings") must announce their state change.
    - Use `Modifier.semantics { stateDescription = "Muted" }`.
- [ ] **Grouping**: Logical groups of text (e.g., "Person detected at 12 o'clock") should be grouped for single focus traversal.
    - Use `Modifier.semantics(mergeDescendants = true) { }` on parent rows/columns.

## 2. Focus & Navigation
- [ ] **Focus Order**: Ensure D-pad/keyboard navigation follows a logical flow (Top-Left → Bottom-Right).
- [ ] **Focus Indicators**: All focusable elements must have a visible highlight state.
    - Automatic in Material 3, but verify custom components.
- [ ] **Trap Avoidance**: Ensure focus doesn't get stuck in dialogs or overlays (back button must escape).

## 3. Visual Requirements
- [ ] **Touch Targets**: All interactive elements must be at least **48dp x 48dp**.
    - If icon is smaller, use `IconButton` which provides the padding, or `MinTouchTargetSize` modifier.
- [ ] **Contrast**: Text contrast ratio must be ≥ **4.5:1** (normal) or **3:1** (large).
    - *Key Danger*: Red warning text on black/dark backgrounds. Verify with Accessibility Scanner app.
- [ ] **No Color-Only Info**: Don't rely solely on red/green for status. Use icons or text labels (e.g., "Connected" vs "Disconnected").

## 4. Live Updates (Crucial for AIVA)
- [ ] **Live Regions**: Obstacle warnings must interrupt or overlay standard navigation announcements.
    - Use `LiveRegionMode.Polite` for status updates.
    - Use `LiveRegionMode.Assertive` for immediate danger warnings.
- [ ] **Toast/Snackbar**: Must be announced automatically by TalkBack.

## 5. Testing Tools
1. **Accessibility Scanner** (App): Run on all screens. Fix all "Touch Target" and "Contrast" warnings.
2. **Pre-Launch Report**: Check the "Accessibility" tab in Play Console after uploading test track build.
3. **Manual Test**: Enable TalkBack, close eyes, and try to navigate from "Launch" to "Start Detection" solely by audio.
