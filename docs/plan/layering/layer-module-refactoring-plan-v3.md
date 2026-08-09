# Fixed Module and Callable Schema — Recovery Plan and Agent Prompt

**Status:** Ready to assign  
**Purpose:** Correct the remaining failure in the layer refactoring: base
classes exist, but real functions and methods still have inconsistent names,
signatures, and contracts.  
**Supersedes for execution:** `layer-module-refactoring-plan-v2.md`  

## 1. Current audit

The latest implementation has made meaningful progress, but it has not
achieved the requested fixed schema.

### Completed or partially completed

- `arian.util` contains `BaseModule`, lifecycle metadata, and typed
  `SyncFunctionProtocol`/`AsyncFunctionProtocol` declarations.
- Most major application, service, repository, and infrastructure classes now
  inherit a layer base class.
- An architecture test checks that selected concrete classes adopt a base.
- A baseline audit and several cleanup commits exist.

### Still not achieved

- There is no single schema that every production function/method must satisfy.
- There is no canonical operation vocabulary enforced by code.
- Methods still use unrelated verbs and shapes: `build`, `build_context`,
  `plan`, `collect`, `load_content`, `materialize`, `render`, `write`,
  `generate`, `get_role`, `get_importance`, `save_file`, `find_symbols`, and
  others.
- The function protocols describe a callable with one input and one output,
  but most real methods have multiple arguments and are not assignable to
  those protocols.
- The module base gives identity/lifecycle metadata but does not require a
  canonical operational method such as `execute`.
- The conformance test uses a manually maintained exemption set. It does not
  prove that every source module, class, function, or method has been
  classified and conforms.
- Naming checks do not compare protocol names, implementation names, callers,
  arguments, attributes, and tests as one symbol contract.
- `Result[T]`, validation, single return, exception boundaries, timeouts, and
  concurrency are not represented in one machine-readable callable schema.

The next agent must not add more marker classes or more isolated tests. The
next task is to define the vocabulary and migrate real call sites to it.

## 2. Agent prompt

> Continue the layer refactoring using this document as the binding prompt.
> The required outcome is a fixed, enforceable schema for every production
> module, class, function, and method. Do not interpret “common schema” as
> merely inheriting `BaseModule`. Do not count a base class, enum, docstring,
> or manually added exemption as compliance.
>
> First create the complete inventory and canonical naming dictionary below.
> Then implement the schema and migrate production code and all callers to it.
> Every renamed symbol must be changed consistently in protocols,
> implementations, bootstrap wiring, tests, and documentation. Delete old
> names and shims after migration; do not preserve parallel names.
>
> Work in bounded milestones. After every milestone run the relevant tests and
> make a conventional commit. Do not squash the commits. Use messages in the
> form `<type>(<scope>): <imperative summary>`, for example
> `refactor(naming): normalize service operation names` or
> `test(architecture): enforce callable schema`. At every update report the
> violation count before and after, checks run, and commit hash.

## 3. The fixed schema to implement

### 3.1 Module schema

Every operational production module must have one canonical module contract:

```text
ModuleContract
├── module_name: canonical dotted path
├── layer: domain | application | bootstrap | controller | service |
│          repository | infrastructure | template | util
├── module_kind: pure | use_case | workflow | adapter | transport |
│                composition | renderer | lifecycle
├── schema_version: literal version
├── execution_mode: sync | async
├── concurrency_mode: single_owner | thread_safe | process_safe
├── input_type / output_type
├── result_policy: direct | Result[T]
├── lifecycle: initialize -> execute -> close
├── side_effects: explicit list
├── resource_owner: explicit owner or none
├── timeout_policy: finite value or none for pure code
├── retry_policy: bounded value or none
└── cancellation_policy: explicit value
```

The contract must be typed and machine-readable. Do not use an untyped
`dict[str, Any]`. It may be a frozen dataclass plus a protocol, or an
equivalent typed model. `BaseModule` must expose this contract and define the
common lifecycle methods:

```python
initialize() -> Result[None]
execute(a_input: InputT) -> Result[OutputT]
close() -> Result[None]
```

For a genuinely infallible pure module, direct output is allowed only through
an explicitly typed pure-function contract. Operational modules must use
`Result[T]`. Async modules must use the native equivalent:

```python
async initialize() -> Result[None]
async execute(a_input: InputT) -> Result[OutputT]
async close() -> Result[None]
```

