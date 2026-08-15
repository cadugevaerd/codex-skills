---
name: precode-system-foundations
description: Create pre-coding system foundation plans.
version: 0.1.0
author: Hermes
metadata:
  hermes:
    tags: [Architecture, PRD, UML, Authorization, Database, Multiuser]
---

# Pre-Coding System Foundations

Use this skill to turn a system idea into a reviewable foundation package before implementation begins. It produces requirements, diagrams, access rules, database invariants, and multi-user separation decisions; it does not write application code or declare the design production-ready. It is framework- and database-neutral: implementation-specific mechanisms must be selected from project evidence, not assumed.

## When to Use

- “Planeje o sistema antes de codificar.”
- “Crie o PRD e a arquitetura inicial.”
- “Defina permissões, banco e multiusuário.”
- “Prepare uma fase para o Spec Kit.”

## Prerequisites

- A system goal, intended users, and at least one business outcome.
- A repository path or an explicit greenfield declaration.
- A named decision owner for unresolved product, security, and data questions.
- Use `read_file` and `search_files` to inspect existing code and docs before treating the work as greenfield.

## How to Run

Use `delegate_task` to inspect existing product, data, and access evidence in parallel when a repository exists. Use `write_file` for the foundation package and `diagram-design` only after the diagram type and content are grounded in the approved model. If material architecture decisions remain open, run `grill-with-docs` before passing a phase to Spec Kit.

## Quick Reference

- Repository evidence: `search_files(pattern="*", target="files", path="<repo>")`
- Read an artifact: `read_file(path="<path>")`
- Create or replace an artifact: `write_file(path="<path>", content="...")`
- Modify an existing artifact: `patch(path="<path>", old_string="...", new_string="...")`
- Parallel discovery: `delegate_task(goal="...")`
- Architecture decisions: `skill_view(name="grill-with-docs")`
- Diagram creation: `skill_view(name="diagram-design")`
- Spec Kit entry gate: `skill_view(name="spec-kit-workflow-entry-governance")`

## Procedure

1. **Inventory evidence and define scope.** Use `search_files` and `read_file` to identify existing PRDs, diagrams, data models, access rules, migrations, and deployment docs. Record the source of each claim as `user-decision`, `code`, `test`, `existing-doc`, or `inference`; unresolved material questions are blockers, not implicit defaults.
2. **Create and maintain the PRD.** Write a PRD that names the problem, users, outcomes, in-scope and out-of-scope behavior, functional requirements, non-functional requirements, acceptance criteria, and open decisions. Make this document the current product source of truth and update it when a user-visible decision changes.
3. **Model the system with UML.** From the approved PRD, produce only the diagrams needed to remove ambiguity: use-case for actors and goals, component for responsibility boundaries, sequence for critical interactions, and class/domain or ER view for durable concepts. Label assumptions; do not invent components merely to complete a diagram.
4. **Define access rules.** Create an authorization matrix with `Actor | Resource | Action | Allow condition | Deny condition | Evidence`. Include administrative, operational, end-user, and service identities only when supported by requirements. Define who may create, read, update, delete, approve, export, or administer each resource relevant to the system.
5. **Specify database locks as invariants.** For every durable entity, state ownership, identity, required fields, uniqueness, valid references, lifecycle constraints, and concurrency rule. Separate application validation from database-enforced invariants; a rule marked database-enforced must map to a real constraint, transaction rule, trigger, or row policy selected later for the actual database.
6. **Design multi-user separation.** State the isolation boundary explicitly: per-user, per-organization/tenant, or another approved domain boundary. Define how ownership is recorded, how every read/write is scoped, how shared resources are authorized, and how cross-boundary access is denied. Treat a UI-only filter as insufficient evidence of separation.
7. **Create the pre-coding plan.** Sequence work into phases with dependencies, artifacts, decision owners, implementation boundary, verification gate, and acceptance criterion. Keep code tasks out until the PRD, diagrams, authorization matrix, database invariants, and separation model have a named status: approved, conditional, or blocked.
8. **Run the entry gate.** Use `grill-with-docs` for unresolved material architectural decisions. When the project uses GitHub Spec Kit, use `spec-kit-workflow-entry-governance` to produce the eligible phase handoff; only a `GO` handoff may enter `specify`.

## Pitfalls

- A PRD that has no explicit scope, acceptance criteria, or owner is not a planning source of truth.
- UML does not replace requirements; diagrams must reflect approved requirements rather than speculative implementation.
- Role names alone are not authorization rules—record actions, resources, conditions, and denials.
- Application checks alone do not satisfy a requirement for database locks.
- “Multi-user” is not automatically tenant isolation; name and test the actual boundary.
- Do not start coding to resolve an unrecorded high-impact decision; mark it blocked or conditional with an owner.

## Verification

The foundation package is ready when a reviewer can trace every in-scope PRD requirement to a UML element, authorization rule, database invariant, isolation rule, planned phase, and acceptance criterion—or see an explicit approved exception or blocker.
