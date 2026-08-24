Universal Runtime — Module Design Report v0.1

0. 文档目的与冻结原则
本文定义 Universal Runtime 中 Module 子系统的完整设计契约，使一个完全没有参与此前讨论的 AI 或工程师，仅凭本文即可理解边界、实现路径、错误语义、测试门槛和禁止事项，并可以直接开始 Phase 1–2 实现。
本文是 Greenfield 设计。旧项目只可在后续 Migration Audit 中被判定 KEEP / ADAPT / REFACTOR / DELETE / REWRITE；不得为了兼容历史实现反向降低本 Contract。
允许用户写坏 Workflow，但不允许 Workflow 写坏 Runtime。
Node is not a Runtime primitive. Module is.
Provenance ≠ Authority.
Commit Fencing 防写假结果；Effect Fencing 防写假副作用。
授权发生在未来，事实记录发生在过去。对于无法确认的过去，系统明确标记 UNKNOWN / ESCALATED，而不是编造方便的答案。
1. Module 的定位
Runtime 不定义大量业务 NodeType。Agent、Developer、Reviewer、Tester、Discussion、Coordinator、Router、Loop、Human Approval、Text Node、LLM Node 都不是 Kernel primitive。
这些上层概念只能是 Module 的配置、UI 包装、多个 Module 组成的 Composite、Graph topology 或产品模板。
User-facing Node / Composite
        ↓
ModuleInstanceRevision
        ↓
ModuleDefinition@version
        ↓
Packet → Delivery → Activation → Run
Kernel 只理解一个可执行 Module 能力、不可变输入、当前 Run Attempt 的 authority，以及其产生的事实；它不理解“这是程序员”或“这是审核员”。
2. 单一 Module Contract：不硬编码 TRANSFORM / INVOKE / LISTEN 类型
不得设计 ModuleType = TRANSFORM | INVOKE | LISTEN。三者只描述行为形态，不是注册类型，也不应产生三套 Executor。
Pure transform:
Packet Inputs → Module → Completed(outputs)

Active invoke:
Packet Inputs → Module → Capability-mediated external effect → Completed(outputs)

Suspend/listen:
Packet Inputs → Module → Suspended(subscription, continuation)
             → Event → resume(...) → Completed / Suspended / Failed
所有行为使用同一执行契约和同一 Run/Attempt/Fencing 模型。
3. ModuleDefinition
ModuleDefinition 是可注册、版本化、不可变的执行能力契约。唯一身份为 module_ref@version。
ModuleDefinition
- module_ref
- version
- input_port_definitions[]
- output_port_definitions[]
- config_schema
- effect_classes[]
- required_capability_types[]
- execution_contract
- metadata
示例：builtin.text.concat@1、provider.model.invoke@2、builtin.json.parse@1。
同一 module_ref@version 一旦注册，其输入/输出契约、config schema、effect 声明、capability 需求与 observable execution semantics 不得原地改变。Breaking change 必须升版本。
允许不改变 observable semantics 的实现 bugfix / 性能修复；若修复改变输入接受范围、输出、effect 行为、错误语义或持久状态语义，则必须升级 Module version。
4. ModuleInstanceRevision 与 GraphRevision pinning
ModuleDefinition 是能力定义；Graph 上被执行的是 ModuleInstanceRevision。
ModuleInstanceRevision
- module_instance_revision_ref
- graph_revision_ref
- module_instance_ref
- module_definition_ref@version
- config_ref
- config_hash
- input_port_contract
- output_port_contract
- static_composite_path
- static_accounting_scope_ref
GraphRevision 发布后不可变。Activation 必须 pin graph_revision_ref + module_instance_revision_ref；不得在执行时重新读取 current graph / current config。
config_hash 只用于 integrity evidence，不能替代可寻址的 immutable config_ref。
历史 GraphRevision / ModuleInstanceRevision 在仍被 durable execution history 引用时必须 retention-protected；可以归档，但引用必须保持可解析。
5. 新增修正：未解析 Module 引用
GraphRevision / Composite 结构校验必须验证每个 ModuleInstanceRevision 引用的 module_definition_ref@version 能解析到 exactly one 已注册、不可变 ModuleDefinition。
If module_ref@version cannot resolve:
→ UNRESOLVED_MODULE_REFERENCE
→ GraphRevision MUST NOT become executable.
错误上下文至少包含 graph_revision_ref、module_instance_ref、module_ref、required_version。
允许导入或保存带有未解析依赖的 Graph/Composite，以便用户查看和修复，但其状态只能是非可执行定义；未解析依赖解决并通过结构校验后才可进入 executable 状态。
这为 workflow 分享 / ComfyUI 风格“缺少节点”体验提供基础：导入不丢图，执行前明确列出缺失 Module。
6. Composite / Graph 的 Module Dependency Manifest 要求
后续 Composite/Graph 子系统必须从图结构自动派生依赖清单，而不是由作者手填。
dependency_manifest =
sorted(unique(all referenced module_ref@version recursively))
Composite 嵌套必须递归 flatten 后去重、稳定排序。Manifest 用于 import validation、missing-module diagnostics、package resolution、workflow sharing、compatibility check 和 offline bundle/export。
此 Manifest 是定义层派生信息，不是新的 Runtime execution primitive。
7. Input Port Activation Contract
每个 Input Port 单独声明 activation mode，以消除 barrier 与 reactive 语义歧义。冻结的四种模式为：TRIGGER、REQUIRED_NEXT、REQUIRED_LATEST、OPTIONAL_LATEST。
Mode	是否触发	是否 consume	语义
TRIGGER	是	是	每个新 Delivery 请求一次 Activation
REQUIRED_NEXT	否	是	每个 Activation 必须拿一个未绑定的新 Delivery
REQUIRED_LATEST	否	否	创建 Activation 时必须存在最新 Delivery，snapshot
OPTIONAL_LATEST	否	否	同上；不存在则 null
8. Packet / Delivery / Activation / Run 映射
Packet
  ↓ Edge projection
