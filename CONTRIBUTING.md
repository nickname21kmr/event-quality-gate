# Contributing

This project uses small, evidence-backed changes. Each change should explain the problem, add or update tests, and record the verification command.

## Workflow

1. Open or select a real issue.
2. Create a focused branch such as `feat/junit-report` or `fix/datetime-offset`.
3. Add the smallest complete implementation and regression tests.
4. Run:

   ```bash
   python -m unittest discover -s tests -v
   python -m compileall -q src
   ```

5. Open a pull request that links the issue and lists the checks performed.
6. Merge only after CI passes.

Avoid empty commits, generated activity, unrelated formatting changes, and claims unsupported by fixtures or tests.

## Design principles

- Standard-library runtime whenever practical.
- Deterministic reports for the same contract and input.
- Streaming input: do not load the full dataset into memory.
- Explicit exit codes for automation.
- Synthetic fixtures only; never commit production event data or credentials.
