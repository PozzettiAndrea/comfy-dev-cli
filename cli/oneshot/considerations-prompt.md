# Considerations for ComfyUI Wrapper Implementation

You are preparing implementation considerations for a ComfyUI custom node wrapper.

## Project: {project_name}

## Finalized Scope
{scope_content}

## Initial Assessment
{assessment_content}

## Project Technical Summary
{claude_md_content}

## Repository README
{repo_readme}

## Cookiecutter Template Structure
The following files from the cookiecutter template need to be filled:

{cookiecutter_template}

## Your Task

Generate comprehensive implementation considerations that will help fill the cookiecutter template. Cover:

### 1. Architecture

- **File structure**: How should nodes be organized? (single nodes.py vs nodes/ folder)
- **Model loading pattern**: Lazy loading? Separate loader node?
- **Memory management**: Any special considerations for GPU memory?
- **Error handling**: What can fail and how should we handle it?

### 2. Dependencies

- **Pure Python deps**: List pip packages needed
- **CUDA/compiled deps**: Any that need special installation?
- **Conflict risks**: Any known conflicts with common ComfyUI setups?
- **install.py requirements**: What should the install script handle?

### 3. Node Design

For each MVP node, specify:
- Input types (IMAGE, MASK, INT, FLOAT, STRING, custom types)
- Output types
- Key parameters with defaults
- Any UI considerations (widgets, hidden inputs)

### 4. Assets & Workflows

- **Example inputs**: What sample files should we include in assets/?
- **Demo workflows**: What workflow(s) best showcase the nodes?
- **Model files**: Where should users place downloaded models?

### 5. Testing Strategy

- What unit tests make sense?
- Any integration tests needed?
- How to test without full ComfyUI?

### 6. README Sections

What should be highlighted in the README:
- Installation gotchas
- Model download instructions
- Basic usage example
- Known limitations

## Output Format

Produce a structured markdown document with clear sections for each consideration area. This will be used by the `fill` command to populate the cookiecutter template.