Delivery
  ↓ Port activation rules
Activation
  ↓ current Attempt
Run
  ↓ atomic terminal outcome
Output Packet
Packet 是不可变数据事实，不被消费；Delivery 是 target-specific delivery fact，consume/bound 语义属于 Delivery。
所有 Activation 必须由 Trigger Delivery 引起。Manual Run、Workflow Start、Schedule、External Event、Human Action 等都应先形成 Trigger Packet，再投影为 Delivery；不保留特殊 explicit-activation 第二入口。
Activation 是不可变执行意图，固定 graph revision、module instance revision、input bindings、trigger delivery 和 accounting affiliation。Run 是实现该 Activation 的一次 Attempt。
9. Delivery ordering 与幂等投影
Derived execution order 必须是 committed canonical facts 的函数，不能由 projector worker 的调度先后决定。
delivery_order_key =
(
  source_packet_seq,
  edge_ordinal,
  target_port_ordinal
)

Delivery uniqueness =
(
  packet_ref,
  graph_revision_ref,
  edge_ref,
  target_port_ref
)
Packet → Delivery propagation 是 idempotent projection，可无限安全 replay。fan-out 中途 crash 后，已存在 Delivery 不重复，缺失 Delivery 补齐。LATEST 的“最新”依据 durable deterministic order，不依赖 wall clock。
10. Activation 创建事务
Trigger 决定为什么尝试形成 Activation；required ports 决定该请求是否 ready。Activation 创建与 consume-once Delivery binding 必须在同一事务完成。
BEGIN
1. select oldest pending TRIGGER by deterministic delivery_order_key
2. check REQUIRED_NEXT availability
3. bind REQUIRED_NEXT deterministic oldest deliveries
4. snapshot REQUIRED_LATEST / OPTIONAL_LATEST
5. bind consumptive Deliveries
6. create immutable Activation with exact input bindings
COMMIT
失败必须全部 rollback；不能出现 Delivery 已被吃掉但 Activation 未创建，也不能同一 consumptive Delivery 被两个 Activation 绑定。
11. Module Execution Contract
execute(
  immutable_inputs,
  immutable_config,
  runtime_context
) -> ModuleResult

ModuleResult =
  Completed(outputs)
  | Suspended(subscription_spec, continuation)
  | Failed(error)
