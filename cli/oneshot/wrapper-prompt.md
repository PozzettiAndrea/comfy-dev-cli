REMIND ME TO ADD A SECTION ABOUT .GITHUB WORKFLOWS AND PYPROJECT.TOML

I want to create a ComfyUI custom node wrapper.

The original code is here: /home/shadeform/original_code/UltraShape-1.0
You should create the custom node within this folder: /home/shadeform/ultrashape/ComfyUI/custom_nodes/ComfyUI-UltraShape
For testing, use the conda environment named: ultrashape
You can find example nodes made by me before here:
- /home/shadeform/original_code/ComfyUI-DepthAnythingV3

## Requirements
Create a complete ComfyUI wrapper following these conventions:

### Repository Structure
```
ComfyUI-[WrapperName]/
├── __init__.py                 # Package entry with NODE_CLASS_MAPPINGS
├── prestartup_script.py        # Asset copier (runs before node load)
├── install.py                  # CUDA dependency installer (if needed, always install from wheel when possible! auto detect the pytorch/cuda versions)
├── requirements.txt            # Dependencies (definitely no model package, we vendor it, of course some dependencies will be needed)
├── assets/                     # Example files copied to ComfyUI/input/ on first load
│   └── placeholder.txt         # Keep empty until you add example assets
├── workflows/                  # Example workflows copied to ComfyUI/user/default/workflows/
│   └── placeholder.txt         # Keep empty until you add example workflows
├── nodes/
│   ├── __init__.py            # Aggregates all node mappings
│   ├── load_model.py          # Model (down)loader node
│   ├── inference.py           # Main inference node(s)
│   ├── utils.py               # Shared utilities
│   └── [model_name]/          # VENDORED MODEL CODE (copied from source repo)

### CRITICAL: Vendoring Pattern
**Always vendor the original model code, but edit when needed** - copy it into `nodes/[model_name]/` as a proper Python module:
- Every directory MUST have `__init__.py`
- Use ONLY relative imports: `from .model import Net` or `from ..utils import helper`
- NO sys.path hacks or absolute imports from vendored code
- Fix any absolute imports in the original code to be relative

Example vendoring structure:
```python
# nodes/depth_anything_v3/__init__.py
from .model import DepthAnythingNet
from .configs import MODEL_CONFIGS

# nodes/depth_anything_v3/model/__init__.py
from .backbone import DinoV2
from .head import DPT

# nodes/load_model.py - importing vendored code
from .depth_anything_v3 import DepthAnythingNet, MODEL_CONFIGS
```

### Node Implementation Patterns

1. **(down)Loader Node** (`DownloadAndLoad[ModelName]Model`):
   - Download checkpoint from HuggingFace to `ComfyUI/models/[package_name]/` or another appropriate folder within ComfyUI/models
   - Global `_MODEL_CACHE = {}` at module level to avoid reloading (offer option to keep model loaded on GPU OR NOT)
   - Device selection: auto/cuda/mps/cpu
   - Dtype selection: auto/bf16/fp16/fp32
   - DON'T offer dtype if it doesn't make sense. If models are offered in only bf16 dtype, then don't let users make stupid choices.

### install.py Pattern (for CUDA dependencies)
If the model needs CUDA-compiled packages (flash-attn, torch-scatter, spconv, nvdiffrast, etc.):

```python
"""Install script for ComfyUI-[WrapperName] dependencies."""
import subprocess
import sys

def get_torch_info():
    """Get PyTorch version and CUDA suffix."""
    import torch
    torch_version = torch.__version__.split("+")[0]
    if torch.cuda.is_available() and torch.version.cuda:
        cuda_suffix = "cu" + torch.version.cuda.replace(".", "")
    else:
        cuda_suffix = "cpu"
    return torch_version, cuda_suffix

def install_package():
    """Install CUDA-dependent package."""
    torch_version, cuda_suffix = get_torch_info()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    print(f"[PackageName] PyTorch {torch_version} with {cuda_suffix}, Python {python_version}")

    # Option 1: PyG wheel index (torch-scatter, torch-sparse, etc.)
    wheel_url = f"https://data.pyg.org/whl/torch-{torch_version}+{cuda_suffix}.html"
    cmd = [sys.executable, "-m", "pip", "install", "torch-scatter", "-f", wheel_url]

    # Option 2: Pre-built wheel URL dict
    WHEELS = {
        ("cu128", "2.8", "3.11"): "https://github.com/.../package.whl",
    }
    key = (cuda_suffix, torch_version[:3], python_version)
    if key in WHEELS:
        cmd = [sys.executable, "-m", "pip", "install", WHEELS[key]]

    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("[PackageName] Installed successfully")
    else:
        print("[PackageName] Installation failed")
        sys.exit(1)

if __name__ == "__main__":
    install_package()
```

Key patterns:
- Detect PyTorch version and CUDA version dynamically
- Use pre-built wheel URLs keyed by (cuda, torch, python) tuple
- Fall back to pip install or source compilation. BUT ALWAYS PREFER WHEEL.

### prestartup_script.py Pattern (for example assets)

Always create `assets/` and `workflows/` folders with a `placeholder.txt` file (empty). When you add example files, `prestartup_script.py` copies them to ComfyUI's input folders on first load:

```python
"""Prestartup script - copies example assets to ComfyUI input folders."""
import os
import shutil

