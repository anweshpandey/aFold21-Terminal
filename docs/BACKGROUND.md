# Background and scientific context

## Protein structure prediction

Protein structure prediction estimates a three-dimensional structure from sequence and related biological information. AlphaFold2 showed that deep-learning approaches can achieve high accuracy for many protein targets. ColabFold made the AlphaFold2/RoseTTAFold ecosystem easier to access by pairing prediction workflows with accelerated multiple-sequence-alignment search based on MMseqs2 and providing notebooks, a Python package, and command-line interfaces. These scientific contributions belong to the upstream teams and are described in their publications.

## Why aFold21 exists

`aFold21` addresses a workflow usability need rather than a new scientific method. It offers terminal commands for interactive predictions and sequential processing of sequence tables, separates results by input ID, and provides basic session convenience commands for a remote Google Colab runtime. This can be useful for researchers who want to integrate a prediction workflow into a Linux-based routine without installing all prediction models and databases locally.

## What is and is not contributed here

The aFold21 contribution is the local wrapper, batch orchestration, prompt/session handling, installer, output organization, and documentation. It does not claim authorship of ColabFold, AlphaFold2, MMseqs2, model weights, training datasets, or the scientific methods in the cited papers. Prediction quality is inherited from the underlying workflow and should not be represented as independently benchmarked by aFold21 unless a separate benchmark is conducted.

## Upstream resources

- ColabFold repository and source: https://github.com/sokrypton/ColabFold
- ColabFold AlphaFold2 notebook: https://github.com/sokrypton/ColabFold/blob/main/AlphaFold2.ipynb
- ColabFold paper: https://doi.org/10.1038/s41592-022-01488-1
- AlphaFold2 paper: https://doi.org/10.1038/s41586-021-03819-2

For scientific use, read the upstream methods and documentation because the exact behavior, options, and limitations depend on the ColabFold version and workflow being run.
