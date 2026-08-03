# 33. UI Accessibility and Privacy Controls

## 33.1 Purpose

This control set reduces avoidable location, persistence, status, injection, motion, and assistive-technology risks in the browser interface. It does not constitute a complete WCAG audit, privacy certification, or clinical usability approval.

## 33.2 Location Safety

The country selector defaults to `Select country` with an empty value. It no longer assumes Pakistan or any other jurisdiction from the developer, browser, language, network, or device.

If the user does not explicitly select a country, the API omits `country_code`. The orchestrator then fails closed before detector processing and returns the bounded unavailable response.

The language selector defaults to generic English rather than treating language as proof of location.

## 33.3 Status Isolation

Health and readiness requests use independent settled results:

1. a readiness failure does not falsely mark the API process offline;
2. a health failure does not claim readiness state is known;
3. status controls always leave the disabled checking state;
4. public labels remain bounded to online, offline, ready, locked, unavailable, unknown, policy version, and documented reasons.

## 33.4 Assistive Technology

1. Major page regions use header, main, aside, and footer semantics.
2. Every select, textarea, and button has a wrapping label, explicit label, visible text, or accessible name.
3. The conversation feed is a polite live region.
4. A dynamic emergency route becomes an assertive `role="alert"` message.
5. Form and feed expose `aria-busy` during requests.
6. The message control references both privacy guidance and the character count.
7. Focus-visible styles remain explicit.
8. Reduced-motion preference changes scripted scrolling to immediate movement and suppresses CSS animation duration.

## 33.5 Browser Privacy

1. The form and message field disable autocomplete hints.
2. The message field disables autocorrect and spellcheck hints to reduce accidental third-party processing.
3. The UI uses no local storage, session storage, cookies, analytics, or conversation persistence.
4. The footer states the narrow fact that this build has no conversation persistence; it does not claim that network or process memory never handles a request.
5. The UI still warns against names, contact details, and medical record numbers.

Browser settings and extensions may ignore hints. These attributes reduce exposure but are not a privacy guarantee.

## 33.6 DOM and CSP Controls

1. Dynamic API fields are inserted with `textContent`.
2. `innerHTML`, `outerHTML`, `insertAdjacentHTML`, inline scripts, inline styles, and event-handler attributes are prohibited by regression tests.
3. Script and style assets remain same-origin under the restrictive Content Security Policy.
4. External source links accept only parsed HTTP or HTTPS URLs and open with `noreferrer noopener`.

## 33.7 Responsive Evidence

The UI defines desktop, single-workspace tablet, compact tablet/mobile, and narrow-mobile breakpoints. Conversation title and selectors now stack at 1050 pixels, before their combined intrinsic width can overflow. Selectors switch from two columns to one below 460 pixels.

Headless browser inspection verified the desktop and 780-pixel tablet layouts after the breakpoint fix. Static regressions preserve the breakpoint and responsive grid rules.

## 33.8 Automated Evidence

Tests verify:

1. unique element IDs;
2. accessible names for controls;
3. required landmarks;
4. no inline execution or event attributes;
5. same-origin asset URLs;
6. sensitive-field persistence hints;
7. empty default country;
8. absence of unsafe HTML and browser storage APIs;
9. assertive emergency notification;
10. focus, reduced-motion, and tablet-grid CSS.

## 33.9 Remaining Work

1. Automated browser accessibility audit against the running application.
2. Keyboard-only and screen-reader testing on supported platforms.
3. Zoom, text-spacing, contrast, forced-colors, and high-contrast verification.
4. Human comprehension review of emergency and limitation wording.
5. Localized reading-order, directionality, and translated copy review.
6. End-to-end interaction tests for unavailable and approved synthetic emergency responses.
