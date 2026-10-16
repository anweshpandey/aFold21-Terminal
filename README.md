# aFold21-Terminal

**A terminal-oriented workflow for running ColabFold-based protein structure predictions through Google Colab.**

`aFold21` is an independently developed command-line wrapper and batch runner. It is intended to make a ColabFold-based prediction workflow easier to launch from a Linux terminal, especially when processing a list of protein sequences. It is not a new prediction model and is not an official ColabFold release.

> **At a glance:** `af21` runs an interactive prediction; `af21-all` reads a CSV/TSV table and processes rows sequentially into separate output directories.

## Background and motivation

Predicting a protein's three-dimensional structure from its amino-acid sequence is an important task in structural biology. AlphaFold2 demonstrated highly accurate structure prediction, while ColabFold made the workflow more accessible by combining AlphaFold2/RoseTTAFold-related prediction workflows with fast multiple-sequence-alignment (MSA) search using MMseqs2 and interfaces including notebooks, a Python package, and command-line tools. The original ColabFold paper describes the scientific method and its performance; aFold21 does not reimplement or claim those scientific advances.

The motivation for aFold21 is practical workflow management: provide a small terminal-facing layer around a remote Colab runtime, accept an individual sequence interactively, process multiple sequences from a table, keep results separated by input identifier, and provide convenience commands for checking or stopping the runtime. The actual prediction software runs remotely in the Colab environment, subject to Google's service availability and policies.

For the full scientific background and methods, read the original ColabFold paper linked below. Do not treat this repository's convenience features as independent scientific validation of the underlying prediction method.

## Features

- `af21`: interactive single-sequence prediction workflow.
- `af21-all`: sequential batch runner for CSV/TSV sequence tables.
- Separate per-ID result directories for batch jobs, including repeated sequences with different IDs.
- Prompt to create a new GPU session when the configured Colab session is unavailable.
- Convenience commands: `af21-status` and `af21-stop`.
- Local output organization for structures, confidence outputs, plots, MSA/input files, logs, and metadata when produced by the workflow.

## Scientific provenance: original notebook, code, and papers

**Original ColabFold code and notebook (upstream; not authored by aFold21):**