Module 不负责 readiness、Activation 创建、下游调度、retry policy、Workflow convergence、Budget authority、canonical state ownership 或 recovery truth adjudication。
12. Completed / Failed 的 Kernel 边界
Module 返回 Completed 并不直接意味着 canonical Run SUCCESS。Kernel 必须先验证 output schema、durable value、current attempt fencing，再在一个 canonical transaction 中提交 Run terminal outcome + Output Packet manifests。
durable output value first
↓
BEGIN canonical transaction
verify current attempt
Run → SUCCESS
create Output Packets
append canonical events
COMMIT
↓
idempotent Delivery projection
允许 orphan durable value；禁止 canonical Packet 指向不存在/未 durable 的 blob。
Failed 只描述当前 Run Attempt 的结果，不自行决定 retry / switch provider / skip / abort。
13. Suspended 与 Continuation
Suspended 表示当前 Attempt 尚未结束，但必须等待未来 Event，且等待期间不存在持续 active computation。不能用 sleep / polling / 持有线程栈来模拟。
Continuation 的严格定义：同一个 Run Attempt 在主动 Suspension 点，为将来 resume 显式持久化的最小状态。它不是 crash checkpoint、provider token-stream checkpoint、失败 Attempt 的重试状态、新 Run 的继承状态或通用 checkpoint 系统。
Continuation
- continuation_ref
- schema_ref
- value_ref
- module_definition_ref@version
- run_ref
- resume_seq
Continuation 必须 explicit、durable、immutable、Run-bound、Attempt-bound、fenced。禁止藏在 Python/JS closure、thread stack、singleton、私有临时文件或 Kernel 不知道的 provider client 内存中。
14. Resume Contract
resume(
  original_immutable_inputs,
  continuation,
  event_packet,
  runtime_context
) -> Completed | Suspended | Failed
resume 不创建新 Activation，不创建新 Attempt。execute → Suspended C1 → Event → resume(C1) → Suspended C2 → Event → resume(C2) → Completed，可以始终属于同一 Activation / Run / attempt_seq。
只有真正的 retry / replacement 才产生新 Attempt。旧 Attempt 一旦被 fence，其 Continuation 和 Subscription 均失去恢复 authority。
15. Event / Subscription 边界
Module 只返回 subscription_spec；Kernel 负责 durable Event Log、Subscription、EventDelivery 和匹配。实时 push 只是 wake-up 优化，不是 correctness authority。
Subscription 创建必须绑定 durable event cursor / causal watermark；EventDelivery 的唯一性与 Subscription completion 必须原子，避免 Event 先到丢失和 duplicate wake-up。
16. Effect Declaration 与 Capability Mapping
每个 ModuleDefinition 必须声明 effect_classes[] 与 required_capability_types[]，Registry 进行 machine-checkable mapping validation。
Effect Class	Required Capability
PURE	none
MODEL_CALL	MODEL_INVOKE
WORKSPACE_READ	WORKSPACE_READ
WORKSPACE_WRITE	WORKSPACE_WRITE
PROCESS_EXEC	PROCESS_EXEC
NETWORK_IO	NETWORK_ACCESS
EVENT_SUBSCRIBE	EVENT_SUBSCRIBE
HUMAN_INTERACTION	HUMAN_INTERACT
CANONICAL_MUTATION	CANONICAL_COMMAND
声明 WORKSPACE_WRITE 但没有 WORKSPACE_WRITE capability requirement 必须拒绝注册：CAPABILITY_EFFECT_MISMATCH。
17. Capability Type 与 Capability Grant
ModuleDefinition 只能声明“需要什么能力类型”；运行时具体权限由 scoped CapabilityGrant 发放。Grant 必须 Run/Attempt-bound、Scope-bound、Lease-bound、Revocable、Non-transferable。
CapabilityGrant
- grant_ref
- capability_type
- activation_ref
- run_ref
- attempt_seq
- fencing_token
- scope
- lease_state
Module 无权自我升级权限，只能提出 request/proposal；真正授权来自外部 Authority / Policy。CANONICAL_COMMAND 必须是 mediated command，不得暴露 raw StateStore / SQLite。
18. Commit Fencing 与 Effect Fencing
两层 fencing 缺一不可。Commit Fencing 保护 canonical history；Effect Fencing 保护外部世界。
每次实际进入 mediated effect boundary 都重新验证 grant ACTIVE、activation current、attempt_seq current、fencing_token current、scope permits operation。不能只在 Grant 签发时检查一次。
workspace.write(...)
process.start(...)
model.invoke(...)
network.request(...)
    ↓
