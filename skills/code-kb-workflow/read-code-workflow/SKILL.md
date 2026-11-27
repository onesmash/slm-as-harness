---
name: read-code-workflow
description: Read unfamiliar source code methodically instead of wandering through files. Use this skill whenever the user needs to orient themselves in an unfamiliar repo, inherit a project, understand how a service or module works, trace a feature or request path, map architecture, study core data structures, or asks where to start reading code. Trigger even when the user does not explicitly say "read code", for requests like "help me understand this codebase", "I just took over this service", "what files should I read first", "trace how login works", "explain this module", "map the main flow", "how does this project work", or "how do I approach this repo". Do not use for pure implementation, pure debugging, or pure PR review unless understanding the code is the main need first.
---

# Read Code Workflow

> Inspired by codedump's "How to Read Code" workflow and adapted into a reusable skill.

## Overview

Read code with a purpose, an interaction loop, and an output artifact.

Do not try to understand an unfamiliar repository by reading everything linearly from top to bottom. Start with a goal, keep the main storyline in view, and force understanding into notes, diagrams, or concise explanations.

## Quick Reference

- Start with the question you need answered, not with random files.
- Prefer runnable evidence over static guessing.
- Read horizontally before reading vertically.
- Keep a parking lot for side plots so they do not derail the main plot.
- End with a written reading artifact, not just a chatty explanation.

## When to Use

Use this skill when the user is mainly trying to understand code, not change it yet.

Common cases:

- taking over a repo or service,
- onboarding into an unfamiliar codebase,
- asking what files to read first,
- tracing how one feature, request, or job works,
- mapping architecture before editing,
- understanding one module or subsystem,
- clarifying core structs, classes, records, or state objects.

## When Not to Use

Route elsewhere when the main task is:

- implementing a feature,
- fixing a bug with root-cause work as the primary goal,
- reviewing a PR for findings-first quality feedback,
- writing a formal research synthesis unrelated to code understanding.

If understanding is the prerequisite for one of those tasks, use this skill first, then hand off.

## Minimum Execution Contract

When this skill triggers, do not stop at a vague explanation. Always do enough work to provide:

1. A clearly stated reading goal and scope.
2. A note about whether the code was run or only read statically.
3. A small architecture or module map.
4. One main storyline traced end to end.
5. A parking lot of side plots that were intentionally deferred.
6. A map of the most important data structures.
7. Open questions, next verification steps, and confidence.

Use `reading-note-template.md` unless the user explicitly wants a different format.

## Core Principles

1. Run the project first if possible.
2. Define the reading goal before diving into details.
3. Separate the main plot from side plots.
4. Alternate horizontal reading and vertical reading.
5. Use scenarios and tests to shrink the search space.
6. Prioritize core data structures and their relationships.
7. Turn input into output through notes, diagrams, and questions.

## First Move

Before diving in, determine four things:

- The primary reading goal.
- The desired depth.
- Whether the project can be built, run, or debugged.
- The deliverable the user wants.

If the request is vague, default to:

- a high-level architecture pass,
- one important execution path,
- the core data structures,
- and a written reading note.

## Scaling Rules

If the repository is too large, the runtime is unavailable, or the user only wants a fast orientation pass, downscope deliberately instead of pretending to cover everything.

Default reduced scope:

- one entrypoint,
- three to seven key modules,
- one representative execution path,
- three to five core data structures,
- and a short list of open questions.

Label the result as partial when you do this.

## Goal Modes

Choose one primary mode. Park secondary curiosities unless they block the main objective.

If the user does not specify a mode:

- choose `Architecture Mode` for broad "understand this repo" requests,
- choose `Execution Path Mode` for "how does X work?" requests,
- choose `Module Mode` for a named component or folder,
- choose `Data Structure Mode` when the confusion is about state or relationships,
- choose `Algorithm Mode` when the user cares about implementation logic over system shape.

### 1. Architecture Mode

Use when the user wants the shape of the system.

Focus on:

- entrypoints,
- top-level modules,
- runtime boundaries,
- ownership boundaries,
- major data flow.

Start horizontally, then follow one representative path end to end.

### 2. Module Mode

Use when the user wants to understand one component well.

Focus on:

- public API,
- responsibilities,
- invariants,
- dependencies,
- lifecycle,
- extension points.

### 3. Execution Path Mode

Use when the user wants to know how one feature or request flows through the code.

Focus on:

- entrypoint,
- major calls,
- state transitions,
- side effects,
- exit and failure paths.

### 4. Data Structure Mode

Use when understanding the system depends on how data is modeled.

Focus on:

- core structs, classes, or records,
- who creates them,
- who owns them,
- where they mutate,
- who consumes them,
- how they relate.

### 5. Algorithm Mode

Use when the user cares about one implementation technique or algorithm.

Focus on:

- inputs,
- outputs,
- stages,
- invariants,
- complexity,
- edge cases,
- relevant tests.

## Workflow

### Phase 1: Make It Runnable If Possible

If the project can be built and run, do that first.

Why this matters:

- Running code unlocks scenario analysis, tracing, breakpoints, logs, and test execution.
- Static reading alone is often enough for rough structure, but it is weaker for behavioral understanding.

When setting up the environment:

- Prefer a debug-friendly configuration.
- Reduce noise where possible.
- Disable aggressive optimization if it hides useful debugging information.
- Simplify concurrency or worker count when that makes behavior easier to follow.

