# Synthetic Emergency Evaluations

This folder contains versioned, hand-authored synthetic detector cases. It contains no patient records, copied conversations, names, contact details, or real incident reports.

## Datasets

1. `emergency_signal_baseline.v1.json` verifies deterministic reference-detector plumbing and is expected to pass.
2. `emergency_signal_challenge.v1.json` demonstrates known keyword-detector failures involving negation, misspelling, and mixed language and is expected to fail.

Neither dataset is clinical validation evidence. The reference keyword detector must not be used for production triage or emergency decisions.

## Commands

```powershell
.venv\Scripts\python -m medibot.evaluation evaluations\emergency_signal_baseline.v1.json
.venv\Scripts\python -m medibot.evaluation evaluations\emergency_signal_challenge.v1.json
```

The baseline command returns exit code `0`. The challenge command returns exit code `1` while known limitations remain. Dataset load or validation failure returns exit code `2`.

Reports intentionally exclude scenario message text. They contain bounded case IDs, expected and actual decision fields, failure categories, versions, aggregate metrics, and the threshold verdict.
