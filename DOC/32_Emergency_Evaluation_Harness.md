# 32. Emergency Evaluation Harness

## 32.1 Purpose

The evaluation harness measures a bounded emergency signal detector against versioned synthetic ground truth. It creates repeatable engineering evidence without storing raw scenario messages in the report.

It does not provide clinical validation, production thresholds, representative population coverage, or permission to activate emergency routing.

## 32.2 Dataset Contract

Every dataset records:

1. stable dataset ID and immutable version;
2. exact expected detector version;
3. mandatory `synthetic: true` marker;
4. owner and engineering-only or clinically-reviewed status;
5. named reviewers when clinical review is claimed;
6. source description and intended use;
7. prohibited uses and known gaps;
8. explicit metric thresholds;
9. at least one possible-emergency and one no-signal case;
10. unique bounded case IDs, locale, synthetic message, expected status, and expected categories.

The schema rejects unavailable as ground truth because unavailable is a runtime detector outcome, not a scenario label. Possible-emergency cases require categories; other labels cannot include categories.

## 32.3 Report Contract

The JSON report contains:

1. dataset ID and version;
2. expected detector version and review status;
3. thresholds and aggregate metrics;
4. overall threshold verdict;
5. per-case ID, expected and actual status, sorted categories, detector version, and bounded failures.

The report excludes scenario messages, dataset source notes, detector exception text, model reasoning, keyword matches, and user data.

## 32.4 Metrics

1. total, passed, and failed cases;
2. emergency and non-emergency case counts;
3. true positives and false negatives;
4. true negatives and false positives;
5. unavailable cases;
6. case pass rate;
7. emergency recall;
8. false-positive rate;
9. unavailable rate.

The verdict requires every configured minimum and maximum threshold to pass. Detector-version or category mismatches fail the case even when the broad status matches.

## 32.5 Commands and Exit Codes

```powershell
.venv\Scripts\python -m medibot.evaluation evaluations\emergency_signal_baseline.v1.json
.venv\Scripts\python -m medibot.evaluation evaluations\emergency_signal_challenge.v1.json
```

1. Exit `0`: configured thresholds pass.
2. Exit `1`: report generated but thresholds fail.
3. Exit `2`: dataset cannot be safely loaded or validated.

Invalid dataset errors are sanitized and do not echo file contents.

## 32.6 Current Results

### Baseline 1.0.0

1. Six of six cases pass.
2. Emergency recall is `100%`.
3. False-positive rate is `0%`.
4. Unavailable rate is `0%`.
5. Verdict passes.

This proves only deterministic plumbing, serialization, metrics, and threshold behavior.

### Challenge 1.0.0

1. One of four cases passes.
2. Two emergency cases are missed.
3. One of two non-emergency cases is incorrectly flagged.
4. Emergency recall is `0%`.
5. False-positive rate is `50%`.
6. Verdict fails.

This confirms that substring keyword matching fails on misspelling, mixed language, and negation and cannot be treated as a production classifier.

## 32.7 Remaining Evidence

1. Approved intended users, function, jurisdictions, and locales.
2. Clinically owned scenario taxonomy and severity weights.
3. Representative paraphrase, slang, ambiguity, negation, typo, and mixed-language coverage.
4. False-negative review for every critical case.
5. Frozen production detector adapter and version.
6. Clinician, localization, legal, privacy, product, and operations approval.
7. Release-linked report artifact, monitoring thresholds, rollback, and incident runbook evidence.
