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
New-Item -ItemType SymbolicLink -Path ".\references\JARVISv2_ref" -Target "C:\Path\ToCopied\JARVISv2"
New-Item -ItemType SymbolicLink -Path ".\references\JARVISv3_ref" -Target "C:\Path\ToCopied\JARVISv3"
```

### 2. Direct Clone
Clone directly into this folder (aka `pushd <repo-root>\references`):
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
