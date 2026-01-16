# Reference Setup

This directory contains read-only references to previous JARVIS versions.

## Targets
*   `<repo-root>/reference/JARVISv2_ref`
*   `<repo-root>/reference/JARVISv3_ref`

## Setup Methods

### 1. Symbolic Links (Recommended)
Link to existing local copies:

```powershell
# Windows (PowerShell Admin)
# From <repo-root>\
New-Item -ItemType SymbolicLink -Path ".\reference\JARVISv2_ref" -Target "C:\Path\To\JARVISv2"
New-Item -ItemType SymbolicLink -Path ".\reference\JARVISv3_ref" -Target "C:\Path\To\JARVISv3"
```

```bash
# Linux / macOS
# From <repo-root>/
ln -s /path/to/JARVISv2 ./reference/JARVISv2_ref
ln -s /path/to/JARVISv3 ./reference/JARVISv3_ref
```

### 2. Direct Clone
Clone directly into this folder (aka `cd <repo-root>/reference`):
```bash
git clone 'https://github.com/bentman/JARVISv2.git'
git clone 'https://github.com/bentman/JARVISv3.git'
```

## Read-Only Policy
**Do not edit files in these directories.** They are for reference only.
Ensure `<repo-root>\.vscode/settings.json` enforces this:
```json
"files.readonlyInclude": { "reference/**": true }
```
