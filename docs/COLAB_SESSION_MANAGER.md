# Colab session manager

The optional session manager checks the configured Google Colab CLI session when the `af21` Conda environment is activated interactively.

## Behavior

- If the named session is available, it prints the session status and the usage information exposed by `colab usage`.
- If the session is missing or unavailable, it offers a menu to check status, authenticate/switch account, create a session with the current account, inspect usage, or return without connecting.
- It never silently creates a GPU runtime during Conda activation.
- It skips the menu in non-interactive shells, so batch jobs are not interrupted and standard input is not consumed.

Environment variables:
- `AF21_SESSION` — session name (default `alphafold21`)
- `AF21_AUTH` — Colab CLI auth mode (default `oauth2`)
- `AF21_GPU` — GPU requested when creating a session (default `T4`)

## Free-tier quota limitation

The CLI reports fields such as compute-unit balance, usage rate, and active assignments. These do not provide a fixed free-tier quota denominator. Google's free-tier limits and availability are dynamic, so this manager does not calculate a quota percentage or claim to warn at 90% usage. A displayed `0.00` compute-unit balance is not a statement that 0% of free-tier access remains.

## Installation

The repository installer copies the helper and activation hook into the user's local aFold21 directory and the `af21` Conda environment. To enable the hook in an existing installation, rerun `./install.sh` from the repository, then reactivate the environment:

```bash
conda deactivate
conda activate af21
```

The hook is only installed for the environment selected by `AF21_ENV_NAME` (default `af21`). The session manager is convenience tooling and does not alter the prediction model or ColabFold scientific workflow.
