# ReviewLens AI – UI/UX Standards Context Document

**Story:** S1-002 · **Rules:** S1-BR-003, S1-BR-015, S1-BR-025 · **Audience:** every developer and AI coding tool touching the frontend

This document is the single source of truth for how ReviewLens looks and behaves. If you are building a page, form, or component and this document answers the question, follow it. If it does not, copy the closest existing pattern, then propose an addition to this document in your pull request.

**Stack assumptions:** React + TypeScript (Vite, React Router), Tailwind CSS, Firebase Authentication (managed identity), FastAPI backend with MySQL, Vitest + React Testing Library, ESLint + Prettier. Ingestion starts from the target's source URL through a server-side review provider; CSV/JSON import is a secondary recovery path only. Ingestion run states are processing, succeeded, and failed. All visual tokens below are expressed as Tailwind classes so they can be applied directly.

## 1. Product Principles

1. **One product, not a set of pages.** The core flow is *AnalysisTarget → Ingestion → (Sprint 2) Summary → Q&A*. Every screen exists to support that flow.
2. **The active target is always visible.** A user must never have to guess which AnalysisTarget they are looking at.
3. **State is never implied.** Ingestion state, loading, success, and failure are always shown explicitly with a label, not just a color.
4. **Errors speak user language.** No stack traces, provider messages, database text, or secrets in the UI (S1-BR-025).
5. **Desktop-first, usable everywhere.** Design for laptop widths first; nothing may become unusable on a tablet or phone.

## 2. Application Navigation (S1-BR-003)

**Pattern: top navigation bar, fixed for the whole app.** Do not introduce a second navigation paradigm (no sidebar on some pages, no hamburger-only on others).

### 2.1 Top bar contents (left to right)

| Zone        | Content                                               | Notes                                                              |
|-------------|-------------------------------------------------------|--------------------------------------------------------------------|
| Left        | ReviewLens logo/wordmark → links to /targets          | Always present                                                     |
| Center-left | **Targets** link, **+ New Target** button             | Targets link highlights when on any /targets* route               |
| Center      | **Active target chip** (target name + platform badge) | Shown only inside a target workspace; links back to that workspace |
| Right       | Account menu (user email/avatar → *Sign out*)         | Sign out must fully end the Firebase session                       |

### 2.2 Route map

| Route              | Screen                                            | Auth      |
|--------------------|---------------------------------------------------|-----------|
| /login             | Sign in / register                                | Public    |
| /targets           | AnalysisTarget list (default landing after login) | Protected |
| /targets/new       | Create AnalysisTarget                             | Protected |
| /targets/:targetId | Analysis Workspace                                | Protected |

### 2.3 Rules

- All routes except /login are wrapped in a single ProtectedRoute component. Unauthenticated visitors are redirected to /login; after sign-in they return to the page they originally requested.
- Route guards are UX only. The backend independently rejects unauthenticated and unauthorized requests (S1-BR-004, S1-BR-009).
- Navigating directly to another user's /targets/:targetId shows the **Not available** page (see §5.5), never partial data.
- Breadcrumbs are not used. The top bar plus the workspace header provide location context.
- Later-sprint destinations (Summary, Q&A) are added as sections *inside* the workspace (§3.3), not as new top-level nav items.

### 2.4 Authentication flow (Firebase)

- /login uses Firebase Authentication sign-in and registration. Password reset and credential handling stay with Firebase; do not build custom credential screens.
- An AuthProvider subscribes to Firebase onAuthStateChanged. Until the first auth state resolves, show the full-page loading screen (§6.1) so protected content never flashes.
- The API client attaches a fresh Firebase ID token as Authorization: Bearer <token> to every backend call. The UI never sends a user ID or owner ID.
- A 401 from the backend signs the user out locally and redirects to /login with "Your session has ended. Sign in to continue."
- **Sign out** calls Firebase signOut, clears cached target and review data from client state, and redirects to /login.
- Firebase error codes are mapped to friendly copy in one place (for example wrong password or unknown email: "That email or password isn't right. Try again."). Raw Firebase codes and messages are never shown.

## 3. Page Layout

### 3.1 Global shell

- Top bar: height h-16, white background, bottom border border-b border-slate-200, sticky (sticky top-0 z-40).
- Page background: bg-slate-50.
- Content container: mx-auto w-full max-w-6xl px-4 sm:px-6 lg:px-8 py-8.
- Forms and narrow screens (login, create target) use max-w-xl centered within the container.
- Every page starts with a **page header**: h1 title on the left, primary action (if any) on the right, optional one-line description under the title.