If the project cannot be run, continue with static reading but explicitly mark confidence lower.

### Phase 2: State the Purpose Clearly

Never begin with aimless reading.

Write down the objective in one sentence:

- "Understand the architecture."
- "Trace the login flow."
- "Learn how this scheduler works."
- "Map the core persistence data structures."

This objective determines what counts as main plot versus side plot.

### Phase 3: Do a Horizontal Pass First

Before going deep, get the shape of the system.

Scan for:

- README and docs,
- entry files,
- build files,
- routing or registration points,
- top-level folders,
- configuration files,
- tests,
- interfaces and major abstractions.

At the end of the horizontal pass, produce a small map:

- key components,
- what each component is responsible for,
- which ones seem central to the current goal.

Also start a `Parking lot` list here so side topics do not hijack the session.

Do not deep dive yet unless the entire system is tiny.

### Phase 4: Separate Main Plot from Side Plots

Maintain two lists while reading:

- `Main plot`: the functions, modules, and data structures directly tied to the current goal.
- `Side plots`: helpers, utilities, abstractions, or lower-level details that are useful but not essential yet.

For side plots, do not fully unpack the implementation unless they block the main plot.

Instead, capture only:

- interface,
- inputs and outputs,
- side effects,
- role in the larger system.

Treat them as black boxes until they become necessary.

### Phase 5: Switch to a Vertical Pass

Once the system shape is roughly clear, follow one concrete path.

For the chosen path, record:

- entrypoint,
- major function or method chain,
- data transformations,
- state transitions,
- external boundaries,
- success path,
- failure path.

Read one path at a time. Do not chase every branch immediately.

### Phase 6: Use Scenario Analysis

Construct one or more concrete scenarios and inspect how the code behaves under them.

Common scenarios:

- happy path,
- boundary condition,
- failure case.

Good tools for scenario analysis:

- breakpoints,
- traces,
- logs,
- debug prints,
- reproducible scripts,
- small input fixtures.

A productive pattern is:

1. Pick an important function as an anchor.
2. Create a scenario that reaches it.
3. Stop there and inspect stack, state, and data.
4. Walk outward from evidence instead of searching blindly.

### Phase 7: Read Tests as Executable Documentation

Well-written tests are focused scenarios. They often reveal behavior faster than production code.

Use tests to answer:

- what the code is expected to do,
- what edge cases matter,
- what setup is minimal,
- what invariants the authors care about.

If tests are strong, they can serve as pre-built scenario analysis.

### Phase 8: Map Core Data Structures

In unfamiliar systems, data structures often reveal the architecture better than individual functions.

Identify a small set of key structures and answer:

- What does this represent?
- Who creates it?
- Who owns it?
- Where does it change?
- Who reads it?
- How long does it live?
- What other structures does it point to or depend on?

If useful, draw a graph or build a small table. The goal is to avoid getting lost inside a large codebase.

### Phase 9: Ask Design Questions

Do not stop at "I can follow the code."

Ask:

- Why was this data structure chosen?
- What is the main abstraction here?
- What complexity is essential, and what is accidental?
- What alternatives might have been possible?
- If I had to change this later, what would be risky?
- If I had to explain this to another engineer, what would I say first?

These questions turn passive reading into active understanding.

### Phase 10: Produce a Reading Artifact

Always finish with output.

Use `reading-note-template.md` in this directory as the default format.

Even if the user asks for a quick explanation, keep the same internal structure and compress it rather than skipping key fields.

Prefer:

- concise notes,
- diagrams,
- tables,
- pseudocode,
- short representative snippets.

Avoid dumping long code blocks. If a long block seems necessary, that is often a sign the explanation is still too close to the source and not yet distilled.

## Deliverable Contract

Unless the user asks for something else, the final deliverable should include:

1. Reading goal and scope.
2. What was run and what was only read statically.
3. System or module map.
4. Main execution path.
5. Parked side plots.
6. Core data structure map.
7. Tests or scenarios worth reading.
8. Open questions and confidence level.
9. A concise reading memo.

If the user asks for a shorter answer, compress the wording, not the structure.

## Red Flags

Stop and correct course if you notice any of these:

- Reading without a stated goal.
- Diving into helpers before understanding system shape.
- Treating every dependency as equally important.
- Following multiple new storylines at once.
- Claiming understanding without producing notes.
- Copy-pasting large code blocks instead of synthesizing them.
- Staying in static reading forever when running the code is feasible.
- Confusing README knowledge with code understanding.

## Default Behavior

When this skill triggers:

1. Identify the primary goal mode.
2. Decide whether the code can be run.
3. Do a horizontal pass.
4. Trace one main storyline vertically.
5. Use tests and scenarios to validate understanding.
6. Map the core data structures.
7. Deliver a reading note, not just commentary.

## Example Requests

- "Help me read this repository."
- "I inherited this codebase. Where do I start?"
- "I just took over this service. Where should I start?"
- "Trace how authentication works in this project."
- "Explain the core data structures in this module."
- "What files should I read first to understand this worker?"
- "I want to understand this codebase without getting lost."

## Related File

- `reading-note-template.md` — default output structure for the reading artifact.
- `test-prompts.md` — example prompts for evaluating whether the skill triggers correctly.