- [Official ColabFold repository](https://github.com/sokrypton/ColabFold)
- [Original AlphaFold2 notebook in the repository](https://github.com/sokrypton/ColabFold/blob/main/AlphaFold2.ipynb)
- [Open the notebook in Google Colab](https://colab.research.google.com/github/sokrypton/ColabFold/blob/main/AlphaFold2.ipynb)
- [Upstream ColabFold source code and releases](https://github.com/sokrypton/ColabFold)
- [Upstream MIT license](https://github.com/sokrypton/ColabFold/blob/main/LICENSE)

**Primary ColabFold paper:**

Mirdita M, Schütze K, Moriwaki Y, Heo L, Ovchinnikov S, Steinegger M. *ColabFold: making protein folding accessible to all.* **Nature Methods** 19, 679–682 (2022). DOI: [10.1038/s41592-022-01488-1](https://doi.org/10.1038/s41592-022-01488-1).

- [Publisher article](https://www.nature.com/articles/s41592-022-01488-1)
- [Open-access full text at PubMed Central](https://pmc.ncbi.nlm.nih.gov/articles/PMC9184281/)
- [PubMed record](https://pubmed.ncbi.nlm.nih.gov/35637307/)

**AlphaFold2 paper (cite when appropriate):**

Jumper J, Evans R, Pritzel A, et al. *Highly accurate protein structure prediction with AlphaFold.* **Nature** 596, 583–589 (2021). DOI: [10.1038/s41586-021-03819-2](https://doi.org/10.1038/s41586-021-03819-2).

If you use aFold21 for research, cite the underlying method papers appropriate to the prediction workflow and acknowledge aFold21 as the wrapper used. Complex prediction or other workflows may require additional citations; consult the upstream documentation.

## How aFold21 fits into the workflow

1. The user runs `af21` or `af21-all` on the local Linux machine.
2. The local wrapper validates the sequence/input table and determines the local output directory.
3. The Google Colab CLI is used to find or create the named remote Colab session.
4. The remote runtime installs/uses ColabFold and performs the prediction workflow.
5. Results are bundled and downloaded into local per-run directories.
6. For batch input, the runner processes records sequentially and keeps each ID in a separate directory.

The exact outputs depend on the selected workflow and what the remote runtime successfully produces. See [Workflow and output guide](docs/WORKFLOW.md).

## Requirements and important constraints

- Linux terminal; the package is documented primarily for Linux.
- Miniforge/Miniconda/Anaconda with `conda` available.
- Internet access, a Google account, and Google Colab access.
- The Google Colab CLI installed in the configured Conda environment.
- A GPU runtime must be available to your Colab account. GPU type, quotas, session lifetime, and access are controlled by Google and are not guaranteed.

The default MSA workflow may submit sequences to a public MMseqs2 service. Do not submit confidential, controlled, embargoed, or otherwise sensitive sequences unless permitted by your data-governance requirements and the relevant service terms.

## Installation

Download/extract the repository ZIP or clone the repository, then run from the project directory:

```bash
chmod +x install.sh
./install.sh
```

The installer creates or reuses a Conda environment named `af21`, installs `google-colab-cli`, and installs launchers under `~/.local/bin/`.

If you prefer a different environment name:

```bash
AF21_ENV_NAME=alphafold21 ./install.sh
```

If `~/.local/bin` is not on your PATH, add it once to `~/.bashrc`:

```bash
printf '
export PATH="$HOME/.local/bin:$PATH"
' >> ~/.bashrc
source ~/.bashrc
```

Verify the installation:

```bash
conda activate af21
which af21
which af21-all
af21-all --help
```

If you copied the commands above, note that the help command must be spelled `af21-all --help` (without a space).

## Single prediction

```bash
conda activate af21
af21
```

Follow the prompts to enter the protein sequence and output directory. If the configured Colab session does not exist, the program asks whether to create a new GPU session. Accepting the prompt uses the equivalent of:

```bash
colab --auth=oauth2 new -s alphafold21 --gpu T4
```

Complete the official Colab CLI authentication flow when requested. Never share OAuth tokens, authentication codes, or session configuration files.

Convenience commands:

```bash
af21-status
af21-stop
```

The equivalent subcommands `af21 status` and `af21 stop` are also available.

## Batch predictions

Create a CSV with `ID` and `Sequence` columns (or start from `example_sequences.csv`):

```csv
ID,Sequence
ID_01,MKTVRQERLKSIVRILERSKEPVSGAQLAEELSVSRQVIVQDIAYLR
ID_02,MAHHHHHHSSGVDLGTENLYFQSM
```

Run sequentially:

```bash
af21-all sequences.csv --output-root ./batch_results
```

For nonstandard column names:

```bash
af21-all table.tsv --id-column ProteinID --sequence-column AASequence --output-root ./batch_results
```

To continue processing after a failed row (if supported by the installed batch runner):

```bash
af21-all sequences.csv --output-root ./batch_results --continue-on-error
```

Each identifier receives a separate output directory. Non-empty output directories are skipped to reduce the risk of overwriting existing results. Review the batch runner's `--help` output for the options supported by your installed version. The remote session is not necessarily stopped automatically after the batch; stop it when you are finished and have confirmed downloads completed.

## Colab session manager and free-tier quota notes

The installer also installs an optional Conda activation hook for interactive terminals. When you run `conda activate af21`, it checks the configured Colab session and prints the session status and the usage fields exposed by the Colab CLI. If the session is missing or unavailable, it offers a menu for checking status, signing in/switching accounts, creating a session with the current account, checking usage, or returning without connecting.

The hook does **not** automatically create a GPU runtime during activation. It is skipped in non-interactive shells and batch jobs, so it does not consume standard input or interrupt unattended runs. You can configure the session, auth mode, and requested GPU using `AF21_SESSION` (default `alphafold21`), `AF21_AUTH` (default `oauth2`), and `AF21_GPU` (default `T4`).

**Free-tier quota limitation:** the CLI exposes usage information such as compute-unit balance, usage rate, and active assignments, but not a fixed free-tier quota total. Google free-tier limits are dynamic. As a result, aFold21 cannot reliably calculate percentage remaining or produce a meaningful 90%-used warning for free-tier access. A displayed `0.00` compute-unit balance is not a free-tier quota percentage. See [`docs/COLAB_SESSION_MANAGER.md`](docs/COLAB_SESSION_MANAGER.md) for details.

## Repository map

- `af21.py` — interactive single-prediction and session-management wrapper.
- `af21_batch.py` — sequential table-driven batch runner.
- `install.sh` — local environment and launcher installer.
- `example_sequences.csv` — example input schema using illustrative sequences.
- `docs/BACKGROUND.md` — expanded background and scientific provenance.
- `docs/WORKFLOW.md` — workflow, outputs, troubleshooting, and interpretation notes.
- `docs/REFERENCES.md` — references and upstream code links.
- `NOTICE.md` — provenance, attribution, and non-affiliation notice.
- `CITATION.cff` — citation metadata for this wrapper.

## Limitations and responsible use

- aFold21 is a workflow wrapper; it is not a new protein-folding model or a substitute for the upstream ColabFold software.
- Colab GPU access, quotas, sessions, network services, and upstream dependencies can change.
- Predicted structures are computational models, not experimental structures. Evaluate confidence scores and biological plausibility, and use independent evidence where required.
- Follow upstream licenses, Google Colab terms, and institutional/data-sharing policies.
- The software is provided as-is, without guarantees of uninterrupted service or scientific suitability for a particular application.

## License

The aFold21 wrapper/tooling in this repository is released under the MIT License; see `LICENSE`. ColabFold, AlphaFold-related components, Google Colab, and other third-party software/services remain under their respective licenses and terms. This repository does not relicense upstream components.


### Batch recovery behavior

The batch runner treats a non-empty `structures/best_model.pdb` as a completed
prediction and skips that ID. If the file is absent, it retries that ID in the
existing directory while preserving previous logs and other files. Review
partial outputs before rerunning if you need strict reproducibility.
