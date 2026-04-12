# Frontend Runtime Harness

A reproducible runtime harness for external React/Tailwind projects. This pack defines how to preview a generated site, capture browser evidence, and store QA artifacts without turning this repo into a frontend runtime.

---

## Purpose

Use the target project's own package scripts and local server. The harness lives in process and documentation, not in a detached service inside `bazzite-laptop`.

This harness must produce:

1. A repeatable preview command
2. A stable local URL
3. A browser evidence bundle with breakpoint screenshots
4. Command-output artifacts aligned with the P63 QA layer

---

## Runtime Targets

Pick the preview path that matches the external project.

### Vite

```bash
npm install
npm run dev -- --host 127.0.0.1 --port 4173
```

Preferred for active iteration:

- URL: `http://127.0.0.1:4173`
- Keep the terminal output for the evidence bundle

For production-like preview:

```bash
npm run build
npm run preview -- --host 127.0.0.1 --port 4173
```

### Next.js

Development preview:

```bash
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Production preview:

```bash
npm run build
npm run start -- --hostname 127.0.0.1 --port 3000
```

### Static Site or Astro-Style Output

```bash
npm install
npm run build
npx serve dist -l 4173
```

If the target project already defines a preview script, prefer that over ad hoc server commands.

---

## Browser Evidence Loop

Every generated frontend project should follow this loop before closeout:

1. Start the preview server on `127.0.0.1`
2. Capture the command used to launch the preview
3. Verify the main route loads without obvious console or network failures
4. Capture screenshots at mobile, tablet, and desktop breakpoints
5. Capture one reduced-motion screenshot for a key animated view
6. Run the QA checklists from the P63 validation layer
7. Save outputs into a stable evidence bundle inside the target project

Do not mark work complete from static review alone. Runtime preview and browser evidence are required.

---

## Breakpoint Matrix

Use these widths unless the target project already defines a stricter device matrix:

| Capture | Width | Purpose |
|---------|-------|---------|
| Mobile | 375px | Primary narrow layout proof |
| Tablet | 768px | Intermediate navigation/layout proof |
| Desktop | 1280px | Main marketing or app layout proof |
| Reduced Motion | 1280px | Motion fallback proof |

Add route-specific captures for dashboards, forms, pricing, or any page with meaningful state changes.

---

## Evidence Bundle Format

Create the bundle inside the target project, not this repo.

Recommended path:

```text
qa/browser-evidence/YYYY-MM-DD-phase-name/
```

Recommended contents:

```text
qa/
  browser-evidence/
    2026-04-12-p65-runtime-harness/
      checklist.md
      notes.md
      manifest.json
      commands/
        install.txt
        preview.txt
        lint.txt
        typecheck.txt
        test.txt
        build.txt
        a11y.txt
      screenshots/
        mobile-home.png
        tablet-home.png
        desktop-home.png
        reduced-motion-home.png
```

### `manifest.json`

Use a small manifest so the evidence bundle is machine-readable:

```json
{
  "project": "example-site",
  "preview_url": "http://127.0.0.1:4173",
  "framework": "vite",
  "captured_at": "2026-04-12T13:30:00Z",
  "breakpoints": ["375", "768", "1280"],
  "reduced_motion": true,
  "routes": ["/"],
  "artifacts": {
    "checklist": "checklist.md",
    "commands": "commands/",
    "screenshots": "screenshots/"
  }
}
```

---

## QA Alignment

The runtime harness must point back to the existing QA layer:

- Responsive checks: `docs/patterns/frontend/responsive-qa-checklist.md`
- Accessibility checks: `docs/patterns/frontend/accessibility-qa-checklist.md`
- Motion checks: `docs/patterns/frontend/motion-sanity-review.md`
- Visual consistency: `docs/patterns/frontend/visual-consistency-review.md`
- Evidence workflow: `docs/patterns/frontend/qa-evidence-workflow.md`

The new requirement is that these artifacts come from a live browser preview, not only from code inspection.

---

## Operator Notes

- Bind previews to `127.0.0.1`, not `0.0.0.0`, unless the target project explicitly requires broader access.
- Reuse the target project's own scripts before inventing wrappers.
- Keep screenshot filenames stable so evidence can be compared across revisions.
- If the page has significant animation, capture both normal and reduced-motion states.
