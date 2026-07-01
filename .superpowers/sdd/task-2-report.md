# Task 2 Report: Strict Result Structure and Model Error Normalization

## Status

Completed through implementation commit `8b5f18c` (`reject extra rubric dimensions`); the full Task 2 commit chain is recorded below.

## Scope

- Tightened `validate_result` so issues are non-empty, limited to 1–3, paired one-to-one with suggestions, and accompanied by a non-empty summary.
- Added the strict Responses API JSON schema for all scores and text fields.
- Added `ModelTimeoutError`, `ModelUnavailableError`, and `ModelResponseError`.
- Normalized `HTTPError` and other `URLError` instances as unavailable; normalized `TimeoutError` as timeout; normalized malformed response payloads as response errors.
- Retried exactly once for `ModelResponseError` and validation `ValueError`; timeout and unavailable errors are not caught by the retry loop.
- Added focused regression coverage without changing API, frontend, or deployment files.

## TDD Evidence

### RED

Command:

`python -m unittest tests.test_analyzer -v`

Observed result: import failed because `core.model_client.ModelResponseError` and the other required public error types did not exist. This was the expected missing-interface failure before production implementation.

### GREEN

Focused command:

`python -m unittest tests.test_analyzer tests.test_rubric -v`

Observed result: 17 tests ran, all passed.

Full command:

`python -m unittest discover -v`

Observed result: 30 tests ran, all passed in 0.600 seconds.

Additional check:

`git diff --check`

Observed result: exit code 0. Git emitted only existing line-ending conversion notices (LF to CRLF), with no whitespace errors.

## Self-review

- Verified `HTTPError` is caught before `URLError`, preserving the required 429/unavailable mapping.
- Verified the retry loop catches only response/validation failures and makes at most two total attempts.
- Verified all code changes are confined to the four requested Task 2 files.
- No secrets or live credentials were added; tests use a placeholder API key.

## Concerns

None blocking. The repository's Git configuration reports LF-to-CRLF conversion notices for the touched files; these do not affect tests or the committed content.

## Important Review Fixes

- Normalized HTTP 200 response-body UTF-8 decoding failures and outer JSON parsing failures as `ModelResponseError`, allowing the analyzer's existing response-error policy to make exactly two total attempts.
- Made `validate_result` explicitly reject non-dict top-level values with `ValueError`; arrays, strings, and null are covered, along with a two-attempt analyzer regression test.

### TDD Evidence

RED command: `python -m unittest tests.test_analyzer tests.test_rubric -v`

Observed result: 21 tests ran with 7 expected errors. Corrupt response bodies leaked `UnicodeDecodeError` / `JSONDecodeError`, and non-object results leaked `AttributeError`, so neither path reached the required retry policy.

GREEN focused command: `python -m unittest tests.test_analyzer tests.test_rubric -v`

Observed result: 21 tests ran, all passed.

Full command: `python -m unittest discover -v`

Observed result: 34 tests ran, all passed in 0.613 seconds.

## Remaining Important Review Fixes

- Required `scores` to be a dict, `issues` and `suggestions` to be lists whose items are strings, and `summary` to be a string.
- Removed silent string conversion of issue, suggestion, and summary values.
- Preserved `int()` score normalization, including numeric strings, while normalizing score conversion type errors to `ValueError`.
- Added malformed nested-value coverage for null containers, non-string list items, and a non-string summary.
- Added an analyzer regression proving a malformed nested result triggers exactly two model calls.

### TDD Evidence

RED command: `python -m unittest tests.test_rubric.RubricTests.test_validate_result_rejects_malformed_nested_values tests.test_analyzer.AnalyzerTests.test_malformed_nested_result_is_retried_once`

Observed result: 2 tests produced 4 errors and 4 failures. Null containers leaked `TypeError`; non-string list items and summary values were silently accepted.

GREEN focused command: `python -m unittest tests.test_rubric tests.test_analyzer`

Observed result: 23 tests ran, all passed.

Full command: `python -m unittest discover -s tests -v`

Observed result: 36 tests ran, all passed in 0.658 seconds.

Additional check: `git diff --check` exited 0 with only existing LF-to-CRLF conversion notices.

## Final Important Review Fix

`validate_result` now requires the `scores` key set to equal `DIMENSIONS` exactly. A payload containing all five required dimensions plus a sixth dimension raises `ValueError` with the explicit message `额外评分维度: <name>`. The analyzer regression confirms this validation failure causes exactly two total model calls.

### Final commit chain

1. `34880dc` - harden model result handling
2. `34461e6` - fix task 2 response validation gaps
3. `ebf636c` - tighten nested rubric validation
4. `8b5f18c` - reject extra rubric dimensions

This report appendix is committed immediately after the final implementation commit above; `8b5f18c` is the final Task 2 production/test change.

### Latest TDD and verification evidence

RED command: `python -m unittest tests.test_rubric.RubricTests.test_validate_result_rejects_extra_dimension tests.test_analyzer.AnalyzerTests.test_extra_score_dimension_is_retried_once -v`

Observed result: 2 tests failed because no `ValueError` was raised, confirming the extra dimension was silently accepted before the fix.

GREEN regression command: the same command above.

Observed result: 2 tests ran, all passed.

Focused command: `python -m unittest tests.test_rubric tests.test_analyzer -v`

Observed result: 25 tests ran, all passed.

Full command: `python -m unittest discover -s tests -v`

Observed result: 38 tests ran, all passed in 0.639 seconds.

Additional check: `git diff --check` exited 0 with only the repository's existing LF-to-CRLF conversion notices.
