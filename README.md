# TFE LaTeX Project

This repository contains the LaTeX source for a UNIR research project template.

## Repository structure

- `main.tex`: main LaTeX entrypoint
- `styles/estilo_unir-1.sty`: shared style definitions
- `references/bibliografia.bib`: bibliography database
- `assets/logo_unir.pdf`: UNIR logo required by the cover page
- `.vscode/settings.json`: shared VS Code configuration for formatting and building
- `build/`: generated LaTeX output directory

## What is tracked in git

- Source files are tracked.
- `assets/logo_unir.pdf` is tracked because the document needs it to render.
- `.vscode/settings.json` is tracked because it contains shared project settings.
- Generated LaTeX files are written to `build/` and should not be committed.
- Other `.vscode` files are ignored because they are usually user-specific.

## Required tools

This repository is configured for:

1. Visual Studio Code
2. `LaTeX Workshop` for VS Code
3. MiKTeX
4. Perl
5. `latexmk`

On this project, `latexmk` is the build runner and writes output into `build/`.

## Installation and setup

### 1. Clone and open the repository

```powershell
git clone <repository-url>
cd <repository-folder>
code .
```

### 2. Install VS Code extension

Install the following extension in VS Code:

```text
James-Yu.latex-workshop
```

### 3. Install MiKTeX

On Windows:

1. Download MiKTeX from `https://miktex.org/download`
2. Install it for the current user unless your environment requires a machine-wide install
3. Open MiKTeX Console after installation
4. Enable automatic package installation
5. Apply updates if MiKTeX reports pending updates

### 4. Install Perl

This repository uses `latexmk`, so Perl must be available on `PATH`.

Recommended on Windows:

1. Download Strawberry Perl from `https://strawberryperl.com/`
2. Install the current 64-bit release
3. Restart VS Code after installation

### 5. Verify the toolchain

Open a new terminal in the repository root and run:

```powershell
pdflatex --version
latexmk -v
perl -v
```

If all three commands work, the environment is ready.

## First build in VS Code

1. Open [main.tex](c:/Users/oolog/Desktop/UNIR/TFE/main.tex#L1)
2. Run `LaTeX Workshop: Build LaTeX project`
3. The PDF should be generated in `build/main.pdf`
4. LaTeX Workshop should open the PDF preview in a VS Code tab

This repository already includes workspace settings for:

- LaTeX formatting through `latexindent`
- format on save for LaTeX files
- `latexmk` builds
- output written to `build/`

## Manual build

If you want to compile outside VS Code:

```powershell
latexmk -synctex=1 -interaction=nonstopmode -file-line-error -pdf -outdir=build main.tex
```

## Daily workflow

- Edit `main.tex` for document content
- Add bibliography entries to `references/bibliografia.bib`
- Keep reusable style changes in `styles/estilo_unir-1.sty`
- Keep static files such as logos in `assets/`
- Do not edit files inside `build/`

## Troubleshooting

### `latexmk` does not run

Check that Perl is installed:

```powershell
perl -v
```

If that fails, reinstall Strawberry Perl and restart VS Code.

### `pdflatex` works but VS Code does not build

1. Restart VS Code
2. Run `Developer: Reload Window`
3. Run `LaTeX Workshop: Build LaTeX project`

### MiKTeX reports missing packages

Open MiKTeX Console and:

1. enable automatic package installation
2. install pending updates
3. rebuild the project

### The repository root looks cluttered

The intended generated output location is `build/`. If root-level `.aux`, `.log`, `.pdf`, or similar files exist, they are leftover artifacts from older builds and can be cleaned safely.
