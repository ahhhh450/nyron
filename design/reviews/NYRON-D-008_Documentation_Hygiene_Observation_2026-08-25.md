# NYRON-D-008 — Documentation Hygiene Observation

**Date:** 2026-08-25  
**Classification:** NON-BLOCKING DOCUMENTATION HYGIENE  
**Architecture Finding:** NONE  
**Freeze impact:** NONE

## Observation

During final integrated-review follow-up, the historical D-008 Candidate was read in full and §11.7 was observed to still contain the pre-Amendment retry wording:

```text
Safe redispatch requires one of:
- proof old operation was never dispatched;
- proof old operation is FENCED;
- ...
```

The standalone `proof old operation is FENCED` condition was previously identified as unsafe by `NYRON-D-004-GPT-F01` and corrected through:

`design/amendments/External_Interfaces_Amendment_001_Fenced_Retry_Semantics.md`

The frozen architecture is therefore already correct. The issue is discoverability for future readers who may open the historical Candidate without first reconstructing the amendment chain.

## Disposition

- `NYRON-D-004-GPT-F01` remains CLOSED.
- D-004 targeted GPT re-review PASS remains valid.
- Overall System Architecture freeze remains valid.
- No new Architecture Finding is opened.
- No frozen semantic contract is changed.

A dedicated supersession notice was added:

`design/errata/NYRON-D-008_Candidate_Supersession_Notice.md`

The design entry-point rules are also updated so Candidates are never treated as standalone implementation authority where a frozen baseline/amendment exists.

## Documentation lesson

A historical Candidate may legitimately preserve the exact wording that was later frozen and amended, but future implementation readers must not be required to infer the correct semantic ordering from an undocumented correction chain.

When an Amendment supersedes correctness-relevant wording, the repository should expose that supersession through a visible notice/index and implementation reading order.
