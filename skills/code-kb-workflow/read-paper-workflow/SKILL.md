---
name: read-paper-workflow
description: Read papers, articles, reports, and other non-code source documents methodically instead of summarizing them loosely. Use this skill when the user wants to understand a research paper, technical report, whitepaper, essay, RFC, or document corpus; extract the main contribution or argument; trace one evidence path; compare claims and limitations; or turn document reading into a durable reading note for a knowledge base.
---

# Read Paper Workflow

> A document-reading companion to `read-code-workflow`, adapted for papers, articles, reports, and mixed non-code source corpora.

## Overview

Read source documents with a purpose, an argument map, and an output artifact.

Do not read a paper linearly and then stop at a vague summary. Start with the question you need answered, identify the main contribution or argument, trace one evidence path end to end, and force understanding into a durable note, diagram, or concise explanation.

## Quick Reference

- Start with the reading goal, not with passive summarization.
- Prefer primary-source evidence over secondhand interpretation.
- Read horizontally before reading vertically.
- Keep a parking lot for side plots so they do not derail the main argument.
- Separate author claims from your inferences.
- End with a written reading artifact, not just a chatty explanation.

## When to Use

Use this skill when the user is mainly trying to understand non-code source material.

Common cases:

- reading a research paper, whitepaper, RFC, or technical report,
- understanding the contribution of a paper before writing notes,
- tracing one argument or evidence chain through a long document,
- comparing papers or source documents on one question,
- building a knowledge base from articles, reports, transcripts, or mixed source files,
- turning raw source documents into a durable reading note.

## When Not to Use

Route elsewhere when the main task is:

- reading source code as the primary object,
- implementing a feature or fixing a bug,
- reviewing a PR for findings-first feedback,
- writing a polished research article when the source-understanding pass is already complete.

If understanding the document corpus is the prerequisite for one of those tasks, use this skill first, then hand off.

## Minimum Execution Contract

When this skill triggers, do not stop at a vague summary. Always do enough work to provide:

1. A clearly stated reading goal and scope.
2. A note about the evidence type and whether the reading is static-only.
3. A small document, section, or source map.
4. One main claim, contribution, or argument traced end to end.
5. A parking lot of side plots that were intentionally deferred.
6. A map of the most important claims, methods, evidence units, or entities.
7. Open questions, limitations, next verification steps, and confidence.

Use `reading-note-template.md` unless the user explicitly wants a different format.

## Core Principles

1. Define the reading goal before diving into details.
2. Distinguish author claims from your inferences.
3. Separate the main plot from side plots.
4. Alternate horizontal reading and vertical reading.
5. Prioritize evidence paths over isolated quotes.
6. Track methods, data, and limitations, not just conclusions.
7. Turn input into output through notes, diagrams, and questions.

## First Move

Before diving in, determine four things:

- The primary reading goal.
- The desired depth.
- What kind of evidence the document provides.
- The deliverable the user wants.

Evidence-type defaults:

- `Empirical` for papers with experiments, datasets, or measurements.
- `Formal` for math-heavy, proof-heavy, or specification-heavy material.
- `Conceptual` for essays, manifestos, or design-philosophy documents.
- `Review` for surveys, literature reviews, or comparison reports.

If the request is vague, default to:

- a high-level contribution pass,
- one important evidence path,
- the core claims and limitations,
- and a written reading note.

## Scaling Rules

If the corpus is too large, the document is long, or the user only wants a fast orientation pass, downscope deliberately instead of pretending to cover everything.

Default reduced scope:

- one paper or seed source,
- three to seven key sections or source clusters,
- one representative claim or argument path,
- three to five core claims, methods, or evidence units,
- and a short list of open questions.

Label the result as partial when you do this.

## Goal Modes

Choose one primary mode. Park secondary curiosities unless they block the main objective.

If the user does not specify a mode:

- choose `Contribution Mode` for broad "what is this paper saying?" requests,
- choose `Argument Mode` for "how does this claim hold up?" requests,
- choose `Method Mode` for method-heavy or experiment-heavy papers,
- choose `Evidence Mode` for "what supports this conclusion?" requests,
- choose `Comparison Mode` when the user cares about differences across documents.

