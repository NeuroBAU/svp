# SVP — Stratified Verification Pipeline

A Claude Code plugin that turns natural language
requirements into verified Python projects. SVP builds
Python and delivers Python — it is not designed for other
languages. You describe what you want; SVP orchestrates
LLM agents to build, test, and deliver it — with
deterministic state management, multi-agent
cross-checking, and human decision gates at every
critical point.

**Paper:** [TODO: link to ArXiv paper] — the theoretical
foundations, design rationale, and empirical results
behind SVP.

## What SVP Does

SVP is a six-stage pipeline where a domain expert authors software requirements in conversation, and LLM agents generate, verify, and deliver a working Python project. You never write code. The pipeline compensates for your inability to evaluate generated code through forced separation of concerns: one agent writes tests, a different agent writes implementation, a third reviews coverage, and deterministic scripts control every state transition.

The pipeline stages:

1. **Setup** — Describe your project context and delivery preferences, optionally connect GitHub references.
2. **Stakeholder Spec** — A Socratic dialog extracts your requirements, surfacing contradictions and edge cases.
3. **Blueprint** — An agent decomposes the spec into testable units with a dependency DAG. An independent checker verifies alignment.
4. **Unit Verification** — Each unit goes through test generation → red run → implementation → green run → coverage review. Human gates at every decision point.
5. **Integration Testing** — Cross-unit tests verify the seams. Bounded fix cycles handle assembly issues.
6. **Repository Delivery** — A clean git repo with meaningful commit history, profile-driven README, and all artifacts.
7. **Post-Delivery Debugging** *(optional)* — Investigate and fix bugs in the delivered software via `/svp:bug`. See "When Things Go Wrong" below.

## Who It's For

Domain experts who know exactly what their software should do but cannot write it themselves. The motivating example is an academic scientist — a neuroscientist who understands spike sorting, a climate scientist who understands atmospheric models — but SVP is domain-agnostic. If you can judge whether a test assertion makes domain sense when explained in plain language, SVP can build your project.

You need:

- Deep knowledge of your professional field
- Conceptual understanding of programming (you know what functions and loops are)
- Ability to follow terminal instructions precisely
- A Claude Code subscription with API access

You do not need:

- Ability to write code in any language
- Ability to evaluate whether an implementation is correct
- Experience with testing frameworks, git, or environment management

## Installation

### Prerequisites

