# Offline Communication Cards

Standalone English frontend. Open index.html in a modern browser or serve this folder using `python -m http.server 8080`. No build step, account, backend, CDN, or deployment required.

## Privacy and limitations
Download and keep this entire app folder for local use. A hosted page is not guaranteed to work offline. Test opening your saved copy with airplane mode before relying on it. Speech depends on your browser and installed voice; it may fail or require connectivity. Remote voices may send card text to your browser’s speech provider. Avoid speaking sensitive text unless you trust the selected voice and provider. These cards do not contact emergency services.

JSON exports are unencrypted. Browser storage is not a backup, may be cleared, and is not shared across devices or origins. Use a trusted device. There is no import/restore UI; exports are readable records for reference, not automatically restorable app state. Print output depends on browser settings. Do not put these tools behind third-party analytics without revisiting privacy claims.

## Accessibility and SEO
Semantic sections, explicit labels, keyboard operability, visible focus, status announcements, responsive layout, print styles, local favicon, unique title/description and Open Graph metadata. Hosting URLs are unknown so no invented canonical or social image URL is included. This is not an accessibility certification.

## Verification
See TEST-REPORT.md. Cross-browser, assistive-technology and real-device manual checks remain recommended.
