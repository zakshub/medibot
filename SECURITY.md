# Security Policy

## Supported Status

Medibot is pre-release software. It must not be used for real medical guidance or production health-data processing.

## Reporting a Vulnerability

Do not open a public issue containing:

- credentials or access tokens;
- personal or health information;
- a working exploit against a deployed system;
- details that would expose another person's account or data.

Use GitHub's private vulnerability reporting feature for this repository when available. Include:

- affected commit or version;
- reproducible steps using synthetic data;
- expected and actual behavior;
- potential security, privacy, or medical-safety impact;
- suggested mitigation, if known.

Do not test against real users, real health records, or systems you do not own or have permission to assess.

## Security Baseline

- Secrets belong in environment variables or an approved secret manager, never Git.
- Development and tests must use synthetic data.
- Raw health content must not appear in logs or validation errors.
- Required safety controls fail closed.
- Dependencies and workflows must remain minimal and reviewable.
- Security, privacy, and medical-safety findings can block release independently.