- [Claude Code](https://docs.claude.com) installed and functional
- A valid Anthropic API key configured
- [Conda](https://docs.conda.io/en/latest/miniconda.html) (Miniconda or Anaconda) installed and on your PATH
- [Git](https://git-scm.com/) installed and configured
- Python 3.10+

### Install the Plugin

Clone the repository, then register it as a Claude Code marketplace and install the plugin.

#### macOS / Linux / Windows (WSL2)

```bash
git clone https://github.com/NeuroBAU/svp.git
cd svp
claude plugin marketplace add "$(pwd)"
claude plugin install svp@svp
```

### Install the Launcher

```bash
pip install -e .
```

This builds the `svp` CLI entry point. The `svp` command is simply a wrapper that invokes `svp/scripts/svp_launcher.py` — the launcher source lives inside the plugin directory and the `pip install` step creates a CLI entry point for it via `pyproject.toml`. The script is placed in pip's script directory, which may not be on your PATH. If `svp --help` does not work after installation, you need to locate the script and make it accessible.

#### macOS / Linux

Find where pip placed the script, then copy or symlink it to a directory on your PATH:

```bash
# Find the script location
find "$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))')" -name svp 2>/dev/null

# If found, copy it to ~/.local/bin/ (create the directory if needed)
mkdir -p ~/.local/bin
cp "$(python -c 'import sysconfig; print(sysconfig.get_path("scripts"))')/svp" ~/.local/bin/svp
chmod +x ~/.local/bin/svp

# Ensure ~/.local/bin is on your PATH (add to ~/.bashrc or ~/.zshrc if not already)
export PATH="$HOME/.local/bin:$PATH"
```

#### Windows (WSL2)

Inside WSL2, the same Linux instructions apply. For native Windows with Anaconda, scripts are typically installed to the Anaconda `Scripts` directory (e.g., `C:\Users\<you>\anaconda3\Scripts\svp.exe`), which is usually on PATH after Anaconda installation.

Verify the installation:

```bash
svp --help
```

### Start a New Project

```bash
svp new my-project
```

The launcher verifies all prerequisites, creates the
project directory structure, writes the initial
configuration, and launches Claude Code with SVP active.

## Workspace and Delivered Repository

SVP maintains two separate directories for your project:

The **workspace** is where the pipeline builds your
software. When you run `svp new my-project`, the launcher
creates `my-project/` containing the pipeline scripts,
configuration files, source directories (`src/unit_N/`),
test directories (`tests/unit_N/`), and all pipeline
state. This is the build environment — you work here
during Stages 0 through 4.

The **delivered repository** is the clean output. At
Stage 5, the git repo agent assembles a separate git
repository at `my-project-repo/` (a sibling directory,
not inside the workspace). It relocates your code from
the workspace's `src/unit_N/stub.py` structure into
proper module paths, rewrites imports, generates
`pyproject.toml`, creates a meaningful commit history,
and delivers a repository that looks like a normal Python
project — no SVP infrastructure, no stubs, no pipeline
state.

The two directories serve different purposes: the
workspace is disposable build scaffolding; the delivered
repo is what you ship, share, or publish.

If you use `/svp:redo` to roll back to the stakeholder
spec or blueprint (before Stage 3), the pipeline rebuilds
from scratch. When Stage 5 runs again, it does not
overwrite the existing delivered repo — it renames the
old one with a timestamp (e.g., `my-project-repo` becomes
`my-project-repo_20260315_143022`) and creates a fresh
`my-project-repo`. Each restart produces a new delivered
directory. After N restarts, you will have N+1 directories:
the current `my-project-repo` plus N timestamped backups.
You can delete the backups once you are satisfied with the
current delivery.

When you use `/svp:bug` after delivery, the triage agent
investigates in the delivered repository (using the
`delivered_repo_path` recorded in pipeline state) and
applies fixes to the workspace source first. The pipeline
then triggers a Stage 5 reassembly to propagate the fix
into the delivered repository. This ensures the workspace
remains the canonical source and the delivered repo stays
in sync.

Once you are satisfied with the delivered project, use
`/svp:clean` to dispose of the workspace. It offers three
modes: **archive** compresses the workspace into a
timestamped zip file and deletes the directory;
**delete** removes the workspace immediately without
backup; **keep** removes the Conda environment but leaves
the workspace files in place. All three modes remove the
Conda environment created during the build. The delivered
repository is never touched by `/svp:clean` — it is yours
to keep regardless of what you do with the workspace.
`/svp:clean` is only available after Stage 5 completes.

## Configuration

SVP is configured through `svp_config.json` in your project root. Changes take effect on the next agent invocation — no restart required.

### Default Configuration

```json
{
    "iteration_limit": 3,
    "models": {
        "test_agent": "claude-opus-4-6",
        "implementation_agent": "claude-opus-4-6",
        "help_agent": "claude-sonnet-4-6",
        "default": "claude-opus-4-6"
    },
    "context_budget_override": null,
    "context_budget_threshold": 65,
    "compaction_character_threshold": 200,
    "auto_save": true,
    "skip_permissions": true
}
```

## Commands

All SVP commands use the `/svp:` namespace.

| Command | Description |
|---------|-------------|
| `/svp:save` | Flush state to disk and confirm. |
| `/svp:quit` | Save and exit the pipeline. |
| `/svp:status` | Show current pipeline state including toolchain, profile summary, and active quality gate status. |
| `/svp:help` | Pause the pipeline and launch the help agent. |
| `/svp:hint` | Request a diagnostic analysis. |
| `/svp:ref` | Add a reference document (Stages 0–2 only). |
| `/svp:redo` | Roll back a previous decision. Supports profile revisions. |
| `/svp:bug` | Enter the post-delivery debug loop (after Stage 5). |
| `/svp:clean` | Archive, delete, or keep the workspace after delivery. |

## When Things Go Wrong: The Two Fix Ladders

Every project has bugs. In practice, bugs almost always
trace back to something the stakeholder spec didn't say
clearly enough. The agents are probabilistic, but when
they produce wrong code it is nearly always because the
spec left room for the wrong interpretation — a vague
contract, a missing constraint, an unstated assumption.
The code is wrong because the spec allowed it to be wrong.

SVP provides two strategies for fixing bugs. Both start
the same way — you find something wrong in the delivered
software — but they climb different ladders. The
difference is not where the bug comes from (it comes from
the spec), but whether the cost of fixing the spec is
worth it for your project.

### Ladder 1: Fix the Unit

The pragmatic choice for small projects and disposable
code. You know the bug comes from the spec, but fixing
the spec, regenerating the blueprint, and rebuilding from
scratch would cost more in time and tokens than the
project is worth. So you fix the symptom and move on.

**When to use:** Small projects, exploratory code, or any
situation where the cost of a full rebuild outweighs the
benefit. The LLM can compensate for spec vagueness in
common domains — data analysis, simulations, utilities —
so unit-level fixes stick well enough.

**How it works:**

1. Run `/svp:bug` and describe what you observed.
2. The triage agent investigates the delivered repo,
   identifies the affected unit, and classifies the bug.
3. A regression test is written to reproduce the failure.
4. The repair agent fixes the unit implementation.
5. All tests pass (including the new regression test).
6. The fix is committed to the delivered repo.

This is fast and self-contained. The spec and blueprint
are not touched. You are fixing the instance of the bug,
not the class. For most projects, this is the right
trade-off.

### Ladder 2: Fix the Source

The thorough choice for complex projects where spec-level
gaps produce cascading bugs across multiple units. You fix
the root cause — the spec itself — and rebuild.

**When to use:** Complex projects with cross-unit
contracts, state machines, or architectural invariants.
Also any project where you fix a unit bug and the same
*kind* of bug keeps appearing elsewhere — that pattern
means the spec has a systemic gap that unit-level repair
cannot close.

**How it works:**

1. Run `/svp:bug` and describe what you observed.
2. The triage agent investigates. Pay attention to its
   root cause analysis and ask yourself: *Why did the
   spec allow this bug to exist? What should it have
   said?*
3. Use the triage agent's findings to trace the bug
   backward: from the failing code, to the blueprint
   contract that produced it, to the spec section that
   should have prevented it.
4. Run `/svp:redo` to roll back to the stakeholder spec.
5. Revise the spec to close the gap — add the missing
   detail, the missing constraint, the missing invariant.
6. The pipeline rebuilds from the corrected spec: new
   blueprint, new tests, new implementation.

This is expensive in time and tokens. You are throwing
away completed work and rebuilding from scratch. But for
the class of project that needs it, there is no
alternative — you cannot test your way out of a spec gap.

## Writing a Good Spec: Intent Engineering

You do not need to learn to code. In a world with AI,
learning to code is not the skill that matters. What
matters is learning to tell the LLM what you actually
need — precisely enough that the gap between what you said
and what you meant is as small as possible. That gap is
where bugs live. Closing it is the skill. We call it
intent engineering.

When you start your first SVP project, you will not be
good at this. That is expected. The Socratic dialog in
Stage 1 exists precisely to compensate: the agent asks
you questions, surfaces contradictions, pushes you to
think about edge cases you hadn't considered, and
structures your answers into a formal specification. You
bring the domain knowledge; the agent brings the
engineering discipline. Together you produce a spec that
is better than either of you would write alone.

But here is what changes with experience: the dialog gets
shorter. Not linearly — exponentially. Your first project
might take an hour of back-and-forth in Stage 1 as the
agent extracts requirements you didn't know you had. Your
fifth project, you walk in with half the spec already
clear in your head because you have learned what the
pipeline needs to hear. Your tenth project, you write a
draft spec before starting SVP and the dialog becomes a
focused review rather than an extraction.

This happens because you are not learning to code. You
are learning to think like someone who specifies software.
You learn that "compute the budget" is not a spec — it is
a wish. A spec says which models to look up, what their
context windows are, what to subtract, and what to return
when no model matches. You learn that every value the
system uses must come from somewhere explicit — a constant
in the spec, a configuration file, a user input — and
that "the agent will figure it out" is not a source.

The return on this skill is enormous. A domain expert who
has learned intent engineering can produce a stakeholder
spec that flows through the pipeline with minimal
friction: fewer review rounds, fewer redo cycles, fewer
post-delivery bugs. The spec is the highest-leverage
artifact in the entire system. Every hour spent making it
precise saves many hours downstream.

This is what makes you a developer for your domain. Not
the ability to write Python, but the ability to close the
gap between what you know and what the machine needs to
hear.

### The Two Documents: Spec and Blueprint

SVP produces two key documents during the first three
stages. Understanding what they are — and the
relationship between them — is essential for intent
engineering.

The **stakeholder spec** is yours. You write it, with the
help of the Socratic dialog agent. It describes *what*
your software should do, in your language, using your
domain concepts. It says nothing about functions, classes,
or modules. It talks about behavior: "the system accepts
a configuration file and fills in missing fields from
sensible defaults." The spec is the single source of
truth for the entire pipeline. Everything downstream —
every test, every line of code — traces back to a
sentence in the spec.

The **blueprint** is the LLM's translation of your spec
into software architecture. An agent reads your spec and
decomposes it into units with signatures, contracts, and
dependencies. You approve the blueprint, but you do not
write it. The blueprint is written in plain English with
embedded code signatures — not source code, but the
*shape* of the code: what each unit accepts, what it
returns, what it promises to do.

Two things follow from the blueprint being in plain
English rather than opaque code:

First, it is documentation. The blueprint describes what
every piece of your software does and why, in language
you can read. When your delivered project produces a
result you do not understand — an unexpected value, a
graph that looks wrong — you can feed the blueprint to
an LLM and ask: "Why does unit 7 produce this output
given this input?" The LLM can trace the answer through
the contracts and explain it in your domain terms. This
eliminates the transparency problem that plagues
AI-generated code: you may not be able to read Python,
but you can read the blueprint, and the blueprint is the
authoritative description of what the Python does.

Second, it teaches you. As your software design skills
grow through experience with SVP, your ability to read
the blueprint compounds on itself. You start noticing
patterns: "this contract is vague — it says 'processes
the data' but doesn't say what happens when the data is
empty." You start recognizing the gap between what your
spec said and what the blueprint had to infer. Over
time, reading blueprints from your previous projects
teaches you to write better specs for your next project.
The blueprint becomes a mirror that shows you exactly
where your intent was clear and where it was not.

### Concepts That Matter

You do not need a computer science degree. You need a
working vocabulary of about ten ideas. These are the 20%
of software design that deliver 80% of the value when
writing a spec. Everything else — design patterns, class
hierarchies, memory management — is the LLM's problem.
What follows is a distillation of the ideas presented in
the SVP paper (TODO: ArXiv link).

**Unit.** A self-contained piece of the system that does
one thing. It might be a single function, a group of
related functions, or a module — the internal structure
does not matter at spec level. What matters is that you
can describe what it does, what it needs, and what it
produces without referring to the internals of other
units. When you write a spec, you are implicitly defining
units: "the system loads configuration" is one unit, "the
system validates user input" is another. If you can
describe a responsibility in one sentence, it is probably
one unit. SVP enforces a strict rule: each unit may only
depend on previously produced units. Unit 5 can use Units
1 through 4, but never Unit 6 or beyond. This means
units are built and verified one at a time, in order —
a linear pipeline, not a parallel one. This is
deliberately less efficient than building multiple units
simultaneously. The trade-off is correctness: when each
unit is tested against already-verified dependencies,
errors cannot hide in circular references or race
conditions between units being built at the same time.
The linear approach is slower but produces far fewer bugs
at the seams.

**Signature.** What a unit accepts and what it returns.
Not how it works — just the shape of the conversation
between the unit and the rest of the system. "This unit
takes a project directory and returns a configuration
dictionary" is a signature. Signatures matter because
they are the connection points between units. If two
units disagree about a signature — one passes a file
path, the other expects a directory path — the system
breaks at the seam, not inside either unit. Many bugs in
complex systems are signature mismatches, not logic
errors. When you write a spec, be precise about what
goes in and what comes out.

**Contract.** What a unit promises to do — not just its
signature, but its behavior. "Takes a configuration file
and returns a dictionary" is a signature. "Missing keys
are filled from defaults via recursive merge; unknown
keys are preserved for forward compatibility; a missing
file returns the default configuration without error" is
a contract. Contracts are where spec precision pays off
most. A vague contract ("loads the config") gives the LLM
room to make choices you didn't intend. A precise contract
("missing file returns defaults, malformed file raises
RuntimeError with the file path in the message") leaves
no room for the wrong choice.

**Invariant.** Something that must always be true, no
matter what. Not a behavior of one function, but a rule
that applies across the entire system. "No function that
modifies pipeline state may mutate its input — it must
return a new copy" is an invariant. "Every gate ID that
appears in the routing table must also appear in the
preparation script's registry" is an invariant.
Invariants are your most powerful tool because they
prevent entire classes of bugs, not individual instances.
A single invariant like "every CLI function must have its
arguments enumerated in the blueprint" prevents a bug
from appearing in any of the 24 units, forever. When you
find yourself fixing the same kind of bug in multiple
places, you are missing an invariant.

**Dependency.** When one unit needs another unit to work.
"The routing script reads pipeline state" means the
routing script depends on the state module. Dependencies
must flow in one direction — if A depends on B and B
depends on A, you have a cycle, and cycles make systems
fragile and hard to test. In your spec, stating
dependencies explicitly ("this component needs
configuration data from that component") helps the
blueprint author arrange units in the right order and
helps the test agent isolate units for testing.

**State.** Data that changes over time. A configuration
file that is read once is not state — it is input. A
pipeline position that advances from stage to stage is
state. State is where most complexity lives, because
every piece of code that reads state must handle every
possible value that state could have at that point. When
you write a spec, identify what changes over time and
describe all the values it can take. "The pipeline
tracks the current stage" is insufficient. "The stage is
one of: 0, 1, 2, pre_stage_3, 3, 4, 5" is sufficient.

**Side effect.** When a unit changes something outside
itself — writes a file, creates a directory, sends a
message, modifies a database. Side effects matter because
they are invisible to the caller unless documented. "This
function validates the input" has no side effects — it
takes data and returns a result. "This function validates
the input and writes a log entry" has a side effect. In
your spec, every side effect must be stated explicitly.
If a function creates a backup directory before deleting
files, that is a side effect. If it sets file permissions,
that is a side effect. Unstated side effects become bugs
that are impossible to diagnose from the contract alone.

**Error condition.** What happens when things go wrong.
Every unit will encounter situations it cannot handle: a
missing file, an invalid value, a network timeout. The
spec must say what happens in each case — not just "it
handles errors gracefully" but "a missing file raises
FileNotFoundError with the path in the message; a
malformed file raises RuntimeError." Without explicit
error conditions, the LLM will make reasonable but
potentially wrong choices about how to fail, and the
tests will not know what to check for.

**Enumeration.** Listing all valid values explicitly
rather than describing them in prose. "The linter can be
ruff, flake8, pylint, or none" is an enumeration. "The
linter is configurable" is not — it leaves the valid
values unspecified, and the implementation agent will
have to guess. Enumerations are the single most common
source of spec gaps. Every time your spec says "one of
several options" or "a valid value," ask yourself: can I
list them all? If you can, list them. The implementation
cannot guess what you consider valid.

**Testability.** Can you verify the behavior from the
outside, without looking at the code? A contract is
testable if you can write a sentence of the form "given
this input, the output must be that." A contract is not
testable if it says "handles the data appropriately" —
appropriate according to whom? Every contract you write
in the spec will become a test. If you cannot imagine
what the test would check, the contract is too vague.
The discipline is: before you write a requirement, ask
"how would I verify this is working?" If you cannot
answer that question, rewrite the requirement until you
can.

### The Spec Prompt: A Checklist for Prevention

SVP itself was built by SVP. The lessons learned document
(`docs/references/svp_2_1_lessons_learned.md` in the
delivered repository) catalogs 73 bugs discovered across
five build generations — from SVP 1.0 through SVP 2.1.
Nearly every one traces back to something the stakeholder
spec didn't say clearly enough. The checklist below is
distilled from that experience. It is not project-specific;
it applies to any spec you write.

These questions are also baked into the reviewer agent definitions as mandatory checklists (Bug 57), so even if you miss something, the pipeline's own reviewers will flag it.

Carry these questions in your head during the Socratic
dialog. The agent will ask you about your domain. These
questions help you answer with the precision the pipeline
needs. Each question below explains why it matters, gives
a concrete example from SVP's own build history, and ends
with a prompt fragment — exact language you can pass to
the agent during the dialog or paste into your spec draft.

**1. Have I listed every valid value?**

Whenever your spec says a field is "configurable" or
accepts "one of several options," stop and list them all.
"The linter is configurable" becomes "the linter is one
of: ruff, flake8, pylint, none." If you cannot list the
values, you do not yet understand the requirement well
enough. This single habit prevents more bugs than any
other. In SVP's own build, Bug 50 found that six
validation sets — linters, formatters, type checkers,
import sorters, commit styles, changelog formats — were
described in prose but never enumerated. The
implementation agents guessed, and guessed differently
from each other.

> **Prompt:** "The valid values for [field] are:
> [value1], [value2], [value3]. Any other value is
> invalid and must be rejected with an error message
> that includes the invalid value and the list of valid
> options."

**2. Have I said what happens when things go wrong?**

For every operation in your spec, ask: what if the input
is missing? What if it is malformed? What if it is empty?
The answer must be specific: "raises RuntimeError with
the file path in the message" — not "handles errors
gracefully." An LLM interpreting "handles errors
gracefully" might return a default, raise an exception,
print a warning, or silently continue. Each is graceful.
Only one is what you meant.

> **Prompt:** "When [input] is missing, the system
> raises [ErrorType] with a message that includes
> [specific detail]. When [input] is malformed, the
> system raises [ErrorType] with a message that includes
> [specific detail]. The system never silently returns a
> default for invalid input."

**3. Have I stated every side effect?**

If an operation writes a file, creates a directory,
deletes something, sets permissions, or modifies anything
outside its own return value — say so. "Validates the
input" has no side effects. "Validates the input and
writes a log entry" does. In SVP's build, Bug 50 found
that `rollback_to_unit` had undocumented side effects
(copying files to a backup directory before deletion) —
a critical behavior that the spec never mentioned. Bug 55
later corrected this: rollback now deletes files outright
(agents regenerate from scratch), and the spec was updated
to document the full rollback-and-rebuild semantics. If
the spec had originally documented the exact side effects,
the blueprint would have contracted them, the tests would
have verified them, and no audit would have been needed.

> **Prompt:** "Before [destructive operation], the
> system preserves [what] in [where]. After [operation],
> [what files/directories] exist at [what paths]. The
> operation also [sets permissions / creates directories
> / writes markers] as a side effect."

**4. Have I specified every value the system uses?**

If the system needs a number, a mapping, a threshold, or
a default — where does it come from? "Computes the
context budget" is a wish. "Looks up each model in a
mapping of model names to context window sizes, finds the
smallest, subtracts 20,000 tokens overhead, returns the
result; if no model is found, uses 200,000 as the
fallback" is a spec. Every value must have an explicit
source: a constant you define, a configuration file, a
user input, or a computation you describe. "The agent
will figure it out" is not a source. This is the core
lesson of Bug 50: 16 functions across 6 units had
correct implementations, but their contracts didn't
specify the values they used — model context windows,
overhead constants, fallback defaults, placeholder sets.
A fresh rebuild from those contracts would have produced
different (wrong) values.

> **Prompt:** "The system uses the following constants:
> [name] = [value] ([why this value]). When computing
> [result], the inputs are [source1] and [source2], the
> formula is [explicit computation], and the fallback
> when [condition] is [fallback value]."

**5. Have I described the behavior, not the mechanism?**

Your spec should say what the system does, not how it
does it internally. "Missing keys are filled from
defaults via recursive merge" is behavior — it tells the
implementation what the output must look like. "Use a
helper function called `_deep_merge` that recurses into
nested dicts" is mechanism — it dictates an internal
design choice that the implementation agent should make
on its own. The boundary: if changing the internal
approach would cause a test to fail, it is behavior and
belongs in the spec. If changing it would produce the
same outputs, it is mechanism and does not.

> **Prompt:** "When loading [data], missing fields are
> filled from the default values. Nested structures are
> merged recursively — a missing sub-field gets the
> default without overwriting sibling fields that are
> present. The implementation may use any approach to
> achieve this behavior."

**6. Have I applied every rule universally?**

When you discover a rule that prevents a bug, apply it
everywhere — not just where the bug appeared. "Every CLI
function must have its arguments enumerated" is a rule.
If you apply it only to the function where you found the
bug, the same bug will appear in every other CLI function
you didn't check. In SVP's build, this pattern appeared
three times: Bug 43 (two-branch routing applied to one
stage, not all), Bug 48 (CLI argument enumeration applied
to one unit, not all), and Bug 49 (the systemic audit
that found five more units with the same gap). Each time,
the fix for one instance should have been applied
universally from the start.

> **Prompt:** "This rule applies to every [unit /
> function / component] in the system that [condition],
> not just the one where the issue was discovered. A
> structural test must verify compliance across all
> instances. The affected [units/functions] as of this
> version are: [exhaustive list]."

**7. Have I made every requirement testable?**

Before you write a requirement, ask: "How would I verify
this is working?" If the answer is "I would check that
the output contains X when given input Y," the
requirement is testable. If the answer is "I would look
at the code and see if it seems right," the requirement
is not testable — rewrite it until it is. Every sentence
in your spec will become a test. If you cannot imagine
the test, the sentence is too vague.

> **Prompt:** "Given [specific input], the system
> produces [specific output]. Given [edge case input],
> the system [specific behavior]. This can be verified
> by [what a test would check]."

**8. Have I distinguished what must always be true from
what happens once?**

A contract says what a specific function does. An
invariant says what must be true everywhere, always.
"This function returns a new state without modifying the
input" is a contract. "No function in the system may
modify its input state" is an invariant. Invariants are
more powerful because they prevent bugs in units that
do not exist yet. When you find a rule that applies to
more than one unit, promote it from a contract to an
invariant.

> **Prompt:** "Invariant: [rule]. This applies to every
> [unit / function / component] in the system without
> exception. A structural test must verify that all
> current and future instances comply. Violation of this
> invariant is a build failure, not a warning."

**9. Have I verified structural completeness?**

When writing or reviewing a spec, explicitly trace every
function from its definition to its call site. Ask: (1)
Are there any functions that are specified but will never
be called? Every exported function must have a call site.
(2) If a unit's implementation changes during debug or fix
ladder, will downstream units still be valid? Apply the
Downstream Dependency Invariant -- if unit N changes, all
units >= N must be invalidated and rebuilt. (3) Does every
exported function have a Tier 3 behavioral contract
sufficient for deterministic reimplementation? (4) Does
every gate response option have a dispatch contract
specifying the exact state transition? In SVP's build,
Bugs 52-55 all involved functions that were implemented
but never wired into the dispatch path. Per-gate-option
dispatch contracts and call-site verification would have
caught every one during blueprint alignment.

> **Prompt:** "Every exported function in this spec must
> have: (a) a call site that invokes it, (b) a behavioral
> contract sufficient for reimplementation, and (c) if it
> is a gate dispatch handler, a per-option contract
> specifying the exact state transition. Every re-entry
> path must document what happens to downstream units."

These nine questions are not exhaustive, but they cover
the patterns that produced 74 bugs across five build
generations of SVP. The lessons learned document in the
delivered repository contains the full catalog with root
causes, patterns, and prevention rules. Bug 50 in
particular demonstrates why this checklist matters: an
audit of the delivered system found 16 functions where
the contracts were technically correct but too vague to
reproduce — the implementations worked by luck, not by
specification. The prompts above, used consistently
during the Socratic dialog, would have prevented every
one of them. Question 9 in particular addresses the
structural gaps that produced the most persistent bug
cluster in SVP's build history (Bugs 52-55).

## Example Project

SVP includes a complete Game of Life example in `examples/game-of-life/` with a stakeholder spec, blueprint, and project context.

```bash
svp restore game-of-life \
  --spec examples/game-of-life/stakeholder_spec.md \
  --blueprint-dir examples/game-of-life/ \
  --context examples/game-of-life/project_context.md \
  --scripts-source svp/scripts/ \
  --profile examples/game-of-life/project_profile.json
```

## Project Structure

```
svp-repo/
├── .claude-plugin/marketplace.json   <- Marketplace catalog
├── svp/                              <- Plugin subdirectory
│   ├── .claude-plugin/plugin.json   <- Plugin manifest
│   ├── agents/                      <- Agent definition files
│   ├── commands/                    <- Slash command files
│   ├── hooks/                       <- Write authorization hooks
│   ├── scripts/                     <- Deterministic pipeline scripts
│   │   ├── toolchain_defaults/      <- Default toolchain configuration
│   │   └── templates/               <- Project template files
│   └── skills/orchestration/        <- Orchestration skill
├── tests/                           <- Test suite
│   └── regressions/                 <- Carry-forward regression tests
├── examples/
│   └── game-of-life/                <- Bundled example
└── docs/                            <- Documentation
    ├── stakeholder_spec.md
    ├── blueprint_prose.md
    ├── blueprint_contracts.md
    ├── project_context.md
    ├── history/
    └── references/
```

### Document Version Tracking

Every time a document is revised through a gate decision (REVISE, FIX BLUEPRINT, or FIX SPEC), the routing script's `dispatch_gate_response` function calls `version_document()` to snapshot the current version before the revision occurs. The previous version is copied to `docs/history/` with an incrementing version number (e.g., `stakeholder_spec_v1.md`, `blueprint_prose_v2.md`), and a diff summary is saved alongside it recording the timestamp, trigger context, and what changed. The current working version remains at its canonical path (`specs/stakeholder_spec.md`, `blueprints/blueprint_prose.md`, `blueprints/blueprint_contracts.md`). Blueprint files are always versioned as an atomic pair — both prose and contracts are snapshotted together. This history is included in the delivered repository at `docs/history/`.

## Test Scenarios

The SVP test suite covers:

- **Unit tests** (`tests/unit_N/`): One test module per pipeline unit, covering the unit's behavioral contracts.
- **Regression tests** (`tests/regressions/`): Carry-forward tests for all 74 catalogued bugs. Each file targets a specific bug scenario.
- **Integration tests** (`tests/integration/`): Cross-unit tests covering toolchain resolution, profile flow, blueprint checker preference validation, quality gate execution, and write authorization.

Run the full test suite from the repository root:

```bash
conda run -n svp2_1 pytest tests/ -v
```

## SVP 2.0 Features

SVP 2.0 adds two capabilities to the complete SVP 1.2 baseline:

**Project Profile (`project_profile.json`)**
The setup agent conducts a Socratic dialog to capture your delivery preferences: README structure, commit message style, documentation depth, license, dependency format, and more. These preferences are recorded in `project_profile.json` and used to drive Stage 5 delivery. You can accept sensible defaults with a single response or dive into detailed configuration.

**Pipeline Toolchain Abstraction (`toolchain.json`)**
SVP's own build commands (conda, pytest, setuptools, git) are now read from a configuration file rather than hardcoded. This is a code quality improvement — it does not change how SVP builds your project. The file is copied from the plugin at project creation and is permanently read-only.

## SVP 2.1 Features

SVP 2.1 is the terminal release of the SVP product line, adding pipeline-integrated quality gates and delivered quality configuration.

**Pipeline Quality Gates (A, B, C)**
Every project built by SVP 2.1 is automatically formatted, linted, and type-checked during the build. Quality is a pipeline guarantee, not an opt-out feature.

| Gate | Position | Operations |
|------|----------|------------|
| Gate A | Post-test generation, pre-red-run | `ruff format` + light lint (E, F, I rules). No type check on tests. |
| Gate B | Post-implementation, pre-green-run | `ruff format` + heavy lint + `mypy --ignore-missing-imports` |
| Gate C | Stage 5 assembly | `ruff format --check` + full lint + full `mypy` (cross-unit) + unused function detection (human-gated) |

- Gate composition is data-driven from `toolchain.json` (`gate_a`, `gate_b`, `gate_c` lists).
- All gates are mandatory. No opt-out.
- Auto-fix runs first; residuals trigger one agent re-pass; then fix ladder.
- Quality gate retry budget is separate from fix ladder retry budget.

**Delivered Quality Configuration**
The `project_profile.json` `quality` section captures your preferences for the delivered project's quality tools (linter, formatter, type checker, import sorter, line length). The git repo agent generates the corresponding configuration in `pyproject.toml`.

**Changelog Support**
Set `vcs.changelog` in your profile to `"keep_a_changelog"` or `"conventional_changelog"` to generate a `CHANGELOG.md` in the delivered repository.

**Test Scenarios in README**
When `testing.readme_test_scenarios` is set in the profile, the README includes a section describing the test suite's coverage approach.

## SVP 2.1.1 Features

SVP 2.1.1 adds unit-level preference capture to the blueprint dialog, enabling domain experts to express non-requirement preferences (output format conventions, naming styles, display choices) during blueprint construction rather than after delivery.

**Unit-Level Preference Capture (RFC-2)**
During Stage 2 blueprint construction, the blueprint author agent follows four rules (P1-P4) to capture domain preferences at the unit level:

- **Rule P1 (Ask at the unit level):** After establishing each unit's Tier 1 description and before finalizing its contracts, ask about domain conventions, output appearance preferences, and domain-specific choices that are not requirements but matter.
- **Rule P2 (Domain language only):** Use the human's domain vocabulary, not engineering vocabulary. The agent asks "What file format do your collaborators' tools expect?" rather than "Do you have preferences for the serialization format?"
- **Rule P3 (Progressive disclosure):** One open question per unit. Follow-up only if the human indicates preferences. No menu of categories for every unit.
- **Rule P4 (Conflict detection at capture time):** If a preference contradicts a behavioral contract being developed, identify immediately and resolve during dialog.

Captured preferences are recorded as a `### Preferences` subsection within each unit's Tier 1 description in `blueprint_prose.md`. Absence of the subsection means "no preferences" -- no explicit marker is needed. The authority hierarchy is: spec > contracts > preferences. Preferences are non-binding guidance that operates within the space contracts leave open.

**Preference-Contract Consistency Validation**
The blueprint checker validates that no stated preference contradicts a Tier 2 signature or Tier 3 behavioral contract. Inconsistencies are reported as non-blocking warnings (not alignment failures), since preferences are advisory by design.

**Structural Completeness Checking**
SVP 2.1.1 introduces a four-layer structural completeness defense: a project-agnostic AST scanner, 14 automated declaration-vs-usage techniques, 163 structural tests, and registry completeness validation. This system catches orphaned functions, missing dispatch paths, and declaration-usage mismatches at build time rather than after delivery.

## History

- **SVP 1.0** — Initial release. The pipeline scripts and plugin infrastructure were hand-written, then used to build subsequent versions of SVP itself.
- **SVP 1.1** — Introduced Gate 6 (post-delivery debug loop), the `/svp:bug` command, triage and repair agent workflows.
- **SVP 1.2** — Bug fixes and hardening. Fixed gate status string vocabulary (Bug 1) and hook permission reset after debug session entry (Bug 2).
- **SVP 1.2.1** — Further bug fixes and robustness improvements.
- **SVP 2.0** — Project Profile (`project_profile.json`) for delivery preferences. Pipeline Toolchain Abstraction (`toolchain.json`). Profile-driven Stage 5 delivery. Delivery compliance scan. `/svp:redo` profile revision support.
- **SVP 2.1** — Pipeline Quality Gates (A, B, C) as mandatory build-time checkpoints. Delivered quality configuration via `project_profile.json`. Blueprint prose/contracts split for token-efficient agent context. Universal two-branch routing invariant applied across all pipeline stages. 51 bug fixes (Bugs 17-58) spanning routing, dispatch, state persistence, dead code removal, and spec structural gaps. See CHANGELOG.md for detailed bug-by-bug history.
- **SVP 2.1.1** — RFC-2: unit-level preference capture in blueprint dialog (Rules P1-P4, preference-contract consistency validation). Structural completeness checking system: four-layer defense with project-agnostic AST scanner, 14 automated declaration-vs-usage techniques, 163 structural tests (Bugs 71-72). 21 additional bug fixes (Bugs 52-72) including full Stage 3 error handling, Stage 4 failure paths, debug loop gates, and selective blueprint loading. RFC-1 (interactive spec) deferred to future release. 74 total bugs cataloged across SVP 1.0 through 2.1.1.

## License

Copyright 2026 Carlo Fusco and Leonardo Restivo

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for the full text.
