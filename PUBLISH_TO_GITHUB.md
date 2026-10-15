# Publish aFold21 to GitHub for the first time

These instructions assume you have not yet created or pushed the aFold21 repository.

## 1. Install and authenticate GitHub CLI

Install Git and GitHub CLI if needed: https://cli.github.com/

```bash
git --version
gh --version
gh auth login
gh auth status
```

Follow the browser-based authentication flow. Do not place a password, access token, or Colab credential in the repository.

## 2. Open a terminal in the extracted project folder

```bash
cd /path/to/aFold21_github
ls -la
```

Replace the path with the actual extraction location. Review the files before publishing. Do not add private sequences, prediction output, OAuth configuration, credentials, or local machine-specific files.

## 3. Initialize and review the first commit

```bash
git init
git branch -M main
git add .
git status
```

Read the staged file list. If it looks correct, commit it:

```bash
git commit -m "Initial release of aFold21 terminal wrapper"
```

If Git asks you to configure your author identity, set your preferred name and email with `git config --global user.name` and `git config --global user.email`.

## 4. Create a new public repository and push

```bash
gh repo create aFold21 --public --source=. --remote=origin --push
```

This creates a new public repository under the currently authenticated GitHub account. If you want to use a different repository name, change `aFold21` consistently. If GitHub says the repository already exists, stop and inspect `git remote -v` before pushing; do not overwrite an existing repository blindly.

## 5. Verify

```bash
gh repo view --web
git status
git remote -v
```

Confirm the README renders, the citation links open, and no private files were published.

## Later updates

After making changes to an existing local repository:

```bash
git add .
git status
git commit -m "Describe the update"
git push
```