### 3.2 Content surfaces

- Group content in **cards**: rounded-xl border border-slate-200 bg-white p-6 shadow-sm.
- Do not nest cards inside cards. Use dividers (border-t border-slate-200) inside a card instead.
- Vertical rhythm between cards or sections: space-y-6.

### 3.3 Analysis Workspace layout (most important screen)

The workspace is the center of gravity of the product. Structure, top to bottom:

1. **Target context header card**
    - Target/entity name (text-2xl font-semibold)
    - Platform badge (e.g. *Google Maps*)
    - Source URL, truncated with ellipsis and a copy/open control
    - **Ingestion status badge** (see §6.2)
2. **Section tabs** under the header: Ingestion (Sprint 1). Sprint 2 adds Summary and Q&A as additional tabs in this same tab bar. Tabs are in-page (same route, ?tab= query param), so the context header never disappears.
3. **Active section content** in one or more cards.

The context header remains visible across all tabs. Switching targets reloads the whole workspace; no state from the prior target may remain on screen.

### 3.4 Target list layout

- Page header: *Your targets* + **New Target** primary button.
- A responsive grid of target cards (grid gap-4 sm:grid-cols-2 lg:grid-cols-3). Each card shows: target name, platform badge, truncated source URL, ingestion status badge, and created date. The whole card is one clickable link to the workspace.
- Empty state: centered card with a short explanation and a primary *Create your first target* button.

### 3.5 Responsive behavior

- Breakpoints follow Tailwind defaults (sm 640, md 768, lg 1024).
- Below md: top-bar links collapse into a menu button; the active-target chip stays visible; grids go to one column; tabs scroll horizontally if needed.
- Never allow horizontal page scrolling. Long URLs must truncate or wrap (truncate / break-all).

## 4. Typography and Spacing (S1-BR-015 supporting)

### 4.1 Typography

- Font: **Inter** (fallback ui-sans-serif, system-ui). Configure once in tailwind.config; never set fonts per component.

| Role                      | Classes                                |
|---------------------------|----------------------------------------|
| Page title (h1)           | text-3xl font-semibold text-slate-900  |
| Section / card title (h2) | text-xl font-semibold text-slate-900   |
| Sub-heading (h3)          | text-base font-semibold text-slate-900 |
| Body                      | text-base text-slate-700               |
| Secondary / helper text   | text-sm text-slate-500                 |
| Labels                    | text-sm font-medium text-slate-700     |
| Code / URLs / IDs         | font-mono text-sm                      |

- One h1 per page. Do not skip heading levels.
- Sentence case everywhere ("Create target", not "Create Target"). Exception: product and platform names.

### 4.2 Spacing

- Use the Tailwind 4px scale only. Allowed everyday values: 1, 2, 3, 4, 6, 8, 12. No arbitrary values (mt-[13px]).
- Inside cards: p-6 (p-4 on mobile). Between a label and its input: mb-1. Between form fields: space-y-5. Between buttons in a group: gap-3.
- Corner radius: rounded-lg for inputs and buttons, rounded-xl for cards, rounded-full for badges.

### 4.3 Color tokens

Define as Tailwind theme colors; components reference semantic names, not raw hex.

| Token   | Value                         | Use                                                 |
|---------|-------------------------------|-----------------------------------------------------|
| primary | indigo-600 (hover indigo-700) | Primary buttons, links, focus rings                 |
| neutral | slate scale                   | Text, borders, backgrounds                          |
| success | emerald-600 on emerald-50     | Succeeded states                                    |
| warning | amber-600 on amber-50         | Processing-with-caution, partial states (Sprint 2+) |
| danger  | red-600 on red-50             | Errors, destructive actions                         |
| info    | sky-600 on sky-50             | Neutral notices, "not yet started"                  |

Color is never the only signal: pair it with an icon and a text label. Maintain WCAG AA contrast (4.5:1 for body text).

## 5. Forms, Validation, and Error Presentation (S1-BR-015, S1-BR-025)

### 5.1 Form conventions

