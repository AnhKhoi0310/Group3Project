# UI/UX Standards

For developers and AI coding tools building ReviewLens screens. Story S1-002. The goal is that two people building different pages produce one recognizable product.

## Navigation

The app uses one **top navigation bar** on every signed-in page: product name on the left, then Targets, with account and logout on the right. Don't add sidebars or per-page navigation patterns.

| Screen | Route |
|---|---|
| Login and register (Firebase) | `/login` |
| Targets list | `/targets` |
| Create target | `/targets/new` |
| Analysis Workspace | `/targets/:targetId` |

## Page layout

Desktop first, and usable on tablet and phone. Page content sits in `max-w-6xl mx-auto px-6 py-8`. Each page has exactly one `h1`, with the primary action at its top right.

The Analysis Workspace is the main screen. Its header always shows the target name, platform, and source URL, so the user never has to guess which target is active. Ingestion state, the ingest action, and the review preview all live on this page.

## Forms

- Every input has a visible `<label>`. Placeholders don't replace labels.
- Validate on submit. The backend is authoritative, so show its `fieldErrors` too.
- Show errors directly under the field in `text-sm text-red-700`, and keep what the user typed.
- A failed submission creates nothing. On success, go to the new target's workspace with a confirmation.

## Errors

Write errors in user terms and say what to do next.

| Category | Example |
|---|---|
| Validation | "Enter a valid Google Maps link." |
| Authentication | "Your session ended. Please log in again." |
| Authorization or not found | "We couldn't find that target. It may not exist or you may not have access." |
| Ingestion | "We couldn't reach the review source. Try again in a few minutes." |
| Unexpected | "Something went wrong on our side. Please try again." |

Never display stack traces, database errors, provider text, or raw status codes.

## Loading and ingestion states

Any wait over a moment shows a visible indicator, and the triggering button is disabled while it runs.

The workspace shows one clear status badge per state:

| State | Badge color | Text |
|---|---|---|
| No ingestion yet | slate | Not started |
| Processing | blue | Collecting reviews |
| Succeeded | green | Reviews collected, with ingested and rejected counts |
| Failed | red | Collection failed, with the reason and next step |

A failed run still shows previously collected reviews.

## Buttons and actions

- Primary: `bg-indigo-600 text-white hover:bg-indigo-700`, at most one per view.
- Secondary: white with `border-slate-300`.
- Destructive: red, and requires confirmation.
- Labels start with a verb: "Create target", "Collect reviews".

## Spacing and typography

Use Tailwind's default scale and system font. Page title `text-2xl font-semibold`, section title `text-lg font-semibold`, body `text-base`, secondary text `text-sm text-slate-600`. Page background `bg-slate-50`, panels `bg-white border border-slate-200 rounded-lg p-6`. Stack sections with `space-y-6`.

## Reusable components

Build these once in `src/components/` and reuse them: `Button`, `TextField`, `Panel`, `StatusBadge`, `ErrorMessage`, `LoadingIndicator`, `EmptyState`. Check for an existing component before creating a new one.

## Accessibility

Use semantic elements, keep every action keyboard reachable with a visible focus state, and give errors `role="alert"`. Status must not rely on color alone.