def copy_assets():
    """Copy assets to appropriate ComfyUI input folders based on file type."""
    script_dir = os.path.dirname(__file__)
    assets_dir = os.path.join(script_dir, "assets")
    workflows_dir = os.path.join(script_dir, "workflows")

    try:
        import folder_paths
        input_folder = folder_paths.get_input_directory()
        comfyui_root = os.path.dirname(os.path.dirname(script_dir))
    except ImportError:
        comfyui_root = os.path.dirname(os.path.dirname(script_dir))
        input_folder = os.path.join(comfyui_root, "input")

    # Destinations
    DEST_3D = os.path.join(input_folder, "3d")
    DEST_IMAGES = input_folder
    DEST_WORKFLOWS = os.path.join(comfyui_root, "user", "default", "workflows")

    # File type mappings
    MESH_EXTENSIONS = {'.obj', '.glb', '.gltf', '.stl', '.ply', '.off', '.fbx'}
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}
    WORKFLOW_EXTENSIONS = {'.json'}

    os.makedirs(DEST_3D, exist_ok=True)
    os.makedirs(DEST_WORKFLOWS, exist_ok=True)

    copied = 0

    # Copy assets (images → input/, meshes → input/3d/)
    if os.path.exists(assets_dir):
        for root, dirs, files in os.walk(assets_dir):
            rel_path = os.path.relpath(root, assets_dir)
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()

                if ext in MESH_EXTENSIONS:
                    dest_base = DEST_3D
                elif ext in IMAGE_EXTENSIONS:
                    dest_base = DEST_IMAGES
                else:
                    continue

                dest_folder = os.path.join(dest_base, rel_path) if rel_path != '.' else dest_base
                os.makedirs(dest_folder, exist_ok=True)

                src = os.path.join(root, filename)
                dst = os.path.join(dest_folder, filename)

                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    copied += 1
                    print(f"[PackageName] Copied {filename} → {os.path.basename(dest_base)}/")

    # Copy workflows (→ user/default/workflows/)
    if os.path.exists(workflows_dir):
        for filename in os.listdir(workflows_dir):
            ext = os.path.splitext(filename)[1].lower()
            if ext in WORKFLOW_EXTENSIONS:
                src = os.path.join(workflows_dir, filename)
                dst = os.path.join(DEST_WORKFLOWS, filename)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    copied += 1
                    print(f"[PackageName] Copied workflow {filename}")

    if copied:
        print(f"[PackageName] Copied {copied} example assets/workflows")

copy_assets()
```

Key points:
- **Always create `assets/` and `workflows/` folders** with `placeholder.txt` (empty file)
- Use `folder_paths.get_input_directory()` (preferred) with fallback
- Route 3D files (.obj, .glb, .stl, .ply, .off, .fbx) → `input/3d/`
- Route images (.png, .jpg, .jpeg, .webp, .bmp) → `input/`
- Route workflows (.json) → `user/default/workflows/`
- Preserve subfolder structure
- Skip if destination exists (non-destructive)
- Print with `[PackageName]` prefix for logs

### Code Conventions
- Image format: ComfyUI uses `[B, H, W, C]` float tensors in `[0, 1]` range
- Use `comfy.model_management` for device management when available
- Use `folder_paths` for ComfyUI directory paths
- Log format: `print(f"[{PackageName}] message")`

### Node Class Template
```python
class NodeClassName:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "input_name": ("TYPE", {"default": value, "tooltip": "Description"}),
            },
            "optional": {}
        }

    RETURN_TYPES = ("OUTPUT_TYPE",)
    RETURN_NAMES = ("output_name",)
    OUTPUT_TOOLTIPS = ("Description",)
    FUNCTION = "method_name"
    CATEGORY = "PackageName"
    DESCRIPTION = "What this node does."

    def method_name(self, input_name):
        # Implementation
        return (output,)
```

### __init__.py Aggregation Pattern
```python
# nodes/__init__.py
from .load_model import NODE_CLASS_MAPPINGS as LOADER_MAPPINGS
from .load_model import NODE_DISPLAY_NAME_MAPPINGS as LOADER_DISPLAY
from .inference import NODE_CLASS_MAPPINGS as INFERENCE_MAPPINGS
from .inference import NODE_DISPLAY_NAME_MAPPINGS as INFERENCE_DISPLAY

NODE_CLASS_MAPPINGS = {**LOADER_MAPPINGS, **INFERENCE_MAPPINGS}
NODE_DISPLAY_NAME_MAPPINGS = {**LOADER_DISPLAY, **INFERENCE_DISPLAY}
```

```python
# Root __init__.py
from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

Do one round of searching to estimate node implementation difficulty. Are there any dependencies that require CUDA compilation? Is code very non standard?

Then get b ack to me and report your findings. Then ask me questions that bdtter help you understand how to implemnent the node. then go ahead.

The 3D input/outputs should be handled as trimesh objects, compatible with /home/shadeform/original_code/ComfyUI-GeometryPack
Let me know if you cannot find GeometryPack code.

Also, I want several nodes, at least one for model loading and one for inference. Possibily more.
Another priority is giving users the opportunity to offload models (or model parts) after they are done so that they can run on the smallest VRAMs.