- One column, labels **above** inputs, never placeholder-as-label.
- Every input has a visible <label htmlFor>; required fields carry a red asterisk and are announced to screen readers via aria-required.
- Helper text sits below the input (text-sm text-slate-500) and gives an example, e.g. *Paste the Google Maps URL of the business*.
- Field order follows the user's mental model: Entity name → Platform → Source URL.
- **Platform** is fixed by team configuration for Sprint 1: render it as a read-only, pre-filled display (badge or disabled select) so the user sees which platform is supported.
- Submit button is last, left-aligned, with *Cancel* as a secondary action beside it.
- Enter submits the form. Use real <form> elements, type="url" where applicable, and correct autoComplete attributes.
- Trim whitespace on submit before sending to the backend.

### 5.2 Validation timing

- Client-side validation is a convenience. **The backend is authoritative** (S1-BR-015); the UI must display backend validation errors with the same presentation as client errors.
- Validate on blur for the first time, then on change; always validate on submit.
- On submit failure: do not clear the form, focus the first invalid field, and show a summary banner if more than one field is invalid.
- An invalid target is never created, and the UI must not show it in the list or navigate away.

### 5.3 Field error presentation

- Red border (border-red-500) + error icon + message directly under the field in text-sm text-red-600.
- Link the message with aria-describedby and set aria-invalid="true".
- Messages say what is wrong and how to fix it:

| Condition                    | Message                                                                                        |
|------------------------------|------------------------------------------------------------------------------------------------|
| Missing name                 | "Enter a name for the business or product you want to analyze."                                |
| Missing URL                  | "Enter the review page URL."                                                                   |
| Malformed URL                | "That doesn't look like a valid web address. Include https:// and try again."                  |
| URL for a different platform | "This link isn't from Google Maps. Paste a Google Maps URL for the place you want to analyze." |

