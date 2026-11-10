# Use-First Food Queue

Standalone English frontend. No build, backend, accounts, external libraries, or API keys.

## Run
Run `python3 -m http.server 8080` in this directory and open http://localhost:8080. ES modules require HTTP; do not double-click index.html. Deploy these files to any static HTTPS host. No canonical URL is invented; add one after choosing a real public URL.

## Test
`npm test` runs pure-logic tests with Node 18+. Browser smoke coverage is documented in QA.md.

## Privacy and limits
Local storage is unencrypted and browser-specific; clearing site data removes records. Exports may contain your entries. No cloud sync or automatic backup. Check factual and safety details yourself.

## Accessibility
Semantic headings, labeled fields, visible focus indicators, live save status, keyboard buttons, responsive layout, reduced reliance on color. Manual assistive-technology testing remains recommended.
