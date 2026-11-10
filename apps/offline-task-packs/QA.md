# Verification

- Pure-logic tests: passed with Node 24 (`npm test`).
- JavaScript syntax checks: passed (`node --check` for each JS file).
- Browser smoke tests: prepared but NOT RUN successfully. Installed Chromium could not launch because the execution environment denies socket creation. An approved escalated launch had the same restriction.
- Visual, mobile viewport, keyboard, screen-reader, download, service worker, and browser persistence behavior therefore require real-browser verification. No screenshots are claimed.

## Manual acceptance checklist
1. Serve this directory over localhost or HTTPS; confirm no console errors.
2. At 390 px width, confirm no horizontal overflow and that labels/buttons remain readable.
3. Add meaningful entries, reload, and confirm persistence.
4. Export and inspect the downloaded file.
5. Test empty and whitespace entries, repeated actions, cancel on destructive confirmation, and keyboard-only operation.
6. Clear site storage or disable it and verify the app remains usable with an honest warning.
7. For Task Packs, restore valid and invalid JSON and test offline reload after cache preparation.
8. For Visit Brief, print and check the generated text; confirm unknown details stay labeled.
9. For Food Queue, test location filtering, entered-date ordering, removal and undo.