### 1. Contribution Mode

Use when the user wants the shape of the document.

Focus on:

- the main contribution,
- the problem framing,
- the intended audience,
- the section structure,
- the claimed significance.

Start horizontally, then trace one representative argument or evidence path end to end.

### 2. Argument Mode

Use when the user wants to understand or evaluate one claim well.

Focus on:

- thesis,
- subclaims,
- assumptions,
- evidence chain,
- counterpoints,
- limits.

### 3. Method Mode

Use when the user wants to understand how the work was done.

Focus on:

- research question,
- setup,
- data or source base,
- procedure,
- evaluation method,
- threat model or assumptions.

### 4. Evidence Mode

Use when understanding depends on what supports the conclusion.

Focus on:

- evidence units,
- where each claim is supported,
- what is measured or observed,
- where interpretation begins,
- what remains weak or unverified.

### 5. Comparison Mode

Use when the user wants to compare multiple documents or positions.

Focus on:

- shared question,
- points of agreement,
- points of divergence,
- evidence quality,
- terminology drift,
- decision-useful takeaways.

## Workflow

### Phase 1: Classify the Source and Evidence Type

Determine what kind of document you are reading and what counts as evidence in it.

Ask:

- Is this empirical, formal, conceptual, or review-style?
- What does the document treat as proof or support?
- Are there appendices, figures, tables, or references that matter?

If the corpus is mixed, say so explicitly and note which parts carry the most evidentiary weight.

### Phase 2: State the Purpose Clearly

Never begin with aimless summarization.

Write down the objective in one sentence:

- "Understand the paper's main contribution."
- "Trace the evidence for the central claim."
- "Map the method and evaluation setup."
- "Compare this report with another source."

This objective determines what counts as main plot versus side plot.

### Phase 3: Do a Horizontal Pass First

Before going deep, get the shape of the document.

Scan for:

- title, abstract, introduction, and conclusion,
- section headings,
- figures, tables, and appendices,
- explicit contribution statements,
- evaluation sections,
- stated limitations,
- references that define the context.

At the end of the horizontal pass, produce a small map:

- key sections or source clusters,
- what each one is doing,
- which ones seem central to the current goal.

Also start a `Parking lot` list here so side topics do not hijack the session.

Do not deep dive yet unless the document is tiny.

### Phase 4: Separate Main Plot from Side Plots

Maintain two lists while reading:

- `Main plot`: the sections, claims, methods, and evidence directly tied to the current goal.
- `Side plots`: related background, digressions, implementation details, citations, or secondary claims that are useful but not essential yet.

For side plots, do not fully unpack them unless they block the main plot.

Instead, capture only:

- what the side topic is,
- what role it plays,
- what claim or section it connects to,
- why it was deferred.

### Phase 5: Switch to a Vertical Pass

Once the document shape is roughly clear, follow one concrete path.

Examples:

- one contribution claim through its supporting sections,
- one method through setup, evaluation, and limitation sections,
- one controversial assertion through the exact evidence that supports it,
- one comparison question across multiple documents.

Follow that path until you can explain:

- what is being claimed,
- what supports it,
- where the reasoning strengthens,
- where it weakens,
- and what remains uncertain.

### Phase 6: Map Claims, Methods, and Evidence Units

Identify the most important structured elements.

Depending on the corpus, these may include:

- claims,
- hypotheses,
- datasets,
- experiments,
- metrics,
- assumptions,
- definitions,
- design principles,
- recommendations,
- limits.

Do not flatten everything into one summary paragraph. Use a table or compact map.

### Phase 7: Capture Limits, Open Questions, and Confidence

Close by recording:

- what the document does not establish,
- what you are inferring rather than reading directly,
- what should be verified next,
- how confident you are in the reading pass.

Confidence should be lower when:

- the corpus is partial,
- the evidence is indirect,
- important appendices were skipped,
- or the document uses terminology you could not resolve cleanly.

## Deliverable Guidance

The default final artifact is a reading note that another person or agent can reuse quickly.

It should help someone answer:

- What is this document trying to do?
- What is the main contribution or argument?
- What evidence supports it?
- What should I trust, question, or read next?

Use `reading-note-template.md` unless the user explicitly wants a different format.
