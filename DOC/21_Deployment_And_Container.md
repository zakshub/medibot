# 21 - Deployment and Container

## 1. Current Artifact

The repository provides a multi-stage Docker build that:

- builds the application and dependency wheels in a disposable builder stage;
- installs the runtime from the local wheel directory without a package-index call;
- runs as a dedicated non-root system user;
- excludes source-control, tests, documentation, local environments, secrets, and generated data;
- disables Python bytecode writes and buffered logs;
- disables Uvicorn access logging to avoid accidental request metadata collection;
- exposes only the application port and a liveness healthcheck.

## 2. Build and Run

```powershell
docker build --tag medibot:local .
docker run --rm --publish 8000:8000 medibot:local
```

The container sets `MEDIBOT_ENVIRONMENT=production` and `MEDIBOT_DEBUG=false`. Secrets must be injected by an approved runtime secret manager, never baked into the image or passed in committed files.

`compose.yaml` provides a hardened local baseline with localhost-only binding, a read-only root filesystem, temporary bounded `/tmp`, all Linux capabilities dropped, no-new-privileges, and process/resource limits. It is intentionally not presented as a production orchestrator configuration.

## 3. Health and Readiness

The Docker healthcheck uses `/v1/health` only to confirm that the process can answer locally. Traffic routing must use `/v1/ready`, which remains HTTP `503` while medical guidance is unavailable.

A healthy container is therefore not equivalent to a medically ready service.

## 4. Required Production Controls

Before any production deployment:

- pin the approved base image and record its digest;
- scan the final image and generate a software bill of materials;
- run with a read-only root filesystem and dropped Linux capabilities;
- set CPU, memory, process, and request limits;
- enforce TLS at the trusted ingress;
- configure distributed rate limiting and trusted proxy behavior;
- configure approved secret injection and rotation;
- send bounded application audit events to the approved sink;
- configure readiness-based traffic routing and tested rollback;
- prohibit privileged mode, host networking, and host filesystem mounts.

## 5. CI Boundary

CI builds the image but does not publish or deploy it. Publication requires an immutable tag, provenance, vulnerability scan, approval evidence, and an approved registry. A successful image build is not release approval.
