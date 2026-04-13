# TFE LaTeX Project

This repository contains the LaTeX source for a UNIR TFE document. The project is configured to be edited in VS Code and built with `latexmk`, with generated files written to `build/`.

## Repository structure

- `main.tex`: main LaTeX entrypoint
- `styles/estilo_unir-1.sty`: shared style definitions
- `references/bibliografia.bib`: bibliography database
- `assets/logo_unir.pdf`: UNIR logo used by the cover page
- `.vscode/settings.json`: shared VS Code build and formatting settings
- `build/`: generated output directory

## Working environment

The repository is set up for this toolchain:

1. Visual Studio Code
2. VS Code extension `James-Yu.latex-workshop`
3. MiKTeX
4. Perl
5. `latexmk`
6. `latexindent`

`latexmk` is the build runner configured in `.vscode/settings.json`. It compiles `main.tex` and writes output to `build/`. `latexindent` is used as the LaTeX formatter in VS Code and also requires Perl on Windows.

## Setup

### 1. Clone the repository and open it in VS Code

```powershell
git clone <repository-url>
cd <repository-folder>
code .
```

If `code` is not available in PowerShell, open the folder manually from VS Code.

### 2. Install the required VS Code extension

Install:

```text
James-Yu.latex-workshop
```

### 3. Install MiKTeX

On Windows:

1. Download MiKTeX from `https://miktex.org/download`
2. Install it for the current user unless your machine requires a system-wide installation
3. Open MiKTeX Console after installation
4. Enable automatic package installation
5. Apply pending updates

MiKTeX provides the LaTeX executables used by this project, including `pdflatex`. It can also install missing packages the first time the document is built.

### 4. Install Perl

Perl is required because both `latexmk` and `latexindent` depend on it in this setup.

Recommended on Windows:

1. Download Strawberry Perl from `https://strawberryperl.com/`
2. Install the current 64-bit release
3. Restart VS Code after installation so the updated `PATH` is picked up

### 5. Verify the toolchain

Open a new terminal in the repository root and run:

```powershell
pdflatex --version
latexmk -v
latexindent -v
perl -v
```

The environment is ready when all four commands return version information without errors.

## First build

### Build from VS Code

1. Open [main.tex](/c:/Users/oolog/Desktop/UNIR/TFE/main.tex)
2. Run `LaTeX Workshop: Build LaTeX project`
3. Confirm that `build/main.pdf` is created
4. Confirm that VS Code opens the PDF preview in a tab

The repository already includes shared VS Code settings for:

- format on save for LaTeX files
- `latexindent` as the formatter
- `latexmk` as the default build recipe
- `build/` as the output directory
- PDF preview inside a VS Code tab

### Build from the terminal

Run this from the repository root:

```powershell
latexmk -synctex=1 -interaction=nonstopmode -file-line-error -pdf -outdir=build main.tex
```

## Daily workflow

- Edit `main.tex` for document content
- Add bibliography entries to `references/bibliografia.bib`
- Keep reusable style changes in `styles/estilo_unir-1.sty`
- Keep static files such as logos in `assets/`
- Do not edit files inside `build/`

## Git behavior

- Source files are tracked
- `assets/logo_unir.pdf` is tracked because the document needs it to render
- `.vscode/settings.json` is tracked because it contains shared project settings
- Generated LaTeX files should not be committed
- Other `.vscode` files are ignored because they are usually user-specific

## Troubleshooting

### `latexmk` or `latexindent` does not run

Check that Perl is installed and available on `PATH`:

```powershell
perl -v
```

If that fails, reinstall Strawberry Perl and restart VS Code.

### `pdflatex` works in the terminal but VS Code does not build

1. Restart VS Code
2. Run `Developer: Reload Window`
3. Run `LaTeX Workshop: Build LaTeX project` again
4. Check that VS Code was opened after MiKTeX and Perl were installed

### MiKTeX reports missing packages

Open MiKTeX Console and:

1. enable automatic package installation
2. install pending updates
3. rebuild the project

### Files such as `.aux`, `.log`, or `.pdf` appear in the repository root

The intended output directory is `build/`. Root-level generated files are leftover artifacts from older builds and can be removed safely.
