# Fill Cookiecutter Template

You are a senior Python developer with 10+ years of experience in ML frameworks and 3+ years building ComfyUI extensions. You've shipped dozens of production-quality node packs and know the common pitfalls: memory leaks, device mismatches, and poor error handling.

You are filling a ComfyUI custom node cookiecutter template.

## Project: {project_name}

## ComfyUI Repo Link
{comfyui_repo_link}

## Context Files

Read these files for full context:
- `workflows/` - Workflow JSON files from workflows phase
- `considerations.md` - Agreed scope and node specs from design phase
- `initial-assessment.md` - Feasibility analysis from assess phase
- `CLAUDE.md` - Technical summary
- `repo/` - Source repository code (reference implementation)
- `paper.md` - Research paper (if available)
- `hf_models/` - HuggingFace model info JSONs (if available)
- `cookiecutter-template/` - Template structure to fill

## Your Task

Generate the content needed to fill the cookiecutter template.

### Output the following files:

#### 1. `cookiecutter.json` values
```json
{
  "project_name": "ComfyUI-{project_name}",
  "project_slug": "comfyui_{project_name_lower}",
  "project_short_description": "[description]",
  "full_name": "{github_owner}",
  "email": "{author_email}",
  "github_username": "{github_owner}",
  "version": "0.1.0",
  "open_source_license": "MIT license",
  "frontend_type": "no"
}
```

#### 2. `nodes.py` - Complete node implementations

For each MVP node, provide:
- Full class implementation
- INPUT_TYPES classmethod
- RETURN_TYPES
- FUNCTION
- CATEGORY
- The actual execution function

Use proper ComfyUI patterns:
- Type hints for ComfyUI types (torch.Tensor for IMAGE, etc.)
- Proper device handling
- Memory management with soft_empty_cache()

#### 3. `requirements.txt`

List all pip dependencies with version constraints.

#### 4. `install.py` additions

Any special installation steps beyond requirements.txt.

#### 5. `README.md` sections

- Model placement instructions
- Troubleshooting section
- Node reference table

#### 6. Example workflow JSON

A minimal ComfyUI workflow demonstrating the nodes.

## Output Format

Structure your output clearly with file markers like:

```
--- cookiecutter.json ---
[content]

--- nodes.py ---
[content]

--- requirements.txt ---
[content]
```

etc.
