# 30. Medical Bot UI Scaffold

## 30.1 Purpose

The browser interface provides a visible, testable shell around the existing fail-closed API. It does not activate medical guidance or imply clinical readiness.

## 30.2 Routes and Assets

1. `GET /` serves the Medibot interface.
2. `GET /assets/medibot.css` serves the responsive visual system.
3. `GET /assets/medibot.js` connects the interface to the versioned API.
4. `GET /v1/health` supplies process status and application version.
5. `GET /v1/ready` supplies policy and medical-guidance readiness.
6. `POST /v1/messages` supplies the bounded response shown in the conversation.

The UI route is excluded from OpenAPI because the versioned API schema remains the machine contract.

## 30.3 Implemented Behavior

1. Desktop, tablet, and mobile layouts.
2. Live process, readiness, policy, and version indicators.
3. Message submission using the strict API request contract.
4. Rendering for safe response fields, limitations, next steps, sources, route, and request ID.
5. Sanitized API-error and network-error states.
6. Character limit and a warning against entering direct identifiers.
7. Persistent emergency notice that does not claim to assess severity.
8. DOM construction with `textContent` rather than untrusted HTML injection.
9. No local storage, analytics, cookies, or browser-side persistence.

## 30.4 Security Boundary

The Content Security Policy defaults to no external content and permits only same-origin API requests, scripts, styles, and form actions. Inline script and inline style execution remain blocked. Every UI and API response remains `no-store`, frame-denied, MIME-sniffing protected, and request-ID correlated.

Approved source links are restricted in the browser to HTTP and HTTPS protocols. All other source values render as text.

## 30.5 Current Limitations

1. Normal medical guidance remains unavailable and returns HTTP `503` by design.
2. Emergency responses require injected approved dependencies; the default runtime has none and remains locked.
3. The language selector changes the request locale but the locked response is currently English only.
4. There is no authentication, consent flow, conversation persistence, or user profile.
5. Accessibility has structural labels, focus states, reduced-motion handling, and responsive behavior, but still needs automated and human audit evidence.

## 30.6 Verification

Automated tests assert that the interface and assets are served, defensive headers remain active, and the CSP permits only the capabilities required by the same-origin application.

The wheel build must include the `medibot/static` files before a release artifact is accepted.
