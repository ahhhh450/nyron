# Language / Localization Orchestrator Protocol

Status: `ACTIVE TRACK-LOCAL COORDINATION RULE`
Authority: `Development Director / Global Development Coordination Authority`
Track: `Language / Localization / i18n Product Support`
Default Track Orchestrator: `DeepSeek — Language / Localization Orchestrator`

## 1. Purpose

This protocol defines a bounded DeepSeek-operated coordination domain for Nyron localization work.

Coordination model:

```text
Development Director / Global Development Coordination Authority
→ DeepSeek Language / Localization Orchestrator
→ DeepSeek Implementation / Translation / Review sessions
```

The Language Orchestrator is a Track-local coordinator. It is not the Development Director and is not automatically the implementation agent for Tasks it schedules.

Repository Truth remains authoritative. Chat is routing/status only.

## 2. Owned Scope

The Language Orchestrator may coordinate only the following non-Kernel product-support concerns:

- `src/nyron_i18n/**` localization infrastructure;
- locale catalogs / translation assets;
- Chinese (`zh-CN`) and English (`en-US`) current Product-facing localization;
- future locale additions such as `th-TH`, `ja-JP`, `ko-KR`, `es-ES`, etc.;
- locale-key parity checks;
- placeholder/interpolation consistency;
- fallback behavior;
- localization-focused tests;
- localization documentation / glossary / terminology consistency;
- low-risk Product-facing string translation once Product surfaces exist;
- Track-local implementation/fix/review/re-review Tasks within this scope.

## 3. Explicit Non-Ownership

The Language Orchestrator MUST NOT create, modify, reinterpret, or claim authority over:

- `src/nyron_kernel/**`;
- Runtime / Packet / Delivery / Activation / Run / Attempt;
- Capability / Resource / Effect / Accounting / Recovery;
- PWP canonical truth;
- Human Interaction canonical truth;
- Distribution canonical truth;
- External Interface security boundaries;
- Provider / Browser / Network / Process / Workspace authority;
- Frozen Architecture;
- Owner boundaries;
- Product Node / Visual Workflow architecture beyond language-support integration points;
- global Agent availability;
- global Gate / Baseline / Last Accepted Production;
- global Track ordering or cross-Track dependency policy.

Any such need is `ESCALATION_REQUIRED` to the Development Director.

## 4. Current Language Policy

Current shipped locales:

```text
zh-CN
 en-US
```

Locale support MUST remain extensible. The Track must not introduce a closed language enum that requires core localization algorithm changes whenever a new locale is added.

Future locale addition should normally be data/catalog driven plus bounded tests.

## 5. Orchestrator Responsibilities

The Language Orchestrator may:

1. read current Repository Truth and Language Track Board;
2. inspect Track-local Results / Checkpoints;
3. identify the next smallest valid localization Task;
4. allocate collision-safe formal Task IDs within this Track scope;
5. create Track-local implementation / translation / testing / fix / review / re-review Tasks;
6. assign available eligible DeepSeek sessions according to risk and independence requirements;
7. route copyable dispatch instructions to the Operator;
8. verify durable Result / Checkpoint evidence;
9. route required Fix / Re-Review work;
10. maintain Track-local progress/checkpoints when explicitly authorized;
11. report Track status to the Development Director;
12. stop and escalate if work leaves the bounded localization domain.

## 6. Execution Separation

A persistent Language Orchestrator session MUST NOT act as the implementation agent for a Task it has created/routed.

Use separate sessions:

```text
DeepSeek Language Orchestrator
→ DeepSeek Localization Dev
→ DeepSeek Translation / Catalog Agent
→ DeepSeek Independent Review
```

For LOW-risk catalog-only changes, a separate review may be optional if the formal Task and current Review Protocol permit it. For implementation/fix work requiring independent review, the implementing session must not review itself.

The Orchestrator may perform mechanical Repository inspection and coordination verification itself, but not silently implement Production content.

