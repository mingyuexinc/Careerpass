---
name: slice-design
description: Create or revise a Careerpass Vertical Slice development document. Use when selecting a backend Slice, defining its Goal and boundaries, locking API or Handoff contracts, recording data and state changes, or completing Readiness Check before implementation.
---

# Slice Design

## Workflow

1. Read the root and target-project AGENTS.md files.
2. Read the frontend flow, backend delivery scope, capability map, gap analysis, Slice plan, and relevant current facts.
3. Verify the Slice has one Trigger, one primary observable result, explicit Scope and Non-goals, and satisfied predecessor Slices.
4. Create or update the corresponding docs/development/slices/<slice>/slice-spec.md from the project template.
5. Define ownership, authorization, API and task contracts, state transitions, data changes, dependencies, failure behavior, and acceptance criteria.
6. Put a cross-Slice Handoff Contract in the Producer Slice document. Make Consumers reference the same ID and version; do not create a global contract registry.
7. Complete Readiness Check with real evidence for first-use external dependencies and confirm affected global documents are synchronized.
8. Mark unresolved critical decisions blocked. Do not start implementation or hide decisions in a task list.

## Boundaries

- Treat code and migrations as implementation evidence, not automatic approval of current behavior.
- Do not copy unimplemented entities, APIs, states, or future designs from archive material.
- Keep each fact in one source: Slice-specific details in slice-spec.md and stable cross-Slice facts in the matching backend document.
- Never expose credentials, sensitive source text, internal storage paths, or model raw responses.