(Replace *Google Maps* with the team's chosen platform; keep the platform name in one config constant.)

Backend validation failures (HTTP 422) return fieldErrors keyed by field (name, source_url). The form maps each key to the matching field and renders it exactly like a client-side error (§5.3). If the backend rejects a field the form does not know, show the message in the summary banner.

### 5.4 Error message categories

Every failure the UI can show falls into exactly one category. Do not merge them into a generic "Something went wrong."

| Category                         | Presentation                         | Example copy                                                                               | Next step shown      |
|----------------------------------|--------------------------------------|--------------------------------------------------------------------------------------------|----------------------|
| Validation                       | Inline field errors (§5.3)           | See above                                                                                  | Fix the field        |
| Authentication / session expired | Redirect to /login with banner       | "Your session has ended. Sign in to continue."                                             | Sign in              |
| Authorization denied             | Full-page *Not available* state      | "We couldn't find that target, or you don't have access to it."                            | Back to your targets |
| Ingestion failure                | Error alert in the Ingestion section | "We couldn't collect reviews from this link. Check that the page is public and try again." | Retry / edit source  |
| Provider quota or timeout        | Error alert, distinct wording        | "The review service is busy right now. Try again in a few minutes."                        | Retry later          |
| Unexpected failure               | Error alert, no technical detail     | "Something went wrong on our side. Please try again."                                      | Retry                |

Rules:

- The authorization message must be identical whether the target does not exist or belongs to someone else (do not leak existence).
- Show a support/reference ID only if the backend supplies a safe correlation ID.
- Technical details (status codes, stack traces, provider text, Firebase error codes) go to console/server logs only in development, and never to the screen. Map backend error codes to copy in one place (src/lib/errorMessages.ts).

**Backend response to UI category.** The API returns one error shape: code, a user-safe message, and optional fieldErrors. The client maps it as follows; pages never branch on raw status codes.

| Backend signal                        | UI category                                         | Presentation                                                                                                 |
|---------------------------------------|-----------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| 422 + fieldErrors                     | Validation                                          | Inline field errors                                                                                          |
| 401                                   | Authentication / session                            | Redirect to /login with banner                                                                               |
| 404 on a target, its runs, or reviews | Authorization denied (also covers a missing target) | Full-page *Not available*                                                                                    |
| Run failure_category = invalid_source | Ingestion failure                                   | "We couldn't collect reviews from this link. Check that it's a public Google Maps place page and try again." |
| provider_timeout                      | Provider timeout                                    | "The review service took too long to respond. Try again in a moment."                                        |
| provider_quota                        | Provider quota                                      | "We've reached the review service's usage limit for now. Try again later."                                   |
| provider_unavailable                  | Provider unavailable                                | "We couldn't reach the review service. Try again later."                                                     |
| unexpected or 5xx                     | Unexpected failure                                  | "Something went wrong on our side. Please try again."                                                        |

Quota, timeout, and unreachable-service failures must read differently from each other and from an invalid-source failure.

### 5.5 Alerts, banners, and toasts

- **Inline alert** (role="alert" for errors, role="status" for info/success): used for results tied to a section, e.g. ingestion outcome. Persists until dismissed or superseded.
- **Toast**: used only for short confirmations of completed actions ("Target created"). Auto-dismiss after 5 s, bottom-right, one at a time. Never use toasts for errors that need action.
- **Full-page states**: Not available, Not found, and Unexpected error use one shared PageState component with icon, title, message, and one button.

## 6. Loading and Processing States

### 6.1 Loading patterns

| Situation                                  | Pattern                                                                           |
|--------------------------------------------|-----------------------------------------------------------------------------------|
| Initial page data (target list, workspace) | **Skeleton** placeholders matching the final layout (no layout shift)             |
| Button action in flight                    | Button shows spinner + progress label ("Creating…"), is disabled, keeps its width |
| Ingestion running                          | Status badge = *Processing* plus an inline progress card (§6.3)                   |
| Auth bootstrapping                         | Full-page centered spinner with the logo; never flash protected content           |

- Never show a blank screen. Never use a spinner for longer than ~10 s without extra text explaining what is happening.
- Disable the triggering control while a request is in flight to prevent duplicate submissions.

### 6.2 Ingestion status badges

One shared IngestionStatusBadge component is used on the list cards and in the workspace header. Do not re-implement it.

| State                       | Label              | Color             | Icon           |
|-----------------------------|--------------------|-------------------|----------------|
| No ingestion yet            | Not ingested       | info (sky)        | circle-dashed  |
| Started / processing        | Ingesting…         | warning (amber)   | spinner        |
| Succeeded                   | Ingested           | success (emerald) | check-circle   |
| Failed                      | Failed             | danger (red)      | x-circle       |
| Partial (only if supported) | Partially ingested | warning (amber)   | alert-triangle |

The badge is driven by the latest ingestion run returned by the API: no run means *Not ingested*; otherwise the run status (processing, succeeded, failed). A failed run also carries a failure_category, which selects the alert copy in §5.4.

### 6.3 Ingestion section content

- **Source panel:** target name, platform, source URL, and which target will receive the reviews.
- **Primary action:** *Ingest reviews* button. When data already exists it reads *Re-run ingestion* (only if re-ingestion is supported).
- **While processing:** card reading "Collecting reviews from <platform> for <target>…" with spinner. Ingest button disabled.
- **On success:** role="status" success alert: "Ingested <N> reviews for <target>." A compact list of a few representative reviews (rating + text excerpt) with a total count confirms persistence. Detailed analytics are Sprint 2 and must not be built early.
- **On failure:** error alert per §5.4. Previously ingested reviews remain displayed and are labeled as the previous data; the UI never implies they were replaced.
- **Supplementary import (if offered):** presented as a clearly secondary link/button ("Having trouble? Import a file instead") per S1-BR-027, never as the primary action.

**Success detail.** The success alert also reports rejected records when there are any: "Ingested 42 reviews for Joe's Pizza. 3 records were skipped because they had no review text or a valid rating." Skipped records are never counted as ingested.

**Running state.** If the backend runs ingestion in the background, the workspace polls GET /api/targets/{id}/ingestions/latest every 3 seconds while the status is processing and stops on succeeded, failed, or when the user leaves the page. If ingestion is synchronous, the button shows its progress state until the response returns.

**Import a file (secondary recovery path, only if built).** Shown as a ghost link below the primary action, never beside it as an equal button. It opens a dialog that accepts CSV or JSON, states when to use it ("Use this if the review service is unavailable or over its limit"), and reports the outcome with the same alerts and badge as URL ingestion. Imported reviews are labeled as imported, so the dataset's source is never misrepresented.

## 7. Buttons and Actions

| Variant      | Classes (base: inline-flex items-center justify-center rounded-lg px-4 py-2 text-sm font-medium focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2) | Use                                      |
|--------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| Primary      | bg-indigo-600 text-white hover:bg-indigo-700                                                                                                                                    | The single main action on a view         |
| Secondary    | bg-white text-slate-700 border border-slate-300 hover:bg-slate-50                                                                                                               | Cancel, back, alternative actions        |
| Danger       | bg-red-600 text-white hover:bg-red-700                                                                                                                                          | Destructive actions (delete, when added) |
| Ghost / link | text-indigo-600 hover:underline                                                                                                                                                 | Low-emphasis navigation                  |

Rules:

- **One primary button per view or card.**
- Button labels are verb-first and specific: "Create target", "Ingest reviews", "Sign out". Avoid "Submit", "OK", "Click here".
- Loading and disabled states per §6.1; disabled buttons use opacity-50 cursor-not-allowed and still explain why (tooltip or helper text) when non-obvious.
- Destructive actions always require a confirmation dialog naming the thing being deleted and stating consequences.
- Icon-only buttons need aria-label and a tooltip.
- Minimum target size 40×40 px for touch.

## 8. Reusable Component Expectations

Build once under src/components/ui/ (generic) and src/components/reviewlens/ (domain). Do not copy-paste markup between pages; if you need a variant, extend the shared component and update this document.

| Component           | Responsibility                                                   |
|---------------------|------------------------------------------------------------------|
| AppShell            | Top bar + page container; the only place the nav is rendered     |
| ProtectedRoute      | Auth gate + redirect-back behavior                               |
| PageHeader          | h1, description, primary action slot                             |
| Card                | Standard surface (§3.2)                                          |
| Button              | All variants, loading and disabled states                        |
| TextField           | Label, helper text, error, aria wiring                           |
| Alert               | Error / success / info / warning variants with correct ARIA role |
| Toast               | Transient confirmation (§5.5)                                    |
| Badge               | Generic pill; PlatformBadge and IngestionStatusBadge build on it |
| Skeleton            | Loading placeholders                                             |
| PageState           | Full-page empty, not-available, not-found, and error states      |
| ConfirmDialog       | Destructive-action confirmation                                  |
| TargetCard          | List-view representation of an AnalysisTarget                    |
| TargetContextHeader | Workspace header (name, platform, source, status)                |

Component rules:

- Typed props (TypeScript, no any); styling via Tailwind classes only (no inline styles, no per-component CSS files).
- Components are presentational. Data fetching lives in hooks/services (src/api/), so components can be tested with fixture props.
- All API calls go through one client module that attaches a fresh Firebase ID token, parses the backend error shape (`code`, `message`, `fieldErrors`), and maps errors to the §5.4 categories. Pages never build fetch calls or error strings by hand.
- Every shared component has at least one test covering its normal and error/disabled behavior (Vitest + React Testing Library).

## 9. Accessibility Baseline

- All functionality is reachable by keyboard with a visible focus ring; tab order follows visual order.
- Use semantic elements (button, a, nav, main, form, label) before ARIA.
- Dynamic results (validation summary, ingestion outcome) are announced via role="alert" / role="status".
- Do not convey meaning by color alone (§4.3).
- Dialogs trap focus, close on Esc, and return focus to the trigger.

## 10. Content and Tone

- Plain, calm, professional. Speak to the user as "you"; refer to the system as "ReviewLens" or "we" sparingly.
- Name the thing: "Ingested 42 reviews for Joe's Pizza" beats "Success".
- Always give a next step on errors (§5.4).
- Do not use the word *chatbot*, and do not use exclamation marks in error messages.

## 11. Pull Request UI Checklist

Copy this into any PR that touches the frontend.

- [ ] Uses AppShell, PageHeader, and Card rather than custom layout wrappers
- [ ] Active target (name + platform) is visible on any target-specific screen
- [ ] Forms follow §5.1; backend validation errors render the same way as client errors
- [ ] Errors map to a §5.4 category with approved copy; no raw technical text on screen
- [ ] Loading uses skeletons / button progress states (§6.1); no blank or frozen screens
- [ ] Status shown via IngestionStatusBadge, not custom markup
- [ ] One primary button; labels are verb-first; destructive actions confirm
- [ ] Only Tailwind scale values and semantic color tokens used
- [ ] Keyboard and screen-reader checks done (labels, focus, ARIA roles)
- [ ] Verified at desktop width and at a phone-width viewport
- [ ] Component/UI test added or updated and mentioned under *Test Evidence*

## 12. Out of Scope for Sprint 1

Do not design or build ahead: ingestion summary analytics and charts, Q&A interface, chat history, sentiment visualizations, organizations or team members, issue and improvement lists, alert rules, dark mode, PWA features, or account settings beyond sign-out. Reserve the workspace tab bar so Sprint 2 can add *Summary* and *Q&A* without changing navigation.

*This is a living document. Changes to conventions require a PR that updates this file and references the affecting story.*
