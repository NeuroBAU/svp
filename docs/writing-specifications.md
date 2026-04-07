# Writing Specifications for AI-Assisted Software Engineering

A specification is not a bureaucratic artifact. It is a thinking tool. In AI-assisted coding, the quality of the implementation is capped by the quality of the specification. If the spec is vague, the code will be vague. If the spec confuses goals, mechanisms, and edge cases, the resulting system will do the same.

This document covers the concepts that matter for writing good specifications. Most of what follows is aimed at the **blueprint** — the architectural decomposition that SVP's agents produce from your spec. But several concepts also directly shape the **stakeholder spec** itself: problem definition, scope, invariants, enumerations, error semantics, and testability. When you sharpen these in your spec, the blueprint inherits that precision. When you leave them vague, the blueprint must guess.

---

## The Two Documents

SVP produces two key documents during the first three stages:

The **stakeholder spec** is yours. You write it with the help of the Socratic dialog agent. It describes *what* your software should do, in your language, using your domain concepts. It says nothing about functions, classes, or modules. It talks about behavior: "the system accepts a configuration file and fills in missing fields from sensible defaults." The spec is the single source of truth. Everything downstream — every test, every line of code — traces back to a sentence in the spec.

The **blueprint** is the LLM's translation of your spec into software architecture. An agent reads your spec and decomposes it into units with signatures, contracts, and dependencies. You approve the blueprint, but you do not write it. The blueprint is written in plain English with embedded code signatures — not source code, but the *shape* of the code.

Two things follow from the blueprint being in plain English rather than opaque code. First, it is documentation — you can feed it to an LLM and ask "why does unit 7 produce this output?" and get an answer in your domain terms. Second, it teaches you — as your design skills grow, you start noticing vague contracts and gaps between what your spec said and what the blueprint had to infer.

**What belongs where.** The spec defines the problem, the scope, the domain invariants, the enumerations of valid values, the error semantics, and the testability criteria. The blueprint defines the units, signatures, contracts, dispatch tables, data models, and state machines. The concepts below apply to both, but the document they belong in differs — the text notes which.

---

## Separating the Problem from the Solution

*Applies to: spec*

Most weak specifications jump too early into implementation language. "Build a Python class that uses Redis and async workers" is a solution. "Maintain low-latency access to session state with bounded inconsistency under concurrent updates" is the actual problem. The second statement is far more useful because it identifies the objective and the constraints. Once those are clear, many implementations become possible.

A spec should begin by naming the system's purpose in concrete terms: what inputs exist, what outputs are expected, what environment the system lives in, and what outcome counts as success. Compare "build a tool that processes student submissions" with "build a service that ingests programming assignment submissions, validates them against an assignment schema, stores them durably, and returns a structured status report within two seconds for 95% of requests." The second version gives the problem shape.

This matters enormously for AI-assisted coding. AI is very good at expanding local structure and very bad at rescuing an ambiguous plan. Give it a blurry request and it will generate plausible blur. Give it a precise specification and it can produce useful, testable components. The human should remain responsible for top-down design — deciding what problem is being solved, what constraints matter, what must never happen, and where flexibility is allowed. The AI then becomes a powerful subordinate for refinement rather than a source of architectural drift.

---

## Scope

*Applies to: spec*

Scope defines what the system is responsible for and what it is explicitly not responsible for. This matters because AI models tend to fill in omitted boundaries with assumptions. If the spec does not say whether authentication is in scope, the model may invent a half-baked auth system. If the spec does not say whether malformed input is expected, the model may silently ignore it.

Scope is not administrative trimming. It is the act of defining the boundary of responsibility. A good spec says: this module owns parsing but not persistence; this service owns authorization checks but not identity management. Once those boundaries are stated, implementation becomes much more reliable.

---

## Invariants

*Applies to: spec (domain invariants) and blueprint (representation and temporal invariants)*

An invariant is a condition that must remain true throughout the life of the system. Invariants are stronger than goals and more durable than examples. A goal says what we hope the system does. An invariant says what must never be violated.

Invariants come in layers:

- **Domain invariants** — derived from the problem itself. An order cannot be shipped before it exists. A user cannot have a negative balance unless overdrafts are explicitly supported. *These belong in the spec.*
- **Representation invariants** — tied to internal data structure consistency. A binary search tree maintains ordering. A cache index points only to existing entries. *These belong in the blueprint.*
- **Temporal invariants** — concerning state transitions over time. A request can move from pending to approved or rejected, but never back to pending after finalization. *Domain-level temporal invariants belong in the spec; implementation-level ones in the blueprint.*

A useful habit is to phrase invariants in language that could almost become an assertion. "Documents should usually save correctly" is not an invariant. "Every saved revision has a monotonically increasing revision number and points to exactly one parent revision except the root" is. You can test it. You can reason from it. You can design around it.