Do not force sync code to become async. Do not add both `build` and `execute`
as equivalent public entry points. One is canonical; the other must be
removed or made a private implementation detail with a distinct role.

### 3.2 Function and method schema

Every non-dunder production function and method must be classified as one of:

```text
pure_transform | validate | execute | collect | load | save | plan |
materialize | render | map | notify | configure | initialize | close
```

No new verb may be introduced without updating the vocabulary and its checker.
The vocabulary is intentionally small. In particular:

- replace `get_*` with the specific read operation (`load`, `find`, or a
  property) selected in the dictionary;
- replace `run`, `process`, `perform`, `do_*`, and `generate` with the exact
  operation slot;
- use `save` for persistence writes, not `save_file`, `save_symbol`, etc.;
  the typed input identifies the entity;
- use one `plan`, one `materialize`, one `render`, one `collect`, and one
  `execute` name per capability, not synonyms for the same stage;
- private helpers use the same approved verb plus a specific object suffix,
  such as `_validate_paths`, `_map_row_to_file`, or `_load_content`.

Each callable must have this schema:

```text
CallableContract
├── callable_name: approved verb or approved private form
├── callable_kind: function | method | protocol_method | constructor
├── owner_module and owner_layer
├── input signature: exact typed parameters in canonical order
├── output signature: exact typed return
├── execution mode: sync | async
├── result policy: direct | Result[T]
├── validation owner and preconditions
├── postconditions and invariants
├── side effects and resource ownership
├── timeout/retry/cancellation policy
├── concurrency/re-entrancy policy
└── canonical callers and implementations
```

The contract must be checked from the AST and type information. Docstrings may
explain the contract but may not be the only enforcement mechanism.

### 3.3 Signature and argument rules

- Use one exact signature in the protocol, implementation, and caller.
- Use `a_` for ordinary parameters, excluding only `self`, `cls`, dunder or
  standard-library/framework signatures documented by a targeted exemption.
- Do not use `*args`, `**kwargs`, `Any`, or untyped tuples to evade the schema.
- Use one request DTO for multi-field operations rather than a growing list of
  loosely ordered arguments.
- Inject collaborators through constructor parameters typed as domain-owned
  protocols; store them using canonical `_role` attributes.
- Use immutable domain DTOs for cross-layer inputs and outputs.
- Constructors initialize dependencies only; operational work belongs in the
  canonical lifecycle/operation method.

## 4. Required canonical operation map

Before editing production code, create
`docs/plan/layering/callable-contract-matrix.yaml`. It must contain every
concrete class, public method, private helper, protocol method, and module-level
function with its old name, new canonical name, signature, layer, result policy,
and callers.

At minimum, resolve the current names as follows. The agent may choose a
better name only by recording the reason in the matrix and updating the
vocabulary checker:

| Current family | Canonical operation | Required action |
|---|---|---|
| `Application.build_context` | `Application.execute` | Use one application use-case entry point. |
| `ContextBuilder.build` | `ContextBuilder.execute` | Use the service execution slot with `BuildRequest`. |
| `ContextPlanner.plan` | `ContextPlanner.plan` | Retain because it is the canonical planning stage. |
| `FileCollector.collect` | `FileCollector.collect` | Retain as the canonical collection stage. |
| `ContextBuilder.load_content` | `ContextBuilder.load` | Use the canonical loading verb. |
| `ContextMaterializer.materialize` | `ContextMaterializer.materialize` | Retain as the canonical materialization stage. |
| `MarkdownRenderer.render` | `MarkdownRenderer.render` | Retain as the canonical rendering stage. |
| `FileOutputWriter.write` | `FileOutputWriter.save` | Use the persistence vocabulary. |
| `SummaryService.generate` | `SummaryService.execute` or `render` | Select one based on whether it is workflow or rendering, then remove the other concept. |
| `get_role`, `get_importance`, `get_branch`, `get_changed_files` | `load`/`find`/property or exact domain verb | Record the choice; no generic `get_` remains. |
| `save_file`, `save_symbol`, `save_dependency`, etc. | `save` | Typed entity input distinguishes the operation. |
| `_row_to_file`, `_row_to_symbol`, etc. | `_map_row_to_file`, `_map_row_to_symbol` | Use the approved mapper verb consistently. |
| `retry_*` | `execute` through a retry policy or one canonical retry helper | Do not maintain separate semantic names for sync/async behavior without a contract reason. |

