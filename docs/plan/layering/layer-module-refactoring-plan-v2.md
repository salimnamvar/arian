# Layer Contract Refactoring — Audit, Recovery Plan, and Agent Prompt

**Status:** Ready to assign  
**Date:** 2026-08-09  
**Supersedes:** `docs/plan/layering/layer-module-refactoring-plan.md` as the execution guide  
**Scope:** All Python code under `src/arian`, tests, architecture checks, and required documentation  

## 1. Audit conclusion

The previous agent completed the scaffolding portion, not the requested
refactoring. The current repository has a shared utility package, eight layer
base classes, exports, and basic tests, but the common schema is not applied to
the actual modules, classes, methods, and functions.

### Evidence-based status

| Goal | Status | Evidence |
|---|---|---|
| Shared `arian.util` package exists | Partial | `util/base.py` and `util/protocol.py` exist. |
| Every named layer has a base class | Achieved as scaffolding | Eight `base.py` files exist and tests instantiate them. |
| Production modules inherit the appropriate layer base | Not achieved | `rg` shows only the base classes inherit `BaseModule`; `Application`, services, repositories, infrastructure adapters, controller code, and bootstrap components do not adopt their bases. |
| One common module schema | Not achieved | Metadata/lifecycle exists only on standalone base objects; real modules have no required schema or conformance test. |
| One common function/method schema | Not achieved | `FunctionProtocol.__call__` uses `*args: Any, **kwargs: Any -> Any`; it does not type or enforce actual function signatures, `Result[T]`, contracts, or sync/async correctness. |
| Consistent naming enforcement | Not achieved | Existing names still include `get_*`, `process`-style variants, framework exemptions, and no AST naming checker enforces arguments, attributes, methods, or protocol/implementation parity. |
| Result-driven behavior | Partial | Many paths use `Result`, but direct-return functions remain widespread and several functions/classes still raise. No conformance checker proves the policy. |
| OOP leakage fixed | Not achieved | Base inheritance was added without migrating concrete classes; this leaves the requested architecture unchanged and risks marker-class theater. |
| DRY leakage fixed | Not achieved | No duplicate-function, duplicate-validator, duplicate-mapper, or repeated-schema report was delivered. |
| Async/sync/concurrency/process contract | Not achieved | Enums describe modes, but no executable policy, capability validation, cancellation/timeout/process contract, or concurrency tests exist. |
| Dead code removed | Partial | Two domain protocols were removed, but there is no repository-wide reference/dead-code report proving broader cleanup. |
| ROD defined and enforced | Not achieved | `docs/rules` does not define ROD and no decision record or checker was added. |
| Quality gates | Partial | Ruff passes. Pyright currently reports 272 errors in the available environment. The full pytest run must be recorded before claiming completion. |
| Conventional commits during implementation | Not evidenced | The existing commits are conventional in places, but the prior plan did not make commit checkpoints a hard acceptance criterion. |

**Overall assessment:** foundational scaffolding is approximately 15–20% of the
requested outcome. Do not report the work as complete until real production
modules and functions conform and the enforcement checks prove it.

## 2. Agent prompt — execute this plan

> You are implementing the layer contract refactoring in this repository.
> Read `docs/rules/*.yaml` and this file before changing code. The goal is
> not to create marker base classes. The goal is to make the real modules,
> classes, methods, functions, arguments, attributes, protocols, return
> values, error handling, and concurrency behavior follow one measurable
> architecture.
>
> Preserve behavior unless a rule violation requires a change. Do not perform
> broad speculative rewrites. Work in small vertical slices, run the required
> checks after each slice, and make a conventional commit after every completed
> milestone. Do not squash the milestone commits. Every commit message must be
> `<type>(<scope>): <imperative summary>` and use only approved types such as
> `feat`, `refactor`, `test`, `fix`, `docs`, `chore`, or `perf`.
>
> At each milestone report: files changed, symbols migrated, checks run,
> remaining violations, and the commit hash. Never claim a phase is complete
> because a base file or test exists; completion requires production adoption
> plus an automated enforcement test.

## 3. Target architecture: define the schemas first

### 3.1 Common module schema

Define one typed, documented schema for every concrete module that participates
in the architecture. The schema must include:

- canonical module name and layer;
- module version/schema version;
- declared public capabilities;
- lifecycle state and ownership of resources;
- execution mode: `sync` or native `async`;
- concurrency classification: single-owner, thread-safe, or process-safe;
- timeout/cancellation/retry policy where applicable;
- injected collaborators, each typed as a protocol;
- side effects and resource cleanup contract;
- validation and failure/result policy.

