# comfy-dev-cli

CLI tools for ComfyUI node development.

## Install

```bash
# Linux
curl -fsSL https://raw.githubusercontent.com/PozzettiAndrea/comfy-dev-cli/main/scripts/linux_setup.sh | bash
```

```powershell
# Windows
irm https://raw.githubusercontent.com/PozzettiAndrea/comfy-dev-cli/main/scripts/windows_setup.ps1 | iex
```

## Usage

```bash
cds --help           # Show all commands
cds get <config>     # Set up a ComfyUI environment
cds clone-utils      # Clone utility repos
cds start <env>      # Start ComfyUI
cds status           # Show repo status
```

## Structure

```
├── cli/           # Python CLI (cds command)
├── config/        # ComfyUI setup configs
│   └── setup/     # Environment configs (trellis2, sam3, unirig, etc.)
└── scripts/       # Setup scripts
```

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (installed by setup scripts)
- GitHub CLI (`gh`)
