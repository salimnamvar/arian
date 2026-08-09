# Layer Module and Function Contract Refactoring Plan

**Status:** Proposed implementation plan  
**Scope:** `src/arian`, tests, architecture checks, and developer documentation  
**Primary inputs:** `docs/rules/*.yaml`  
**Implementation owner:** Assigned refactoring agent  

## 1. Outcome

Introduce a small, dependency-safe module contract shared by every package,
then define layer-specific module contracts for `domain`, `application`,
`bootstrap`, `controller`, `service`, `repository`, `infrastructure`, and
`template`. Standardize function and method signatures around one function
protocol, typed `Result[T]` outcomes, explicit resource ownership, and a
documented execution model for synchronous, asynchronous, threaded, and
multi-process work.

The result must be a reduction in accidental inheritance, duplicated logic,
duplicate protocols, naming drift, hidden state, and dead code. The base
classes are conventions and lifecycle boundaries; they must not become a new
god object or a place for business logic.

## 2. Non-negotiable constraints from `docs/rules`

1. Dependencies point inward. `domain` remains pure; `bootstrap` is the only
   composition root. Layer-specific base classes may depend only on the shared
   utility base and contracts permitted for that layer.
2. Cross-layer capabilities are domain-owned protocols. Do not move concrete
   adapters or adapter-shaped protocols into `util`.
3. Every public symbol has one canonical import path. A move is completed by
   updating callers, deleting the old definition, and removing re-export
   shims.
4. Fallible functions return `Result[T]`; functions validate at entry, use the
   execution guard where required, catch external exceptions locally, log at
   the detection layer, and return exactly once. Only transport controllers
   raise transport exceptions.
5. Functions have one responsibility, explicit return annotations, no input
   mutation, documented preconditions/postconditions/invariants/side effects,
   and no more than 60 executable lines.
6. No module-level mutable state. Shared mutable state is synchronized; frozen
   values and immutable DTOs are preferred.
7. All I/O has configurable finite timeouts, retries are bounded, resources
   have deterministic cleanup, and ownership transfer is explicit.
8. Naming must be canonical across protocol, implementation, and callers. The
   existing repository convention uses `a_` for parameters (with documented
   framework and dunder exemptions), `_role` for injected attributes, and
   `<Capability>Protocol` for capability protocols.

## 3. Clarify “ROD” before implementation

`docs/rules` does not currently define the acronym `ROD`. Before changing
names, the implementation agent must add a short decision record under this
plan (or a linked architecture decision) that records what ROD means for this
repository and translates it into testable naming rules. Until that decision
is made, use the existing `naming.yaml` rules as the authoritative baseline:

- one name for one concept;
- verbs identify the same pipeline stage everywhere;
- arguments match across protocol, implementation, and caller;
- attributes identify injected roles and are protocol-typed;
- domain names do not leak `Service`, `Repository`, or `Infrastructure`;
- mapper names encode direction, such as `_row_to_entity`;
- no synonyms such as `run/process/execute` for the same operation.

## 4. Target contract design

### 4.1 Shared utility package

Create `arian.util` as the lowest-level shared package. It may import only the
Python standard library and must not import any Arian layer, domain DTO, config
model, adapter, or framework.

Proposed responsibilities:

- `BaseModule`: immutable identity metadata, lifecycle state, capability
  introspection, and a deterministic close/dispose hook. It must not own
  application services, global registries, logging setup, or business logic.
- `ModuleMetadata`: frozen value object containing canonical module name,
  layer, version, and declared execution capabilities.
- `ModuleState`: a small closed state model such as created, ready, closing,
  closed, and failed; transitions are explicit and testable.
- `FunctionProtocol`: generic structural contract for a callable operation,
  including its typed input/output contract and sync/async execution mode.
  It must remain generic and layer-neutral.
- `ExecutionMode` and `ConcurrencyMode` enums/value objects. These describe
  behavior; they do not silently create threads or processes.
- shared result/error helpers only if they do not duplicate the canonical
  domain `Result[T]`. Prefer moving `Result[T]` to `arian.util` only after an
  import-graph and API review; otherwise keep the current domain result and
  make the generic utility protocol compatible with it.

The base module should use composition for optional capabilities. Do not add
abstract methods that every layer must implement merely to satisfy inheritance.
Do not require every function to be a method: pure transformations should
remain functions.

### 4.2 Layer base modules

Each layer gets one canonical base module, for example
`arian/<layer>/base.py`, containing a thin `Base<Layer>Module` subclass of
`BaseModule` and only the invariants unique to that layer:

| Layer | Base-module responsibility | Must not do |
|---|---|---|
| `domain` | Pure model/port identity and invariant declarations | I/O, logging setup, adapters, outer imports |
| `application` | Use-case lifecycle and injected port inventory | Construct services, repositories, or infrastructure |
| `bootstrap` | Composition-root lifecycle and graph validation | Contain business workflows |
| `controller` | Transport metadata and result-to-transport mapping boundary | Validate business rules or construct adapters |
| `service` | Domain workflow identity and collaborator declarations | Import application/controller/infrastructure |
| `repository` | Persistence adapter identity and transaction/resource contract | Know application or controller concerns |
| `infrastructure` | External-resource ownership, timeout, retry, and cleanup contract | Orchestrate use cases |
| `template` | Rendering/template identity and renderer contract | Contain business or persistence logic |