Implement this in `arian.util` as a genuinely typed contract. Keep the shared
base dependency-free from Arian layers. Do not use an untyped `dict[str, Any]`
as the schema. Metadata may be immutable, but runtime capability storage must
not become hidden mutable global state. Prefer immutable declarations and
explicit constructor injection.

Every concrete production class that is a module/service/adapter/use case
must either inherit the correct `Base<Layer>Module` or explicitly document why
it is a pure value object, protocol, framework-required class, or standalone
function. Add an AST/conformance test that enumerates every concrete class and
fails when a class is unclassified.

### 3.2 Common function/method schema

Define a typed function contract that can represent the real callable shape;
`*args: Any, **kwargs: Any -> Any` is not sufficient. Use generic protocols or
separate typed sync/async protocols with input and output type variables.

Every production function and method must declare:

- canonical name and role;
- typed parameters and explicit return type;
- input validation owner and preconditions;
- postconditions and internal invariants;
- direct return type if truly infallible, otherwise `Result[T]`;
- side effects and resource ownership;
- sync/async and concurrency behavior;
- timeout/retry/cancellation/idempotency behavior if relevant.

Use decorators, structured docstrings, annotations, or an equivalent
machine-readable representation, but select one canonical mechanism and test
it. Do not require every pure function to become a class method. Do not make
every function async merely to satisfy a schema.

### 3.3 Naming schema

The repository rules already establish `a_` parameter prefixes, `_role`
injected attributes, `<Capability>Protocol`, domain nouns, directional mapper
names, and stable pipeline verbs. ROD is currently undefined. Before renaming
production symbols, create an ADR or section in this plan that defines ROD in
plain language and maps each rule to a checker.

The checker must enforce at least:

- same concept has the same name across protocol, implementation, caller, and
  tests;
- all non-exempt parameters use the approved prefix;
- injected collaborators use protocol-typed private attributes;
- no layer-prefixed domain types such as `ServicePlan` for domain concepts;
- no synonym drift for the same stage (`build`, `run`, `execute`, `process`);
- mapper names follow `_source_to_target` direction;
- public names are unique and have one canonical import path.

Framework/dunder signatures require explicit exemptions with a reason. Do not
silence violations with blanket `# noqa` comments.

## 4. Required execution sequence

### Milestone 0 — Baseline and commit

Create a machine-readable audit report under `docs/plan/layering` containing:

- all concrete classes and their current layer/base status;
- all functions/methods with line count, return count, raises, annotations,
  parameter names, I/O, shared state, and async/sync status;
- all protocols and their definitions/implementations;
- all duplicate symbols, aliases, dead-code candidates, and layer violations;
- current test, Ruff, and Pyright results with environment notes.

Commit: `docs(refactor): record layer contract baseline`

### Milestone 1 — Correct and prove the shared contract

Review the existing `BaseModule` before reuse. Its current mutable capability
dictionary, runtime exceptions, and untyped function protocol must be assessed
against the rules. Replace or narrow it as necessary.

Implement:

1. typed immutable module metadata and explicit lifecycle/resource ownership;
2. typed sync and async function protocols;
3. typed result/error contract without duplicating `Result[T]` ownership;
4. execution and concurrency declarations that are descriptive, not magical;
5. conformance tests with real typed sync and async callables;
6. utility purity test: `arian.util` imports only the standard library and
   itself.

Commit: `refactor(util): establish typed module and function contracts`

### Milestone 2 — Adopt the schema in production, layer by layer

Migrate actual classes, not just base classes, in this order:

1. domain models/ports and pure functions;
2. repository and infrastructure adapters;
3. services (`ContextBuilder`, planner, materializer, classifier, analyzer,
   summary service);
4. application validator/orchestrator;
5. template/rendering boundary;
6. bootstrap/lifespan/wiring;
7. controller/CLI transport boundary.

For each concrete class, record its base class, module metadata, collaborator
protocols, execution mode, concurrency mode, and ownership contract. For each
function/method, normalize names/signatures and apply the function schema.

No class may inherit a base only to satisfy a count. If a class has no module
lifecycle or resource responsibility, keep it as a value object or pure
function and mark the exemption in the conformance report.

Commit after each layer, for example:

- `refactor(domain): align domain contracts and naming`
- `refactor(repository): align repository adapters with module schema`
- `refactor(infrastructure): align resource adapters and failure contracts`
- `refactor(service): align workflow services and function contracts`
- `refactor(application): align use-case orchestration contracts`
- `refactor(template): align rendering contract`
- `refactor(bootstrap): align composition-root lifecycle`
- `refactor(controller): align transport boundary and naming`

### Milestone 3 — Result, error, and single-exit conformance

Audit every fallible function. Convert expected validation and external
failures to the canonical `Result[T]` contract, catch specific external
exceptions locally, preserve context in logs/results, and keep transport
`raise` statements only at controller/framework boundaries.

Do not mechanically wrap infallible pure computations. Instead, document the
proof that they cannot fail under their typed/prevalidated inputs.

Add AST checks for return count, forbidden raises by layer, missing return
annotations, bare exceptions, and fallible functions that return `None` or
untyped tuples.

Commit: `refactor(errors): enforce result and boundary error contracts`

### Milestone 4 — Concurrency and resource ownership

Create a concurrency matrix for every I/O and pipeline operation:

| Operation | Mode | Shared state | Synchronization | Timeout | Retry | Cancellation | Process-safe |
|---|---|---|---|---|---|---|---|

Implement only the concurrency required by the application. Native async
functions must not block the event loop. Threaded work must protect every
shared mutable write/read set. Multi-process work may pass only serializable
immutable DTOs and must not share live handles, locks, connections, or module
state. All resources must close deterministically.

Add tests for cancellation, timeout, bounded retry, race protection, resource
cleanup, process serialization, and partial failure. Descriptive enum values
alone do not satisfy this milestone.

Commit: `refactor(concurrency): enforce execution and resource contracts`

### Milestone 5 — DRY, OOP leakage, and dead code

Produce before/after reports for:

- duplicate validators and path checks;
- duplicate result/error conversion;
- duplicate mappers and protocol definitions;
- repeated pipeline branches;
- concrete adapter imports in inner layers;
- infrastructure construction outside bootstrap;
- domain models containing outer-layer concepts;
- stateful classes used where pure functions or composition are sufficient;
- unused symbols, aliases, stale exports, and unreachable modules.

Move each rule to one owner, update all references, then delete old definitions
and shims in the same commit. Do not preserve aliases unless a written
deprecation window is approved.

Commit: `refactor(cleanup): remove duplicated leaked and dead code`

### Milestone 6 — Enforcement and final handoff

Add CI tests/checkers for:

- module schema and concrete-class adoption;
- function schema and typed protocol assignability;
- parameter/attribute/method naming;
- canonical import paths and duplicate symbols;
- layer boundaries and utility purity;
- Result/raise/return contracts;
- function length/complexity and mutable module state;
- timeout/retry/resource/concurrency declarations;
- strict Pyright and runtime behavior.

Update documentation only after the checks are real and passing.

Commit: `test(architecture): enforce layer and callable contracts`

Final commit, only after all gates pass: `docs(refactor): document completed layer contracts`

## 5. Definition of done

The agent may claim completion only when all are true:

- every concrete production class is classified and either adopts the correct
  layer base or has a tested documented exemption;
- every production function/method has the common schema and naming contract;
- the function protocol has typed sync/async signatures and no `Any` catch-all
  callable contract;
- protocol implementations pass strict static assignability without casts;
- Result/raise/single-exit rules are enforced automatically;
- all layer boundaries, canonical imports, and utility purity pass;
- concurrency/resource matrix and tests are complete for actual operations;
- duplicate, leaked, aliased, and dead symbols have an evidence-backed report;
- `pytest`, `ruff check`, `ruff format --check`, and `pyright` pass in the
  documented project environment;
- all milestone changes are separated into conventional commits and the final
  handoff includes commit hashes and remaining known limitations (which must
  be zero for a complete status).

Passing tests for newly added base classes alone is explicitly insufficient.

## 6. Agent handoff format

At the end of each progress update, use:

```text
Milestone: <number and name>
Completed: <concrete production symbols migrated>
Checks: <commands and pass/fail results>
Violations remaining: <count and categories>
Commit: <conventional commit hash and message>
Next: <next bounded task>
```

If a rule conflicts with existing behavior, stop and document the conflict in
the audit report before choosing a compatibility strategy. Do not silently
weaken the schema, add aliases, widen types to `Any`, or declare scaffolding
complete.
