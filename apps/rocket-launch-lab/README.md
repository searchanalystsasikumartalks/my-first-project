# Rocket Launch Lab 1.0

A standalone static educational app. Keep index.html, style.css and app.js together. No build, backend, API key, account or database is needed. Serve from an ordinary static folder or open index.html locally.

Controls: lift strength, power duration, Earth/Moon gravity; Launch, Pause/Resume, Reset, playback speed and JSON experiment download. Some labels include Tamil; this is not a full Tamil translation.

This is a deliberately simplified constant-mass, vertical, constant-gravity model, without drag, fuel depletion, staging or orbit. It is not a real rocket design or launch tool. Physics uses analytic powered and unpowered motion and stops at ground contact. Lift strength is a multiple of Earth weight even when selecting Moon gravity.

Validation: JavaScript syntax and analytic physics tests passed, including no-lift, known Earth peak, gravity/duration comparison, burn-boundary continuity, landing and finite/nonnegative trajectory grid. Browser visual/interaction QA could not execute in the build environment because Chromium local socket creation was denied. Do not describe this as browser-tested or live deployed.

Scope: repository package only. Existing deployment hook, homepage, manifest, sitemap and other apps were not changed. Pulling this package is not proof of publication. The owner handles hosting/deployment separately.

Existing educational alternatives include NASA RocketModeler and Science Learning Hub Rocket Launch Challenge. This app is not claimed to be unique; search demand has not been measured.

Sources:
- https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/flight-of-a-water-rocket/
- https://www.sciencelearn.org.nz/embeds/rocket-launch-challenge