If a layer has no meaningful invariant, its base class should be an empty
marker subclass or the layer should use `BaseModule` directly. Inheritance is
not required for standalone pure functions.

### 4.3 Function protocol and result policy

Define one canonical generic function contract with these documented fields:

- input type and validation responsibility;
- direct return type for proven infallible pure functions, otherwise `Result[T]`;
- sync or async execution mode;
- side effects and resource ownership;
- timeout, retry, cancellation, and idempotency behavior;
- concurrency safety and whether the callable is re-entrant.

Provide explicit sync and async protocol variants if static typing cannot
express both cleanly. Do not wrap synchronous functions in fake async methods
or make all methods async by default. Use adapters at an intentional boundary:
CLI remains sync at its transport edge and calls the async application through
the existing runner; native async callers use the async contract directly.

## 5. Refactoring workstreams

### Phase 0 — Baseline and inventory

1. Record the current test, lint, formatting, and strict Pyright baseline.
2. Build an AST inventory of every module, class, function, method, import,
   protocol, alias/re-export, mutable module variable, `raise`, `return`, and
   external I/O call.
3. Build a symbol reference graph to classify each symbol as live, test-only,
   unreachable, duplicate, compatibility shim, or uncertain.
4. Record all current layer-boundary exceptions, especially
   `arian.infrastructure.config`, and decide whether the shared data-only
   config should remain there or move to a neutral package.
5. Produce a migration table: current symbol, canonical target, callers,
   replacement, deletion condition, and tests affected. No deletion happens
   from guesswork.

### Phase 1 — Establish contracts without behavior changes

1. Add `arian.util` and the generic contracts with no layer imports.
2. Add the layer base modules and metadata/state tests.
3. Add contract tests proving that every concrete module can expose metadata,
   has deterministic lifecycle behavior, and does not acquire hidden global
   state.
4. Add a machine-readable module registry or AST checker only if it can be
   generated from source; do not maintain a manually duplicated registry.
5. Add architecture checks for allowed imports, canonical module locations,
   forbidden aliases, base-class dependency direction, and missing type
   annotations.

### Phase 2 — Normalize domain contracts first

1. Consolidate cross-layer protocols in `arian.domain` (or a domain-owned
   `ports` package) and remove narrower local protocol duplicates.
2. Move shared DTOs/value objects and the canonical result contract to their
   correct owner, updating all consumers in the same change.
3. Fix protocol/implementation signatures so the composition root type-checks
   without casts or `type: ignore`.
4. Make domain modules inherit the domain base only where identity/invariant
   behavior is useful; keep pure value objects and pure functions lightweight.
5. Delete old definitions and re-export shims immediately after all references
   are migrated.

### Phase 3 — Normalize each concrete layer

Refactor one layer at a time in dependency order: `domain`, `util`,
`repository`/`infrastructure`, `service`, `application`, `template`,
`bootstrap`, then `controller`.

For each module:

1. Make the module contract and public symbols explicit.
2. Rename methods, parameters, and attributes using the approved ROD decision
   and `naming.yaml`; update protocol and callers together.
3. Extract duplicated pipeline stages into one owner and one helper.
4. Separate pure transformations from I/O and state mutation.
5. Replace hidden construction with protocol-typed injection.
6. Convert fallible operations to the canonical `Result[T]` shape and retain
   transport exception translation only in controllers.
7. Bound function size/complexity, eliminate input mutation, and document
   contracts and ownership.
8. Remove dead code only after the reference graph and tests prove it is dead.

Specific focus:

- `application`: remove concrete infrastructure/config behavior from use-case
  construction; require edge capabilities from bootstrap; consolidate merged,
  separate, and grouped flows around one shared pipeline.
- `service`: ensure planners, builders, classifiers, analyzers, and
  materializers depend on domain protocols and do not duplicate DTOs.
- `repository`: move adapter protocols to domain where they cross boundaries;
  isolate persistence errors and resource ownership.
- `infrastructure`: make timeout/retry/cleanup contracts explicit and keep
  adapters replaceable; do not use infrastructure as a general utility dump.
- `template`: treat rendering as an injected capability with a stable domain
  or application-facing protocol; keep Jinja/template assets passive.
- `bootstrap`: construct the complete graph exactly once and validate all
  implementations against their protocols.
- `controller`: keep parsing and transport mapping only; remove duplicate
  business validation and pipeline logic.

### Phase 4 — Concurrency and execution model

1. Classify every operation as pure sync, fallible sync, native async,
   thread-compatible, process-compatible, or single-owner stateful.
