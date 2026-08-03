# Contributing to Medibot

## Working Method

1. Keep each change focused on one outcome.
2. Update relevant documentation with the implementation.
3. Add or update tests for behavior changes.
4. Run available checks before committing.
5. Use clear commit messages such as `docs: define safety boundaries` or `feat: add symptom intake validation`.

## Review Requirements

Every change should be reviewed for the dimensions it actually touches:

- correctness and edge cases;
- error handling and observability;
- privacy, security, and handling of health data;
- medical safety and harmful-output risk;
- performance and reliability;
- backward compatibility;
- test coverage and documentation.

## Medical and Privacy Rules

- Never commit personally identifiable health information.
- Use synthetic or fully de-identified test data.
- Do not add diagnosis or treatment logic without qualified clinical review.
- Do not silently send user health data to third-party services.
- Document data collection, purpose, retention, deletion, and access controls before persistence is implemented.

## Pull Request Checklist

- [ ] Scope and expected behavior are documented.
- [ ] Failure and emergency paths are handled.
- [ ] Medical claims have an identified authoritative source and review owner.
- [ ] No secrets or sensitive health data are included.
- [ ] Tests cover the changed behavior.
- [ ] Relevant `DOC` files and change log are updated.

