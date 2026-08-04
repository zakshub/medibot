# 12. Change Log

## 2026-08-03

1. Created the `DOC` folder
2. Added the documentation index
3. Added numbered core documentation files
4. Added planning, status, risk, and handoff templates
5. Established a recommended folder structure for future project growth
6. Added the repository README, contribution rules, ignore policy, and execution roadmap
7. Added draft product requirements, safety boundaries, emergency behavior, and acceptance criteria
8. Added the medical-safety risk register and release evidence rules
9. Added data-governance, privacy, logging, retention, and processor controls
10. Added logical architecture, trust boundaries, dependencies, and safe failure behavior
11. Added draft API, error, audit, content, and policy data contracts
12. Added layered testing, safety evaluation, regression, and release evidence strategy
13. Added a typed FastAPI scaffold, strict request contract, fail-closed message endpoint, and automated API tests
14. Added GitHub Actions quality gates and a private security-reporting policy
15. Added transport-level request-size enforcement, sanitized 413 errors, and defensive response headers
16. Added response correlation IDs and bounded structured audit events without raw health content
17. Added strict startup validation for environment, request limits, policy versions, and production debug mode
18. Separated process liveness from policy-gated traffic readiness
19. Added dependency consistency, vulnerability auditing, and weekly update automation
20. Added a per-process message-rate backstop, sanitized 429 contract, and production abuse-control boundary
21. Added an injectable application factory and fixed false readiness from policy-only configuration
22. Added explicit OpenAPI error contracts and schema-regression tests
23. Migrated HTTP tests to async ASGI transport and removed deprecated TestClient usage
24. Added measured source-coverage reporting with a 90 percent CI regression floor
25. Added a non-root multi-stage container, liveness healthcheck, Docker CI build, and deployment boundaries
26. Added a hardened local Compose baseline and CI configuration validation
27. Added an operational runbook for startup, signals, incidents, safe logs, and rollback
28. Added pull-request and issue intake controls with explicit medical-safety and sensitive-data gates
29. Added repository ownership rules and an immutable release-evidence template
30. Added cross-platform one-command verification scripts and aligned CI to the Linux script
31. Disabled pytest's nonessential cache provider to avoid synced-drive cache races
32. Added explicit cross-platform line-ending policy for source, configuration, docs, and scripts
33. Added targeted ASGI tests for chunked overflow, middleware pass-through, header preservation, and limiter expiry
34. Added regression coverage proving malformed content length cannot bypass streamed body limits
35. Added the blocking product decision register and reviewed-content provenance contract
36. Extracted deterministic unavailable responses and added a fail-closed empty content repository
37. Added a deterministic reviewed-content reference repository with duplicate, locale, expiry, and latest-version controls
38. Added explicit application-factory content repository injection with a fail-closed default
39. Added versioned policy approval/effective-window contracts and a fail-closed policy repository
40. Added a fail-closed emergency resource registry contract with country, locale, approval, expiry, and duplicate-version controls
41. Added an emergency signal detection contract with fail-closed default behavior and synthetic keyword reference tests
42. Added an emergency response composer contract that requires both a possible emergency signal and an approved resource
43. Added a responsive safety-first medical bot UI with live API status, bounded message rendering, and same-origin CSP controls
44. Replaced the stale status tracker with evidence-based done and remaining estimates for each workstream
45. Extended the repository line-ending policy to browser HTML, CSS, and JavaScript assets
46. Added an active in-memory policy repository with deterministic effective-window selection
47. Added bounded emergency decision validation for route consistency, category shape, and category count
48. Connected live message orchestration through active policy, route permission, location, detector, and approved-resource gates
49. Added sanitized dependency-failure handling and bounded emergency orchestration audit outcomes
50. Documented `200` emergency and `503` fail-closed message response contracts in OpenAPI and numbered project docs
51. Bound emergency route policies to explicit detector-version allowlists and blocked unreviewed versions
52. Split policy, detector, and registry dependency failures into bounded operational audit outcomes
53. Made the UI asset regression test portable across standard Windows JavaScript MIME mappings
54. Added a strict synthetic emergency evaluation dataset and case schema with review and usage metadata
55. Added deterministic case, recall, false-positive, unavailable, and threshold report metrics
56. Added privacy-safe evaluation reports that exclude scenario message text and detector exceptions
57. Added passing baseline and intentionally failing negation, misspelling, and mixed-language challenge datasets
58. Added a packaged evaluation command with explicit pass, threshold-failure, and load-failure exit codes
59. Extended the line-ending policy to versioned JSON evaluation artifacts
60. Removed the UI's assumed Pakistan location and now requires explicit country selection
61. Isolated health and readiness status failures so one failed check cannot falsely mark both offline
62. Added assertive emergency announcements, busy states, reduced-motion scrolling, and browser persistence hints
63. Added static UI regressions for unique IDs, control labels, landmarks, CSP compatibility, unsafe DOM sinks, and privacy storage APIs
64. Fixed conversation-header overflow across the 761-to-1050-pixel tablet breakpoint and visually verified the rendered layout
65. Added strict bounded scope decisions for no-signal, unsupported, prohibited, and unavailable outcomes
66. Added a fail-closed scope detector and deterministic synthetic keyword reference detector with prohibited precedence
67. Bound scope routes to explicit active-policy detector versions and route permissions
68. Added emergency-first orchestration so scope handling cannot suppress a possible emergency response
69. Added bounded unsupported and prohibited response composers with no medical guidance or sources
70. Added API, audit, policy, dependency-failure, precedence, privacy, and response regression coverage for scope routing
71. Realigned the product core to a domain-locked self-learning medical video system
72. Added safe operator dataset manifests, source confinement, and duplicate asset hashing
73. Added persistent SQLite domain, video, insight, status, and schedule-decision records
74. Added provenance-gated scripts and domain revalidation after narration assembly
75. Added atomic local artifact storage and safe browser-openable storyboard previews
76. Added a credit-free local vertical H.264 MP4 preview renderer
77. Added media signature verification and fail-closed publishability gates
78. Added explainable online strategy learning with bounded exploration and confidence
79. Added evidence-based one-to-five daily frequency control with incident backoff
80. Added approved-only duplicate-safe automation schedule planning
81. Added official-flow YouTube, Instagram, Facebook, and X publishing adapters
82. Added trusted upload-host, platform-ID, artifact-hash, audio, and approval gates
83. Added four-platform insight normalization into the online-learning reward contract
84. Added persistent concurrent-safe publication idempotency and bounded retries
85. Added the responsive MediLoop operator dashboard as the root product UI
86. Preserved the earlier chatbot UI under the `/legacy` route
87. Added authenticated operator APIs for domain, dataset, preview, approval, insight, and schedule workflows
88. Restricted production operator reads and disabled unauthenticated production artifact mounting
89. Prevented imported seed examples from bypassing render and hash verification before approval
90. Made schedule reservation and status transition one atomic database transaction
91. Fixed cold-start timing to select the earliest equally scored safe slot
92. Fixed local MP4 encoding to preserve exact declared dimensions without FFmpeg resizing
93. Added end-to-end tests from seed import through rendered approval, scheduling, and learning insight
94. Visually verified desktop and 390-pixel mobile layouts with live API state and no overflow
95. Rewrote the repository entry point and status tracker around the actual video automation product
96. Added encrypted S3-compatible artifact mirroring with remote hash and size verification
97. Added bounded HTTPS signed artifact URLs and verified cloud downloads
98. Added durable idempotent automation jobs with exclusive SQLite leases and crash recovery
99. Added heartbeat, delayed retry, max-attempt, cancellation, and bounded failure transitions
100. Rejected credential-like fields and oversized JSON from persistent job payloads and results
101. Added authenticated operator job create, count, detail, and cancel routes
102. Aligned the development pytest range with installed async tooling and removed the local plugin workaround
