---
name: "code-review-cadu"
description: "Code review de pull request com veredicto GO/NO-GO por finding sobre o merge — NO-GO = merge bloqueado, corrigir nesta PR; GO = merge pode seguir, finding diferível registrado no backlog do projeto (.specify/backlog.json via skill /backlog). Use quando for revisar uma PR do GitHub e quiser a triagem automática dos findings entre 'bloqueia merge' e 'diferir para o backlog'. Fork personalizado (Cadu) do plugin oficial code-review da Anthropic."
argument-hint: "<número ou URL da PR>"
---

# Code Review (Cadu) — PR review with GO/NO-GO verdict

Fork of the official Anthropic `code-review` plugin (Apache-2.0 — see the
plugin's LICENSE file), extended with: a **GO/NO-GO verdict per finding** —
the verdict is about the MERGE (**NO-GO** = merge blocked, fix in this PR;
**GO** = merge may proceed, finding is deferrable) — and **backlog
integration** for deferred items (GO → `.specify/backlog.json` via the
`/backlog` skill).

Provide a code review for the given pull request.

To do this, follow these steps precisely:

1. Use a lightweight reviewer pass or subagent to check if the pull request (a) is closed, (b) is a draft, (c) does not need a code review (eg. because it is an automated pull request, or is very simple and obviously ok), or (d) already has a code review from you from earlier. If so, do not proceed.
2. Use another lightweight reviewer pass or subagent to give you a list of file paths to (but not the contents of) any relevant instruction files from the codebase: root `AGENTS.md`/`CLAUDE.md` files if they exist, as well as any such files in directories whose files the pull request modified.
3. Use a lightweight reviewer pass or subagent to view the pull request, and ask it to return a summary of the change.
4. Then, launch 5 parallel reviewer passes/subagents to independently code review the change — plus 2 ADDITIONAL parallel reviewer passes/subagents (#6 and #7) IF the project uses LangGraph / LangChain / LangSmith (detect first with a fast grep for `langgraph`, `langchain` or `langsmith` in dependency manifests — `pyproject.toml`, `requirements*.txt`, `package.json` — or in the imports of the changed files). The reviewers should do the following, then return a list of issues and the reason each issue was flagged (eg. instruction-file adherence, bug, historical git context, etc.):
   a. Reviewer #1: Audit the changes to make sure they comply with the relevant `AGENTS.md`/`CLAUDE.md` instructions. Note that these files are guidance for coding agents as they write code, so not all instructions will be applicable during code review.
   b. Agent #2: Read the file changes in the pull request, then do a shallow scan for obvious bugs. Avoid reading extra context beyond the changes, focusing just on the changes themselves. Focus on large bugs, and avoid small issues and nitpicks. Ignore likely false positives.
   c. Agent #3: Read the git blame and history of the code modified, to identify any bugs in light of that historical context
   d. Agent #4: Read previous pull requests that touched these files, and check for any comments on those pull requests that may also apply to the current pull request.
   e. Agent #5: Read code comments in the modified files, and make sure the changes in the pull request comply with any guidance in the comments.
   f. Reviewer #6 (LangGraph/LangChain projects only): Validate that the changes follow the **Thinking in LangGraph** methodology. Check: minimal state carrying RAW data, not formatted text (CRUE rule); routing via `status` flag + State-Check (NEVER `interrupt()` for handoff); the deterministic/non-deterministic boundary is explicit — critical guarantees (validation, authorization, persistence invariants) implemented in deterministic code/subgraphs, never delegated to ReAct/`create_agent` discretion; fixed flows (ingestion, validation pipelines) as deterministic subgraphs; internal routing via `Command(update=..., goto=...)`; error handling discriminated (transient → `RetryPolicy`; recoverable → LLM loop; structural/unexpected → `raise`, never silently swallowed); internal (non user-facing) LLM `.invoke()` calls suppress AG-UI streaming (`config={"metadata": {"emit-messages": False, "emit-tool-calls": False}}`). If the repo's instruction files or constitution define these conventions (eg. a "Thinking in LangGraph" section), cite the specific rule violated.
   g. Reviewer #7 (LangGraph/LangChain projects only; return no issues if the diff does not touch code that uses `ChatOpenRouter`): Validate that the changes respect the **official ChatOpenRouter integration docs** — the reviewer MUST first fetch https://docs.langchain.com/oss/python/integrations/chat/openrouter with the available web/documentation tool and review the diff against it. Check at minimum: multimodal content blocks use the canonical format (PDF/documents MUST be `{"type": "file", "base64"/"url": ..., "mime_type": "application/pdf"}` blocks — NEVER `image`/`image_url`, whose mime_type only accepts image/jpeg|png|gif|webp); model fallback chains send payloads valid for ALL models in the chain (not just the primary — eg. a payload Gemini tolerates but Anthropic/Bedrock/Vertex reject 400 is a bug); reasoning budget vs `max_tokens` (reasoning tokens count against the cap → `finish_reason=length` with empty tool calls and no exception); `with_structured_output` method/strict choices; `openrouter_provider` routing params. If the repo has a `/chatopenrouter` skill, use it as the quick-reference.
5. For each issue found in #4, launch a parallel scoring pass/subagent that takes the PR, issue description, and list of instruction files (from step 2), and returns a score to indicate its level of confidence for whether the issue is real or false positive. To do that, the scoring pass should score each issue on a scale from 0-100, indicating its level of confidence. For issues that were flagged due to instruction-file rules, the scoring pass should double check that the instruction file actually calls out that issue specifically. The scale is (give this rubric to the scoring pass verbatim):
   a. 0: Not confident at all. This is a false positive that doesn't stand up to light scrutiny, or is a pre-existing issue.
   b. 25: Somewhat confident. This might be a real issue, but may also be a false positive. The scoring pass wasn't able to verify that it's a real issue. If the issue is stylistic, it is one that was not explicitly called out in the relevant instruction file.
   c. 50: Moderately confident. The scoring pass was able to verify this is a real issue, but it might be a nitpick or not happen very often in practice. Relative to the rest of the PR, it's not very important.
   d. 75: Highly confident. The scoring pass double checked the issue, and verified that it is very likely it is a real issue that will be hit in practice. The existing approach in the PR is insufficient. The issue is very important and will directly impact the code's functionality, or it is an issue that is directly mentioned in the relevant instruction file.
   e. 100: Absolutely certain. The scoring pass double checked the issue, and confirmed that it is definitely a real issue, that will happen frequently in practice. The evidence directly confirms this.

   The scoring pass MUST end its reply with a final line in exactly this format: `SCORE: <integer 0-100>` — no prose after it.
6. Coerce each score, then filter:
   a. **Total coercion, never case enumeration.** The score arrives in an LLM reply — an open domain. Do not parse it by enumerating expected shapes ("if it looks like `NN`, elif `NN/100`, ..."). Coerce ANY reply to an integer: take the number from the final `SCORE:` line if present (match is case-insensitive and tolerates trailing prose; within that line the first number wins); otherwise take the last number anywhere in the reply; accept floats (`82.5` → 82), fractions (`85/100` → 85) and percents (`85%` → 85); clamp the result to [0, 100].
   b. **Never drop a finding on a parse failure (fail-loud).** If no number can be extracted at all, re-run that scoring pass once; if the reply still cannot be coerced, treat the score as indeterminate: KEEP the finding, mark it `[score: indeterminate]`, and surface it to the user for a manual call — never silently discard it. A silent drop corrupts the review. Indeterminate findings get no verdict in step 7 and are NOT posted in the PR comment (step 9); list them only in the conversation for the user to decide.
   c. Filter out issues with a coerced score below 75. If no issues remain (and none are indeterminate), do not proceed.
7. Assign a **verdict about the merge** to each issue that passed the filter, with a one-line justification:
   - **NO-GO** — the merge must NOT proceed with this issue pending: fix it in this PR. Criteria: correctness, security, data loss/corruption, regression, or breaking the contract with real infrastructure.
   - **GO** — the merge may proceed: the issue is deferrable with no merge risk. Criteria: cleanup, refactor, technical debt, efficiency/style improvement, unlikely edge case.
8. Use a lightweight reviewer pass or subagent to repeat the eligibility check from #1, to make sure that the pull request is still eligible for code review.
9. Use the gh bash command to comment back on the pull request with the result. When writing your comment, keep in mind to:
   a. Keep your output brief
   b. Avoid emojis
   c. Link and cite relevant code, files, and URLs
   d. Prefix every issue with its verdict: `**[NO-GO]**` (merge blocked, fix in this PR) or `**[GO → backlog]**` (merge may proceed, deferred)
10. Backlog flow for the GO issues (NEVER register automatically):
    a. After posting the PR comment, present the user (in the conversation) a summary table: `# | finding | verdict | justification`.
    b. Ask the user to confirm which GO issues should go to the backlog.
    c. After the user's OK, register the confirmed GO issues in batch in the project's backlog (`.specify/backlog.json`) via the `/backlog` skill, and report the generated `BL-NNNN` id next to each finding.
    d. If the project does not have `.specify/backlog.json`, offer the `/backlog` bootstrap before registering.

Examples of false positives, for steps 4 and 5:

- Pre-existing issues
- Something that looks like a bug but is not actually a bug
- Pedantic nitpicks that a senior engineer wouldn't call out
- Issues that a linter, typechecker, or compiler would catch (eg. missing or incorrect imports, type errors, broken tests, formatting issues, pedantic style issues like newlines). No need to run these build steps yourself -- it is safe to assume that they will be run separately as part of CI.
- General code quality issues (eg. lack of test coverage, general security issues, poor documentation), unless explicitly required in `AGENTS.md`/`CLAUDE.md`
- Issues that are called out in `AGENTS.md`/`CLAUDE.md`, but explicitly silenced in the code (eg. due to a lint ignore comment)
- Changes in functionality that are likely intentional or are directly related to the broader change
- Real issues, but on lines that the user did not modify in their pull request

Notes:

- Every field you consume from a reviewer/scoring reply (eligibility, summary, scores) is an open-domain LLM payload: demand a fixed output format in the prompt, coerce totally on consumption (never by enumerating expected cases), and treat an uncoercible reply as indeterminate + visible — never as a silent default.
- Do not check build signal or attempt to build or typecheck the app. These will run separately, and are not relevant to your code review.
- Use `gh` to interact with Github (eg. to fetch a pull request, or to create inline comments), rather than web fetch
- Make a todo list first
- You must cite and link each bug (eg. if referring to an `AGENTS.md` or `CLAUDE.md`, you must link it)
- For your final comment, follow the following format precisely (assuming for this example that you found 3 issues):

---

### Code review

Found 3 issues (2 NO-GO / 1 GO):

1. **[NO-GO]** <brief description of bug> (`AGENTS.md` says "<...>")

<link to file and line with full sha1 + line range for context, note that you MUST provide the full sha and not use bash here>

2. **[NO-GO]** <brief description of bug> (some/other/AGENTS.md says "<...>")

<link to file and line with full sha1 + line range for context>

3. **[GO → backlog]** <brief description of bug> (bug due to <file and code snippet>)

<link to file and line with full sha1 + line range for context>

Generated with Codex.

<sub>- If this code review was useful, please react with 👍. Otherwise, react with 👎.</sub>

---

- Or, if you found no issues:

---

### Code review

No issues found. Checked for bugs and instruction-file compliance.

Generated with Codex.

- When linking to code, follow the following format precisely, otherwise the Markdown preview won't render correctly: https://github.com/anthropics/claude-cli-internal/blob/c21d3c10bc8e898b7ac1a2d745bdc9bc4e423afe/package.json#L10-L15
  - Requires full git sha
  - You must provide the full sha. Commands like `https://github.com/owner/repo/blob/$(git rev-parse HEAD)/foo/bar` will not work, since your comment will be directly rendered in Markdown.
  - Repo name must match the repo you're code reviewing
  - # sign after the file name
  - Line range format is L[start]-L[end]
  - Provide at least 1 line of context before and after, centered on the line you are commenting about (eg. if you are commenting about lines 5-6, you should link to `L4-7`)