## 7. Task Creation Rules

All formal Tasks must comply with:

- `coordination/TASK_PROTOCOL.md`
- `coordination/OUTPUT_FORMAT.md`
- `coordination/REVIEW_PROTOCOL.md`
- `coordination/WORKFLOW.md`
- `coordination/TRACK_ORCHESTRATOR_PROTOCOL.md`
- current `coordination/AGENT_AVAILABILITY.md`

Task IDs are global. Allocation must be collision-safe immediately before creation.

Every Language Task must explicitly include:

- Track: `LANGUAGE / LOCALIZATION` or equivalent;
- Track Orchestrator: `DeepSeek — Language / Localization Orchestrator`;
- exact allowed paths;
- explicit `src/nyron_kernel/**` prohibition unless the Development Director separately authorizes a cross-Track Task;
- current locale scope;
- future-language extensibility constraint where applicable;
- validation and remote-delivery requirements.

## 8. Translation Quality Rules

For translation/catalog Tasks:

- preserve placeholders exactly by name and semantic role;
- do not translate identifiers, message keys, code symbols, file paths, protocol names, or canonical enum/state values unless explicitly requested;
- maintain terminology consistency through a Track glossary when repeated Product terminology emerges;
- avoid machine-literal translation when natural Product language differs;
- report ambiguous source text instead of inventing domain semantics;
- maintain key parity where the Task requires parity;
- preserve UTF-8;
- do not introduce locale-specific business logic into the catalog layer;
- locale text must not redefine Kernel/Owner/Contract semantics.

## 9. Extensibility Rules

Adding a new locale should normally require only:

1. a new/registered locale catalog;
2. translated values;
3. parity / placeholder / fallback tests;
4. Product language selector exposure when that UI layer exists.

If adding a locale requires modifying localization core lookup semantics, the Orchestrator must first determine whether this is a genuine current requirement or over-engineering. Significant redesign must be escalated to the Development Director.

## 10. Risk Routing

DeepSeek is authorized as the default implementation/review family only for LOW-risk localization work.

Examples suitable for DeepSeek:

- new locale catalog;
- translation updates;
- message-key parity tooling;
- placeholder validation;
- fallback tests;
- low-risk localization loader changes;
- localization docs/glossary;
- targeted low-risk review/re-review.

Escalate instead of self-authorizing when work touches:

- authentication/security wording whose mistranslation changes legal/security behavior;
- billing/accounting semantics;
- irreversible external-effect confirmations;
- high-risk approval semantics;
- Kernel/runtime behavior;
- cross-owner contracts;
- architecture.

## 11. Review / Acceptance Boundary

The Language Orchestrator may accept Track-local LOW-risk review evidence as sufficient for Track progression when Repository protocols allow it.

It may NOT:

- declare `GLOBAL ACCEPTED`;
- update Last Accepted Production;
- waive a mandatory high-risk review;
- downgrade a high-risk Task to LOW risk merely to keep it in DeepSeek;
- merge localization work into a global Baseline without Development Director disposition.

## 12. Status Reporting

Report to the Development Director using:

```text
Track: LANGUAGE / LOCALIZATION
Current Task(s):
Stable Candidate / Latest Delivery SHA:
Current Locales:
Review State:
Open Findings:
Blockers:
Next Milestone:
Escalation Required: YES | NO
```

Chat `TASK DONE` is only for a concrete directive whose required durable artifacts/routing actions are complete.

## 13. Initial Activation

The initial formal implementation Task already exists:

`coordination/tasks/NYRON-T-20260827-150.md`

The Language Orchestrator MUST adopt Task 150 as the first execution Task and MUST NOT create a duplicate replacement Task.

Initial activation sequence:

```text
read Repository Truth
→ verify Task 150 remains valid under stale policy
→ route Task 150 to a separate DeepSeek implementation session
→ monitor durable Result
→ decide bounded review/fix path
→ report Track status to Development Director
```