validate current fencing authority
    ↓
allow / STALE_EFFECT_ATTEMPT
19. EffectOperation
长期或异步副作用必须有 Kernel 可见的 canonical tracking record。EffectOperation 是 Kernel 内部对象；external_operation_ref 只是外部系统 identity。
EffectOperation
- operation_ref
- activation_ref
- run_ref
- attempt_seq
- fencing_token
- effect_class
- state
- external_operation_ref?

states:
ACTIVE
REVOKE_REQUESTED
FENCED
COMPLETED
UNKNOWN
external_operation_ref 可以是 PID、process_group、provider_request_id、remote_job_id。没有外部 ID 也不能省略 EffectOperation，因为 Kernel 仍必须知道其 attempt ownership 与 fencing 状态。
20. 长时间副作用
PROCESS_EXEC 等长时间 operation 不能在 start 时校验一次后就放任运行。Kernel/Module Host 必须持有实际生命周期控制能力：identify、revoke、kill/cancel、confirm stopped。
R1 becomes stale
↓
EffectOperation ACTIVE → REVOKE_REQUESTED
↓
kill/cancel
├─ confirmed stopped → FENCED
└─ cannot confirm → UNKNOWN → ReconciliationCase
旧冲突 Effect 未确认 fenced 前，新 Attempt 不得获得冲突 side-effect Grant。
21. Resource
Packet = 数据；CapabilityGrant = 权限；Resource = Kernel 知道并控制生命周期的 opaque stateful handle。三者必须严格区分。
Resource
- resource_ref
- resource_type
- resource_owner_ref
- scope_ref
- affinity
- state
- external_ref?
典型 Resource：Provider Session、Browser Session、Workspace Handle、Remote Job、Tool Session。Resource owner 管生命周期；Lease holder 表示当前哪个 Run Attempt 可以使用。Resource 的存在不授予权限，Capability 的存在也不保证 Resource 可用。
Resource 可以提高连续性和效率，但不能成为 Workflow-semantic truth 的唯一载体。Resource 丢失后可以变慢或重新 hydrate，但不能让 Workflow 无法解释自身历史。
22. 新增修正：Resource Lease 有界生命周期
每个 Resource Lease 必须具有显式 release / revoke / expiry 路径；不能因为 Workflow 终止后没有新 Attempt 就永久停留在 LEASED。
ResourceLease
- lease_ref
- resource_ref
- lease_holder_ref
- attempt_seq
- fencing_token
- issued_at
- expires_at
- state

states:
ACTIVE
EXPIRING
REVOKE_REQUESTED
RELEASED
EXPIRED
UNKNOWN
正常 Run/Workflow terminal 时应主动 revoke/release outstanding leases；TTL/expiry 是兜底，不是主要生命周期控制。
关键安全规则：Lease expiry 只终止未来 authority，不自动证明外部状态已经停止。如果外部资源仍可能产生副作用且无法确认已解绑/停止，则进入 UNKNOWN → ReconciliationCase，而不是直接伪造“已安全释放”。
23. Hidden Durable State 禁止
Module implementation MUST NOT own hidden durable state that affects future workflow semantics.
禁止私有 SQLite、隐藏 JSON、跨 Run singleton、未登记 provider session、私有跨 Run cache（若内容改变语义）、Kernel 不知道的磁盘状态。
允许当前函数局部变量、不影响语义的 transient cache、当前 active stack、Kernel-issued Resource handle、当前 RuntimeContext。
判断标准：如果 crash 后某个隐藏状态丢失，会导致 Workflow 无法解释已经发生过什么，则该状态必须显式进入 Packet / Resource / Continuation / Artifact / Canonical State。
24. AccountingScope 与静态归属
ModuleDefinition 本身不属于 Accounting Scope。每次执行的归属只由目标 ModuleInstanceRevision 在 GraphRevision 中的静态 Composite containment 决定。
Provenance ≠ Authority.
Packet provenance、Activation lineage、incoming Edge、trigger source 都不得改变 Accounting membership。动态血缘解释“为什么发生”，静态图定义决定“权限属于哪里、钱怎么算”。
25. BudgetReservation 与 Hierarchical Accounting
需要资源授权的 effect 必须先 Reserve，再执行，再 Settle actual。实际成本超出 estimate 时仍要提交真实 actual；Limit 只限制未来授权，不能修改已经发生的事实。
Reservation 对完整 static ancestor chain 做原子 reserve；子 scope 可以收紧但不能放宽父限制。被拒 Reserve 在后来提高预算时也不会自动复活，必须显式产生新请求。
26. 新增修正：EffectOperation 与 BudgetReservation 是两个正交维度
EffectOperation 和 BudgetReservation 必须保持独立状态机。前者记录外部副作用是否存在/活跃/已 fenced/已完成/未知；后者记录资源消费是否已授权/预留/提交/释放/未知。两者不得为了“省一套状态”而合并。
External effect state and accounting state are independent facts and MUST both be correct.
Examples:

EffectOperation = COMPLETED
BudgetReservation = SETTLED
→ effect 已完成，实际成本已结算。

EffectOperation = UNKNOWN
BudgetReservation = SETTLED
→ 无法确认外部副作用最终状态，但已知已经发生的成本仍必须真实结算；不能因为 effect unknown 就把费用“回滚掉”。

EffectOperation = FENCED
BudgetReservation = RELEASED
→ operation 在产生可计费执行前被成功阻止/取消，未使用的 reservation 可以释放。

EffectOperation state transition 不得隐式驱动 BudgetReservation state transition，反之亦然。两者可以由同一 canonical transaction 更新，但必须作为两个独立事实分别验证。
27. Budget 与 Capability 的授权顺序
对于需要预算的 effect，推荐授权顺序：
1. resolve static AccountingScope chain
2. BudgetReservation reserve
3. issue scoped CapabilityGrant
4. execute mediated effect
5. settle actual cost
6. release unused reservation
若 reserve 失败，不签发 effect grant。若 effect 已经发生，即使实际 cost 超预算，也必须记录真实 actual，再拒绝未来授权。
28. Module Host Boundary
Module 不应与 Kernel 在同一无限信任边界中长期耦合。架构必须保留 Module Host 抽象，即使 v0.1 初期实现为 in-process trusted host。
Kernel
  ↓ narrow RuntimeContext / Capability ABI
Module Host
  ↓
Module Implementation
未来可演进：
Trusted in-process Module Host
  ↓
Sandboxed / Isolated Module Host
  ↓
Custom Module
v0.1 可以只支持 TRUSTED MODULE MODE，并明确不宣称 hostile arbitrary plugin 已被安全 sandbox。未来可选择 worker process/container/WASM/VM 等实现，但不得为了第一版把 Module Host boundary 从架构中删除。
29. Module Registration
Register ModuleDefinition
        ↓
Schema validation
        ↓
Version identity validation
        ↓
Effect / Capability mapping validation
        ↓
Execution contract validation
        ↓
REGISTERED | REJECTED(reason_code)
Registration reason codes 至少包含：
• INVALID_MODULE_DEFINITION
• MODULE_VERSION_CONFLICT
• INVALID_PORT_SCHEMA
• INVALID_CONFIG_SCHEMA
• UNKNOWN_EFFECT_CLASS
• UNKNOWN_CAPABILITY_TYPE
• CAPABILITY_EFFECT_MISMATCH
• INVALID_SUSPENSION_CONTRACT
• UNRESOLVED_MODULE_REFERENCE（Graph/Composite validation）
30. Runtime Reason Codes
Runtime control flow 必须依赖 machine-readable reason_code，而不是自然语言字符串。用户可读解释属于独立 Diagnostics / Presentation 层。
• MODULE_EXECUTION_FAILED
• MODULE_RESULT_INVALID
• MODULE_OUTPUT_SCHEMA_MISMATCH
• MODULE_CONTINUATION_INVALID
• STALE_ATTEMPT_REJECTED
• STALE_EFFECT_ATTEMPT
• CAPABILITY_DENIED
• RESOURCE_UNAVAILABLE
• RESOURCE_LEASE_EXPIRED
• RESOURCE_LEASE_REVOKED
• EFFECT_OPERATION_UNKNOWN
• BUDGET_RESERVATION_DENIED
• BUDGET_SETTLEMENT_REQUIRED
• RECONCILIATION_REQUIRED
31. RuntimeContext
RuntimeContext 只向 Module 暴露窄接口，不暴露 Kernel internals。
至少包含：
- activation_ref
- run_ref
- attempt_seq
- fencing_token
- capability facade(s)
- resource access facade
- artifact/value writer
- suspension API
- diagnostics logger
- runtime metadata
RuntimeContext 不得暴露 raw unrestricted filesystem、raw subprocess、raw StateStore connection 或直接 canonical DB mutation。
32. Committed-History Determinism 对 Module 的要求
Kernel 不承诺现实中所有并发 interleaving 得到同一历史；它承诺给定同一 committed durable history 与 immutable definitions，crash/restart/replay 推导出同一 pending Deliveries、下一 Activation、input bindings、graph revision 和 subscription matching。
现实中哪个并发事务先提交是历史事实；一旦提交，Restart 不能重新解释。
33. 典型示例：Model Invoke Module
inputs:
- prompt
- optional context

