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