2. Keep mutable state function-local or instance-owned and document the owner.
3. For threaded work, protect every shared write/read set with a lock,
   semaphore, atomic operation, or concurrent-safe structure. Prefer immutable
   DTOs and per-task state to locks.
4. For async work, make cancellation and timeout behavior part of the
   contract; never block the event loop with synchronous I/O.
5. For multi-process work, pass only serializable immutable inputs/results;
   never share live handles, locks, database connections, or mutable module
   state across processes. Process orchestration belongs at the outer edge
   (`bootstrap`/`infrastructure`).
6. Define bounded worker counts, queue/back-pressure behavior, cancellation,
   failure aggregation, and shutdown ownership. A concurrency mode must be an
   explicit injected policy, not an implicit behavior of `BaseModule`.
7. Add deterministic tests for race protection, cancellation, timeout,
   process serialization, partial failure, and clean shutdown.

### Phase 5 — Dead-code and leakage cleanup

1. Re-run the symbol graph after each layer migration.
2. Remove unreachable modules, unused methods, duplicate validators,
   duplicate mappers, stale tests, unused imports, and compatibility aliases.
3. Search for OOP leakage: concrete adapter types in inner layers, service or
   repository names in domain models, infrastructure construction outside
   bootstrap, mutable class/module state, transport exceptions below the
   controller, and inheritance used only to share unrelated implementation.
4. Search for DRY leakage: repeated validation, repeated result construction,
   repeated exception conversion, repeated path handling, repeated lifecycle
   code, and near-identical protocols.
5. For every deletion, retain either a replacement test or evidence that the
   behavior was unreachable and unreferenced.

### Phase 6 — Enforcement and handoff

Add CI checks that fail on:

- forbidden layer imports or cycles;
- base modules importing outer layers;
- duplicate protocol names/capabilities;
- public symbols with multiple canonical homes;
- missing explicit return annotations or unapproved `raise` statements;
- functions over 60 executable lines or over complexity 10;
- unbounded I/O, retries, or worker creation;
- mutable module-level state;
- unsynchronized shared mutation where statically detectable;
- protocol/implementation incompatibility under strict Pyright.

Update `docs/rules/index.yaml` only for rules that are genuinely general and
reusable. Keep project-specific migration decisions in this plan or an ADR.

## 6. Required tests and acceptance gates

Each phase must pass the existing suite plus new tests for:

- base module metadata, lifecycle, idempotent close, and invalid transitions;
- sync and async function protocol assignability;
- `Result[T]` success/failure behavior and single boundary translation;
- all layer import boundaries and canonical import paths;
- protocol contract tests for every concrete implementation;
- no shared mutable state and correct synchronization under concurrent access;
- timeout, retry, cancellation, resource cleanup, and process serialization;
- behavior parity for merged, separate, and grouped context generation;
- dead-code removal without loss of public CLI behavior.

Final gates:

```text
pytest
ruff check src tests
ruff format --check src tests
pyright
architecture/import-graph checks
symbol/dead-code report reviewed
```

The handoff is complete only when the implementation agent supplies the
symbol migration table, the ROD decision, changed canonical API list, deleted
code list, concurrency matrix, and test/lint/type-check results.

## 7. Agent assignment slices

These slices may be assigned independently, but each agent must preserve the
migration table and run the gates before handing off:

1. **Contract agent:** `arian.util`, generic base contracts, lifecycle and
   function protocol tests.
2. **Domain agent:** domain ports, DTO/result ownership, protocol assignability,
   and removal of duplicate protocol homes.
3. **Layer agents:** one agent per concrete layer, following the order in
   Phase 3 and changing production code/tests together.
4. **Concurrency agent:** execution-mode matrix, synchronization, timeout,
   cancellation, process boundaries, and deterministic tests.
5. **Architecture/enforcement agent:** AST checks, import graph, naming/ROD
   checks, dead-code reports, and CI integration.
6. **Integration agent:** bootstrap wiring, controller compatibility, end-to-end
   behavior, final cleanup, and documentation.

No agent may introduce a compatibility alias, bypass a protocol with a cast,
or delete a symbol without updating the migration table and validating its
references.

## 8. Risks and decisions to protect

- A universal base class can become a god object. Keep it metadata/lifecycle
  only and prefer protocols/composition for capabilities.
- Making every operation async can make sync code harder to use and can hide
  blocking I/O. Preserve native execution modes and adapt only at boundaries.
- A utility package can become a dependency back door. Enforce its zero-layer
  import rule in architecture tests.
- “Dead” code may be an external API. Check package exports, CLI entry points,
  documentation examples, and integration consumers before deletion.
- The current rules require `Result[T]` broadly while existing pure functions
  return direct values. Keep direct returns for genuinely infallible pure
  functions and require evidence in their contracts; do not mechanically wrap
  every function.
- The current application has defaults such as current-working-directory
  resolution and default config construction. Review each default against the
  composition-root rule and replace hidden infrastructure defaults with
  explicit injection where it is an edge capability.
