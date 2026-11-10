# AWS Cloud Classroom

English-only, frontend-only AWS introduction with English service names. Twelve concept cards, category/search filters, browser-local completion progress, two clickable request-flow simulations, and a six-question quiz with explanations. Official AWS sources are linked next to each topic; introductory documentation was checked on 9 November 2026. The complete interface and learning content were translated to English on 10 November 2026, preserving lesson IDs, quiz answers and browser-local progress. This independent educational project is not affiliated with AWS.

## Run

Open `index.html` or serve this directory with any static web server. Keep `index.html`, `style.css`, `data.js`, and `app.js` together. No build step, backend, API keys, AWS account, external font, analytics, SDK or runtime dependency is needed. No AWS resources are created. Lesson progress is stored only under `aws-classroom-v1` in browser localStorage; blocked storage does not prevent learning. Quiz scores are session-only.

## Verification

With Node 18+ in this directory: `npm install --ignore-scripts`, then `npm test`. jsdom is a test-only dependency, pinned to 26.1.0. Do not upload node_modules or development files to the public app folder.

Passed: English-only runtime text and HTML language; saved-progress compatibility; malformed and blocked storage; JavaScript syntax; unique lesson IDs; source domains; search/filter/empty results; progress toggling; architecture stepping, wraparound, direct selection, scenario reset and restart; all quiz answers; duplicate answer prevention; incorrect answer feedback; retry; progress reset cancel/confirm. Tests use a DOM simulator, not a real browser.

Visual/mobile browser QA has NOT passed: bundled Playwright Chromium was absent and installed Chromium failed to launch in the execution environment. CSS includes desktop/tablet/mobile layouts, but verify the rendered result on phone and desktop before public release. Check keyboard focus, English text rendering, no horizontal overflow, all interactive controls, refresh persistence, and source links.

## Repository and manual release

Repository: searchanalystsasikumartalks/my-first-project
Branch: test/under-construction-20261108
Package: apps/aws-cloud-classroom/
Existing hosting checkout identified by its configured workflow: repositories/github-transfer-test-20261108 under the hosting account home.

1. In cPanel Git Version Control, select the existing github-transfer-test-20261108 checkout. Verify it targets the repository and branch above. Use **Update from Remote**, then compare the displayed HEAD to the delivered commit. Stop for dirty/diverged checkouts; do not force-reset unrelated work.
2. Do NOT assume **Deploy HEAD Commit** publishes this app. At inspection, `.cpanel.yml` ran an isolated catalog-updater test only. This delivery intentionally leaves that hook, Application Studio manifest, existing apps, homepage, catalog and sitemap unchanged.
3. Follow the existing Application Studio/Master review and release approval process. This package does not create an application record, approval, or publication event. If that workflow cannot accept a standalone static package, obtain its supported import/release step rather than bypassing the gate.
4. For an owner-approved manual static release, use File Manager to create a new `aws-cloud-classroom` directory within the verified public `/appln/apps/` hosting directory, only if that folder does not already exist. Copy only the four runtime files from the checkout's `apps/aws-cloud-classroom/` into it. Do not overwrite another app, copy the repository root, or change deployment hooks.
5. After publication, open the site's `/appln/apps/aws-cloud-classroom/` route and test the app. This is a conditional route, not a verified live URL. Confirm the actual domain/document root and hosting mapping before using it. No live deployment or URL verification was performed by this task.

The demo architectures are simplified teaching examples, not production deployment blueprints. IAM, authentication, input validation, cost controls, resilience, observability and data protection require workload-specific design. An AWS Budget alert is not a hard spending cap. Never put AWS secrets in frontend code.