In SVP's own build, invariants prevented entire classes of bugs. "No function that modifies pipeline state may mutate its input — it must return a new copy" is one. "Every gate ID that appears in the routing table must also appear in the preparation script's registry" is another. A single invariant applied universally prevents a bug from appearing in any unit, forever. When you find yourself fixing the same kind of bug in multiple places, you are missing an invariant.

---

## Signatures

*Applies to: blueprint*

A signature is the formal shape of an operation: what it takes, what it returns, what errors it may have. In strong engineering cultures, signatures are treated as mini-specifications. Compare `process(x)` returning `y` with `authorize(request: AccessRequest, policy: Policy) -> AuthorizationDecision`. The second signature already communicates the conceptual model.

For AI-assisted coding, signatures are crucial because they constrain the search space. Well-designed signatures narrow the plausible completions dramatically. But to get the full benefit, signatures should be designed around domain concepts, not accidental implementation details. `reconcile(entries: Sequence[LedgerEntry], tolerance: MoneyTolerance) -> ReconciliationReport` is much more useful than `reconcileLedgerEntries(entries, config, mode)`.

An especially good practice is to make illegal states hard to express in the signature itself. If an operation requires a parsed object, its signature should not accept raw text. If a function operates only on validated submissions, make that explicit: `grade(validated_submission: ValidatedSubmission, rubric: Rubric) -> GradeReport` is better than `grade(text, rubric)`.

---

## Contracts

*Applies to: blueprint*

A contract specifies the preconditions, postconditions, and permitted side effects of an operation. Signatures tell you shape; contracts tell you obligation.

Consider `reserveInventory(item, quantity)`. Is quantity allowed to be zero? Does the reservation expire? Is the operation idempotent? Does it decrement stock immediately or tentatively? A contract answers these: quantity must be positive, the item must exist, the function is idempotent with respect to a request ID, successful reservation reduces available inventory atomically, expiration time is included in the result, and insufficient stock yields a structured failure without side effects. That is a real specification.

There is a deep connection between invariants and contracts. Invariants describe what must always hold. Contracts describe how individual operations preserve or transform those truths. If an invariant says "a published grade must have an audit trail," then every contract that can lead to publication must write an audit record — the publication function, the override function, the batch import function. Once you think this way, a spec becomes a map of preserved truths rather than a pile of feature ideas.

---

## Dispatch and Dispatch Tables

*Applies to: blueprint*

Dispatch is the rule by which a system chooses what behavior to execute for a given input, type, state, or command. A great deal of software complexity is not in computation but in branching. Systems become hard to understand not because individual branches are difficult, but because the set of possible branches is poorly organized.

A good spec should identify dispatch points explicitly: these are the cases the system distinguishes, this is the basis of differentiation, these are the allowed handlers, and this is how unrecognized cases are treated. AI models are especially prone to solving local cases by adding another conditional rather than discovering the deeper structure.

A dispatch table is a data-driven mapping from keys to behaviors. Instead of spreading routing logic through code, you represent it explicitly. The virtue of dispatch tables is not merely aesthetic — they make the set of cases visible, enumerable, and testable. If every supported command must have a handler, you can evaluate completeness by comparing the command set with the dispatch table keys.

SVP uses six per-language dispatch tables (`SIGNATURE_PARSERS`, `STUB_GENERATORS`, `TEST_OUTPUT_PARSERS`, `QUALITY_RUNNERS`, `PROJECT_ASSEMBLERS`, `COMPLIANCE_SCANNERS`). Adding a new language means adding one entry to each table. The table structure makes missing entries obvious and extension predictable.

Dispatch tables are appropriate when behavior selection is data-like and case-based. They are less appropriate when logic depends on rich semantic interaction that cannot be cleanly captured by a lookup. The spec writer's job is to recognize when the problem has a finite case structure that benefits from one.

---

## Data Models, State Machines, and Error Semantics

*Data models and error semantics apply to: spec. State machines apply to: both.*

**Data models.** A spec should identify the core entities, their fields, their identities, their relationships, and their lifecycle states. It should distinguish essential properties from derived properties and say what is authoritative, what is cached, and what is immutable. Without this, generated code tends to entangle transport schemas, persistence schemas, and domain objects into one confused mass.

**State machines.** If an entity changes over time, the spec should define its legal states and transitions. This prevents a common AI failure mode: implementing operations independently without a coherent lifecycle model. A state machine turns vague language like "when an order is processed" into a precise transition system: created, paid, packed, shipped, delivered, cancelled, returned. Each transition carries preconditions, postconditions, and side effects.

**Error semantics.** One of the clearest signs of a poor spec is that it describes success cases vividly and failure cases vaguely. A good spec states what categories of failure exist, how they are represented, whether retries are safe, whether operations are idempotent, whether partial completion is possible, and what cleanup behavior is required. If your spec says only "handle errors gracefully," you are not specifying — you are wishing.

---

## Enumerations

*Applies to: spec*

Listing all valid values explicitly rather than describing them in prose. "The linter can be ruff, flake8, pylint, or none" is an enumeration. "The linter is configurable" is not — it leaves the valid values unspecified, and the implementation agent will have to guess.

