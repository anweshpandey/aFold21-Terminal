# Workflow and output guide

## High-level execution

1. Launch `af21` for an interactive run or `af21-all` for a CSV/TSV batch.
2. Validate input sequences and identify a local output directory.
3. Check whether the configured remote session exists. If it is missing, the wrapper can ask whether to create a new T4 session. The corresponding CLI command is `colab --auth=oauth2 new -s alphafold21 --gpu T4` (the session name/authentication can be configured).
4. Use the Google Colab CLI to prepare the remote runtime and invoke the ColabFold workflow.
5. Download the result archive into the local output directory. Batch jobs are run sequentially with separate output folders.

## Batch input

The default columns are `ID` and `Sequence`. Each row is a job. Repeated sequences under different IDs remain separate rows and are treated as separate jobs. Check `af21-all --help` for available options and the accepted file formats in the installed version.

## Result folders

The wrapper aims to organize outputs into folders such as:

- `structures/`: predicted coordinate files (for example PDB/mmCIF, depending on workflow).
- `confidence/`: confidence scores/JSON files when generated.
- `plots/`: confidence or alignment visualizations when generated.
- `msa/`: multiple-sequence alignment artifacts when generated.
- `inputs/`: sequence/FASTA or run input records.
- `logs/`: run logs.
- `metadata/`: run settings and metadata.
- `archives/`: downloaded result bundle.

Exact contents vary by successful prediction, upstream software version, and runtime. Do not assume every folder or file will be present for every run.

## Session management

- Check status with `af21-status` or `af21 status`.
- Stop the remote runtime with `af21-stop` or `af21 stop` when the batch and downloads are complete.
- A stopped or reclaimed session may need to be created again. Colab GPU access and runtime persistence are not guaranteed.

## Troubleshooting

- **Session not found:** launch `af21` and accept the prompt to create a new session, or run the printed `colab --auth=oauth2 new -s alphafold21 --gpu T4` command.
- **Authentication issue:** follow the installed Colab CLI's OAuth flow; never paste credentials or tokens into issues.
- **Timeout or remote execution error:** check `colab --auth=oauth2 status -s alphafold21`, inspect the CLI output, and retry a single short test before restarting a large batch.
- **Batch row failure:** preserve the failed row's logs and output folder, verify the sequence/input format, and consult `af21-all --help`.
- **Missing output files:** inspect the downloaded archive and remote execution log. Some outputs are conditional on the workflow.

## Interpreting predictions responsibly

Predicted structures and confidence metrics are not experimental validation. Interpret pLDDT, PAE, pTM/ipTM where available, oligomeric state, sequence coverage, and biological context appropriately. Use experimental evidence or independent validation when conclusions require it.