The matrix is authoritative. The agent must not mechanically rename distinct
operations to the same word when that would destroy their semantic contract;
instead, each operation must occupy a declared vocabulary slot. The violation
is arbitrary synonym drift, not the existence of domain-specific nouns.

## 5. Enforcement implementation

Add `tests/architecture/test_callable_contracts.py` or an equivalent checker
that fails when:

1. a production class is not classified as a value object, protocol,
   framework type, exception, or concrete module with the correct base;
2. a concrete module lacks a module contract;
3. a public operation lacks the canonical lifecycle/operation slot;
4. a method/function name is outside the approved vocabulary or an approved
   documented exemption;
5. a protocol method and implementation method differ in name, parameters,
   asyncness, or return type;
6. a method uses a non-canonical `get_*`, `run`, `process`, `generate`, or
   `do_*` synonym;
7. a callable lacks an explicit return annotation or uses `Any`/catch-all
   arguments without a targeted exemption;
8. a fallible operation returns a direct value instead of `Result[T]`;
9. a lower layer raises or imports a concrete outer-layer adapter;
10. a module contains more than one public synonym for the same operation;
11. a function exceeds the project limit or violates the single-responsibility
    and resource contract checks.

The test must discover source files dynamically. A manually curated list of
“approved” classes is not sufficient; only narrowly defined categories such
as dataclasses, enums, exceptions, protocols, and framework-required classes
may be exempted by AST characteristics and a reason.

## 6. Migration phases and conventional commits

### Phase A — Inventory and vocabulary

Create the complete callable matrix and ROD/naming decision. Do not change
behavior yet. Count every violation.

Commit: `docs(refactor): define callable vocabulary and contract matrix`

### Phase B — Contract implementation

Implement the typed `ModuleContract`, `CallableContract`, lifecycle contract,
and AST/type checker. Make the checker fail against the current code so that
progress is measurable.

Commit: `test(architecture): add executable module and callable contract checks`

### Phase C — Canonicalize public operation names

Migrate domain protocols first, then implementations and all callers. Remove
old public names in the same change. Preserve only language/framework dunder
exceptions. Update tests to call the canonical names.

Commit per layer:

- `refactor(domain): canonicalize domain operation names`
- `refactor(repository): canonicalize repository operations`
- `refactor(infrastructure): canonicalize adapter operations`
- `refactor(service): canonicalize workflow operations`
- `refactor(application): canonicalize use-case execution`
- `refactor(template): canonicalize rendering operations`
- `refactor(bootstrap): canonicalize lifecycle operations`
- `refactor(controller): canonicalize transport operations`

### Phase D — Canonicalize private helpers and signatures

Normalize private helper verbs, argument prefixes, DTO usage, attribute names,
protocol/implementation signatures, return types, and asyncness. Remove
`Any`, arbitrary `*args/**kwargs`, and mismatched protocol copies.

Commit: `refactor(signatures): align callable arguments and return contracts`

### Phase E — Result, concurrency, and resource contracts

Apply the callable schema to Result/error behavior, timeout/retry,
cancellation, ownership, thread safety, and process serialization. Add tests
for actual operations rather than enum values only.

Commit: `refactor(execution): align result concurrency and resource contracts`

### Phase F — Dead code and final enforcement

Remove stale names, aliases, duplicate functions, unused protocols, dead
classes, and obsolete tests only after the matrix proves no references remain.
Make the checker and all quality gates pass.

Commit: `refactor(cleanup): remove obsolete callable names and dead code`

Final documentation commit: `docs(refactor): document enforced callable schema`

## 7. Definition of done

The task is complete only when:

- the callable matrix contains every production function/method and has zero
  unclassified entries;
- every operational module exposes the fixed typed module contract;
- every operational module has exactly one canonical public execution slot and
  the appropriate declared stage slots;
- every protocol, implementation, and caller uses identical canonical names
  and compatible typed signatures;
- no arbitrary synonym verbs remain without an explicit documented exemption;
- no `Any`, catch-all arguments, or untyped outputs bypass the contract;
- module/function conformance tests dynamically discover and enforce the rules;
- Result, exception, validation, timeout, resource, async, thread, and process
  policies are represented and tested;
- all behavior tests pass after callers are migrated;
- `ruff check`, `ruff format --check`, strict `pyright`, architecture tests,
  and the full pytest suite pass in the documented environment;
- every milestone has a conventional commit and the agent reports each hash;
- the final violation count is zero, not merely lower than the baseline.

Passing inheritance tests, passing Ruff, or having a populated base class is
not evidence of completion by itself.