Enumerations are the single most common source of spec gaps. Every time your spec says "one of several options" or "a valid value," ask yourself: can I list them all? If you can, list them. In SVP's own build, Bug 50 found that six validation sets — linters, formatters, type checkers, import sorters, commit styles, changelog formats — were described in prose but never enumerated. The implementation agents guessed, and guessed differently from each other.

---

## Nonfunctional Requirements and Observability

*Applies to: spec*

Many poor specs describe what the system should do but not what qualities it must exhibit while doing it. If performance, latency, reliability, security, or privacy matter, they must be specified. AI-generated code tends to optimize for surface completion, not operational quality, unless the spec includes those constraints. Not "fast," but "p95 latency under 200 ms at 500 requests per second." Not "secure," but "authorization enforced server-side on every mutable operation."

Observability requirements help bridge the gap between code generation and evaluation. A system cannot be evaluated well if it cannot be observed. If a queue processor has an invariant that messages are never silently dropped, the spec should also define the observability needed to detect drops, retries, and latency.

---

## Separating Semantics from Implementation Freedom

*Applies to: spec and blueprint boundary*

Semantic requirements are non-negotiable truths: the output must preserve ordering; retries must be idempotent; every input record must either produce a result or a traceable error. Implementation freedom is the space in which the AI may choose a method: hash map or tree map, synchronous or asynchronous, class hierarchy or composition — as long as the semantics hold.

This separation is powerful. If you overconstrain, the AI becomes brittle. If you underconstrain, it hallucinates architecture. The art is to specify semantics tightly and mechanisms selectively. "The system must support CSV, JSON, and XML parsers behind a uniform interface with format-specific validation" captures the semantic need while leaving the implementation open.

---

## The Nine-Question Spec Checklist

SVP itself was built by SVP. The lessons learned document catalogs 95+ bugs across five build generations. Nearly every one traces back to something the stakeholder spec didn't say clearly enough. These nine questions are distilled from that experience. They are also baked into the reviewer agent definitions as mandatory checklists, so even if you miss something, the pipeline's own reviewers will flag it.

**1. Have I listed every valid value?** Whenever your spec says a field is "configurable" or accepts "one of several options," stop and list them all.

**2. Have I said what happens when things go wrong?** For every operation, ask: what if the input is missing, malformed, or empty? The answer must be specific.

**3. Have I stated every side effect?** If an operation writes a file, creates a directory, sets permissions, or modifies anything outside its return value — say so.

**4. Have I specified every value the system uses?** Every constant, threshold, default, and mapping must have an explicit source. "The agent will figure it out" is not a source.

**5. Have I described the behavior, not the mechanism?** The spec says what the output must look like. The blueprint decides how to get there internally.

**6. Have I applied every rule universally?** When you discover a rule that prevents a bug, apply it everywhere — not just where the bug appeared.

**7. Have I made every requirement testable?** Before you write a requirement, ask: "How would I verify this is working?" If you cannot answer, rewrite the requirement until you can.

**8. Have I distinguished what must always be true from what happens once?** A contract is local to one function. An invariant applies everywhere, always. Promote recurring rules from contracts to invariants.

**9. Have I verified structural completeness?** Trace every function from definition to call site. Every exported function must have a call site, a behavioral contract sufficient for reimplementation, and if it is a gate dispatch handler, a per-option contract specifying the exact state transition.

---

## Intent Engineering: The Skill That Matters

You do not need to learn to code. What matters is learning to tell the LLM what you actually need — precisely enough that the gap between what you said and what you meant is as small as possible. That gap is where bugs live. Closing it is the skill.

When you start your first SVP project, you will not be good at this. That is expected. The Socratic dialog in Stage 1 exists precisely to compensate: the agent asks you questions, surfaces contradictions, pushes you to think about edge cases, and structures your answers into a formal specification. You bring the domain knowledge; the agent brings the engineering discipline. Together you produce a spec that is better than either of you would write alone.

But here is what changes with experience: the dialog gets shorter. Not linearly — exponentially. Your first project might take an hour of back-and-forth as the agent extracts requirements you didn't know you had. Your fifth project, you walk in with half the spec already clear in your head. Your tenth project, you write a draft spec before starting SVP and the dialog becomes a focused review.

This happens because you are learning to think like someone who specifies software. You learn that "compute the budget" is not a spec — it is a wish. A spec says which models to look up, what their context windows are, what to subtract, and what to return when no model matches. You learn that every value the system uses must come from somewhere explicit — a constant in the spec, a configuration file, a user input — and that "the agent will figure it out" is not a source.

The return on this skill is enormous. A domain expert who has learned intent engineering can produce a stakeholder spec that flows through the pipeline with minimal friction: fewer review rounds, fewer redo cycles, fewer post-delivery bugs. The spec is the highest-leverage artifact in the entire system. Every hour spent making it precise saves many hours downstream.
