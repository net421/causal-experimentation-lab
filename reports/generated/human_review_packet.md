# Human review packet

## Automated evidence status

The pipeline status is **eligible_for_human_review**. This is an invitation to review evidence, not a deployment decision. Automated deployment authorization is fixed to `false`.

## Required review record

A real-world decision must be recorded in an external governed system by an accountable reviewer. The record must include reviewer identity, date, decision (`approve pilot`, `request changes`, or `reject`), rationale, budget impact, affected groups, rollback trigger, and monitoring owner. This repository deliberately contains no fabricated signature or approval.

## Review questions

1. Is the treatment operationally defined well enough to reproduce?
2. Are margin, stockouts, service level, and customer harm measured together?
3. Is randomization feasible without contamination between centers?
4. Are implementation cost and capacity constraints included in the business case?
5. Is there a rollback threshold and a named monitoring owner?
6. Does the real pilot population match the population for which a decision is proposed?

## Current authorization

- Evidence review may proceed: `true`
- Pilot authorized by this repository: `false`
- Production rollout authorized by this repository: `false`