config:
- provider_ref
- model
- generation parameters

effects:
- MODEL_CALL

capabilities:
- MODEL_INVOKE

execute:
inputs → model.invoke(capability mediated) → output Packet
Module 不保存 provider session；若需要 session continuity，使用 Kernel-visible Resource。
34. 典型示例：Human Approval Module
inputs:
- proposal

execute:
→ Suspended(
   subscription = approval_event,
   continuation = approval_request_state
   )

Event arrives
→ resume(...)
→ Completed(Response Packet)
35. 典型示例：Shell / Process Module
effects:
  PROCESS_EXEC
  WORKSPACE_WRITE

capabilities:
  PROCESS_EXEC
  WORKSPACE_WRITE
Module 不得直接调用 unrestricted subprocess.run；必须经过 Runtime/Module Host 的 controlled process capability，生成 EffectOperation，并确保 process group 可 revoke/kill/fence。
36. 反例清单
• Module 私有跨 Run Provider Session：违反 Resource / hidden durable state 规则。
• Module 内部无限 retry loop：Kernel 无法准确追踪 effect、预算和 attempt authority。
• Module A 直接私有调用 Module B/C：绕过 Packet → Delivery → Activation → Run。
• Module 直接拿 raw StateStore/SQLite：绕过 canonical owner/command authority。
• Module 在 Suspended 状态偷偷继续 PROCESS_EXEC / WORKSPACE_WRITE：绕过 active-time、budget 和 fencing。
37. Module Test Strategy
测试必须覆盖 contract-level correctness，而不只 happy path。
至少包含：
- Module definition registration / rejection
- unresolved module reference rejection
- deterministic Delivery projection
- Activation input binding atomicity
- Completed / Failed commit fencing
- stale Attempt late completion
- stale Attempt effect rejection
- output durable-before-canonical
- Suspension / resume replay
- Event-before-wakeup
- duplicate event delivery
- Resource lease expiry/revoke/release
- EffectOperation UNKNOWN reconciliation
- BudgetReservation reserve/settle/release
- hidden durable state crash test
- PURE determinism test
38. 实现阶段顺序
Phase 1 — Definition：ModuleDefinition Registry、ModuleInstanceRevision、immutable GraphRevision refs、schema/effect/capability validation；跑通一个 PURE text Module 注册。
Phase 2 — Execution ABI：实现 execute + Completed/Failed，经 Activation → Run → Output Packet 跑通。
Phase 3 — Capability：实现 CapabilityGrant、attempt/fencing context、至少一个 mediated effect。
Phase 4 — Resource：实现一个真实 Resource，例如 ProviderSessionResource；验证 owner / lease-holder / expiry。
Phase 5 — Suspension：实现 Suspended、Continuation、Subscription、EventDelivery、resume。
Phase 6 — Effect Fencing：实现 EffectOperation、revoke、fence、UNKNOWN。
Phase 7 — Recovery：把 UNKNOWN 接入 ReconciliationCase，保证 deadline → escalation。
39. 不建议的实现顺序
不要一开始先做 Developer Node、Reviewer Node、Discussion Node、Agent marketplace 或拖拽 UI polish。先证明一个 Module 能注册、实例化、Activation、Run、产生 Packet、被 fence、suspend/resume。
40. Module Registry 验收清单
• module_ref@version 唯一且 immutable。
• input/output/config schemas 有效。
• effect classes / capability types 已知且 mapping 完整。
• PURE module 不声明 external capability。
• suspension-capable implementation 能产生显式 durable Continuation。
• implementation ABI 与 execution_contract 匹配。
• GraphRevision 中所有 Module references 可解析，否则 UNRESOLVED_MODULE_REFERENCE 且不可执行。
41. Module Runtime 验收清单
• Run 属于存在的 immutable Activation。
• Activation pin 的 GraphRevision / ModuleInstanceRevision / ModuleDefinition 可解析。
• 执行时不读取 mutable current config/graph。
• input bindings 与 Activation 一致。
• Run 是 current Attempt。
• Capability Grants / Resource Leases 有效且 fencing current。
• output schema 合法；durable output 已确认。
• canonical commit 时再次校验 attempt fencing。
• stale Run 不产生 Output Packet / new mediated effect。
42. Suspension 验收清单
• execute → suspend → event → resume → success。
• 同一 Run suspend/resume 多次。
• crash 在 continuation durable 后 / canonical commit 前。
• Event 先于 realtime wake-up 仍不会丢。
• duplicate Event notification 不重复完成。
• stale Attempt Event 到达不能唤醒旧 Run。
• Continuation 不可形成 dangling canonical reference。
• Suspended Run 不继续持有 active-effect Grants。
43. Effect Fencing 验收清单
• 同一 Activation 两个 Attempt 不得同时持有 commit authority。
• R1 stale 后 workspace.write / process.start / model.invoke 被拒绝。
• 已运行 Process 收到主动 revoke；确认 kill 后 R2 才获冲突 Grant。
• kill/cancel 无法确认 → EffectOperation UNKNOWN → ReconciliationCase。
• 旧 Resource lease 被拒绝。
• R1 late Completed → STALE_ATTEMPT_REJECTED，不产生 Packet。
44. Resource Lease 验收清单
• 正常 Run terminal 主动 release/revoke lease。
• Workflow terminal 清理 outstanding leases。
• TTL/expiry 发生后未来使用 authority 立即失效。
• expiry 不自动伪造 external resource 已停止。
• 无法确认资源解绑/停止时进入 UNKNOWN + ReconciliationCase。
• Resource owner 与 lease holder 可以不同，且不会互相混淆。
45. Hidden State / PURE 验收
对 Module Host 做 crash/restart 测试：若恢复语义依赖 Kernel 不知道的内存/文件状态，则 FAIL。所有必须保留的语义状态必须追踪到 Packet、Resource、Continuation、Artifact 或 Canonical State。
PURE Module 在相同 module version/config/inputs 下重复执行 observable output 必须一致，并验证无 network/filesystem/clock/random/process/mutable external state 访问。
46. AI 实现时禁止自行做出的架构决定
1. 新增硬编码业务 NodeType。
2. 把 TRANSFORM / INVOKE / LISTEN 变成 Module enum。
3. 允许 Module 直接持有 raw canonical StateStore/SQLite。
4. 允许 Module 私有跨 Run durable semantic state。
5. 把 Packet consume 与数据删除混为一谈。
6. 允许 stale Attempt canonical commit。
7. 只做 Commit Fencing 而不做 Effect Fencing。
8. 用 sleep/polling/thread stack 代替 durable Suspension。
9. Resource existence 等于 permission。
10. Packet provenance 决定 Accounting membership。
11. 未知外部状态直接猜 SUCCESS / FAILED。
12. ModuleDefinition@version 原地改变 observable semantics。
13. 为了兼容旧项目降低新 Contract。
14. 把 EffectOperation 与 BudgetReservation 合并为一套状态机。
15. 让 Resource Lease 没有 release/revoke/expiry 出口。
16. 允许 executable Graph 含 unresolved module_ref@version。
发现必须改变上述任何一点：STOP → Architecture Finding → explicit review。不得在实现中顺手修改。
47. Architecture Invariants
Invariant	Requirement
M-INV-01	Every Module execution belongs to exactly one Run Attempt.
M-INV-02	Every Run belongs to exactly one immutable Activation.
M-INV-03	Every Activation pins immutable Module/Graph definitions.
M-INV-04	A Module cannot create canonical workflow truth directly.
M-INV-05	Every declared external effect requires corresponding capability authority.
M-INV-06	Capability authority is checked at actual effect boundaries.
M-INV-07	A stale Attempt cannot canonical-commit.
M-INV-08	A stale Attempt cannot initiate new mediated effects.
M-INV-09	Module semantic durable state must be Kernel-visible.
M-INV-10	Resource existence never implies permission.
M-INV-11	Dynamic provenance never determines Accounting membership.
M-INV-12	Suspension state is explicit and durable.
M-INV-13	Unknown external history is never converted to guessed success/failure.
M-INV-14	ModuleDefinition@version semantics are immutable.
M-INV-15	User-visible Node taxonomy cannot alter Kernel execution semantics.
M-INV-16	Every executable ModuleInstanceRevision MUST resolve to an immutable registered ModuleDefinition@version.
M-INV-17	Every Resource Lease MUST have a bounded lifecycle and a canonical release/revocation/expiry path. Lease expiry MUST NOT fabricate certainty about external resource state.
M-INV-18	EffectOperation state and BudgetReservation state are orthogonal facts and MUST NOT be collapsed into a single lifecycle or authority.
48. AI HANDOFF — 必须记住的十句话
1. Node 不是 Runtime primitive；Module 才是。
2. Runtime 只有一种 Module Contract，不存在硬编码 Transform/Invoke/Listen 类型体系。
3. ModuleDefinition 版本不可变；实际执行 pin ModuleInstanceRevision + GraphRevision。
4. Packet 是事实，Delivery 是投影，Activation 是不可变执行意图，Run 是 Attempt。
5. Module 无权决定 retry、下游调度、预算权威、canonical truth 或恢复裁决。
6. Capability 是权限，Resource 是状态句柄；两者必须分开。
7. Commit Fencing 防假结果；Effect Fencing 防假副作用。
8. Suspension 必须 durable；Continuation 只属于同一 Run Attempt 的主动等待。
9. UNKNOWN 必须进入 reconciliation，不得猜历史。
10. Provenance 解释“为什么发生”；静态 Graph containment 决定 Accounting membership。
49. Architecture Review Gate
任何实现若发现必须改变本 Contract 中的 Architecture Invariant、核心对象边界、fencing 语义、Activation binding、Suspension/Continuation 语义、Resource/Capability 区分或 UNKNOWN truth rule，必须停止实现并提出 Architecture Finding。
允许实现层自行决定：数据库索引、局部类名、语言/框架、内部 helper、非语义缓存、性能优化、日志格式等，只要 observable semantics 不改变。
50. 推荐最小 Phase 1–2 代码对象
建议最少对象：
- ModuleDefinition
- ModuleRegistry
- ModuleInstanceRevision
- GraphRevision
- Packet
- Delivery
- Activation
- Run
- ModuleResult
- RuntimeContext
- Value/Artifact Ref
- Canonical Event
不要在 Phase 1–2 提前实现完整 Resource Manager、Budget Engine、Recovery UI 或 Marketplace。
51. Phase 1–2 Definition of Done
Phase 1：
- 注册合法 PURE Module。
- 拒绝版本冲突 / schema 错误 / capability-effect mismatch。
- GraphRevision pin immutable ModuleInstanceRevision。
- unresolved module dependency 阻止 executable publication。

Phase 2：
- Trigger Packet → Delivery → Activation → Run。
- Completed → durable output → canonical Run success + Output Packet。
- Failed → canonical failed attempt。
- stale completion 被 fencing 拒绝。
- crash/replay 不改变 committed-history-derived activation binding。
52. 最终设计结论
Module 是一个版本化、无隐藏持久语义状态的执行能力；它接受由 immutable Activation 固定的 Packet 输入，通过 Kernel 发放且持续受 fencing 约束的 Capability 与 Resource 完成计算或副作用，并只返回 Completed、Failed 或带显式 durable Continuation 的 Suspended；它不拥有调度、Workflow truth、权限升级、Accounting authority 或恢复裁决权。
本报告已经吸收三项补丁：UNRESOLVED_MODULE_REFERENCE、Resource Lease bounded lifecycle、EffectOperation 与 BudgetReservation 正交状态机。该版本可作为 Phase 1–2 的冻结实现依据。
