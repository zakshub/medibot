# 39 - Online Learning and Automation Planner

## Learning Unit

The system evaluates a content variant as:

`topic + posting hour + style + duration bucket`

Each platform result is converted to a bounded reward using:

- view rate;
- average watch ratio;
- weighted likes, comments, and shares.

## Decision Method

The learner uses an explainable upper-confidence-bound score.

- Unseen in-domain variants receive controlled exploration priority.
- Seen variants combine mean reward with an uncertainty bonus.
- Confidence increases with observation count.
- The recommendation records mode, score, reward, evidence count, and reasons.
- Out-of-domain variants are removed before scoring.

## Frequency Control

- Hard range: one to five posts per day.
- Cold start: safe minimum.
- Sustained high reward: increase by at most one post per day.
- Sustained low reward: decrease by one.
- Any spam or policy incident: decrease by one.
- Medium performance: hold.
- The learning layer cannot exceed configured limits.

## Schedule Planning

Only domain-verified, operator-approved, not-already-scheduled candidates are eligible. The
planner combines the learned strategy with:

- today's adaptive post target;
- allowed posting windows;
- historical posting hours;
- minimum spacing;
- duplicate schedule prevention;
- remaining time in the local day.

Every accepted schedule contains machine-readable reasons.

## Current Boundary

The engine is online-learning logic, not an autonomous production worker yet. Platform adapters,
persistent job execution, and operator controls are added in later batches.

