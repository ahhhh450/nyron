# Nyron Lead Active Queue

Authority: Lead Design Authority
Purpose: Keep the main design window's immediate execution queue explicit so review/delegation work is not left as an unstated next step.

## Active Queue

1. NYRON-D-004 — DeepSeek bounded consistency review
   - Review candidate: `design/Nyron_Capability_Resource_Effect_Authority_Design_Candidate_v0.1.md`
   - Required baseline: `design/Universal_Runtime_Module_Design_Report_v0.1.md`
   - Required amendment: `design/amendments/Module_Architecture_Amendment_001_EffectOperation_Prepared.md`
   - Goal: validate three-owner separation, PREPARED semantics, R1→R2 fencing, UNKNOWN preservation, Host boundary, and Effect/Budget orthogonality.

2. NYRON-D-003 — Lead integration review
   - Candidate: `design/Nyron_Runtime_Orchestration_Design_Candidate_v0.1.md`
   - Check Runtime ownership, retry/replacement/resume, cancellation, convergence, suspension/replay, deterministic ordering, and D-004 fencing interface.

3. NYRON-D-005 — Lead integration review
   - Candidate: `design/Nyron_Accounting_Recovery_Design_Candidate_v0.1.md`
   - Check Accounting/Recovery ownership, hierarchical reservation atomicity, UNKNOWN handling, ReconciliationCase, late billing, and cross-owner convergence.

4. NYRON-D-008 — Lead integration review
   - Candidate: `design/Nyron_External_Interfaces_Workspace_Boundary_Design_Candidate_v0.1.md`
   - Check external-boundary mappings consume D-004 without redefining authority/resource/effect ownership.

5. NYRON-D-002 — Lead final consolidation/freeze
   - Candidate: `design/Nyron_Graph_Composite_Design_Candidate_v0.1.md`
   - Clarification: `design/clarifications/NYRON-D-002_Lead_Integration_Clarification_001.md`
   - Review: `design/reviews/NYRON-D-002_DeepSeek_Targeted_ReReview.md`

6. NYRON-D-001 — Overall Architecture integration
   - Add `EffectOperation -> Effect Authority` to canonical Owner table.
   - Integrate frozen/accepted subsystem boundaries after local review gates.

## Operating Rule

When the main window states a concrete next action and the required tool/candidate is available, execute it in the same turn unless blocked by an explicit dependency. Do not stop after merely announcing the next action.

This file is an operational queue, not an architecture baseline. `design/coordination/STATUS.md` remains the authoritative task status table.
