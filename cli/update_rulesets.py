#!/usr/bin/env python3
"""Script to update branch protection rulesets for ComfyUI repos."""

import os
import httpx
from config import GITHUB_OWNER

# Repos to ADD new rulesets to
REPOS_TO_ADD = [
    "ComfyUI-TRELLIS2",
    "ComfyUI-Sharp",
    "ComfyUI-MeshSegmenter",
    "ComfyUI-Multiband",
]

# Repos with EXISTING rulesets to update (remove bypass actors)
REPOS_TO_UPDATE = {
    "ComfyUI-SAM3": 10453678,
    "ComfyUI-UniRig": 10453653,
    "ComfyUI-DepthAnythingV3": 10453610,
    "ComfyUI-SAM3DBody": 10453713,
    "ComfyUI-MotionCapture": 10453956,
    "ComfyUI-SAM3DObjects": 10453828,
    "ComfyUI-GeometryPack": 10453697,
    "ComfyUI-Hunyuan3D-Part": 10453639,
    "ComfyUI-Grounding": 10454084,
    "ComfyUI-CADabra": 10453725,
    "ComfyUI-HunyuanX": 10454286,
}


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Part 1: Create new rulesets for unprotected repos
    print("=" * 60)
    print("PART 1: Creating new rulesets")
    print("=" * 60)

    new_ruleset_payload = {
        "name": "protect-main",
        "target": "branch",
        "enforcement": "active",
        "conditions": {
            "ref_name": {
                "include": ["~DEFAULT_BRANCH"],
                "exclude": []
            }
        },
        "rules": [
            {"type": "deletion"},
            {"type": "non_fast_forward"},
            {"type": "update"}
        ],
        "bypass_actors": []  # No bypass actors - no one can push directly
    }

    for repo in REPOS_TO_ADD:
        print(f"\nCreating ruleset for {repo}...")
        response = httpx.post(
            f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/rulesets",
            headers=headers,
            json=new_ruleset_payload,
            timeout=30,
        )
        if response.status_code == 201:
            data = response.json()
            print(f"  SUCCESS: Created ruleset ID {data.get('id')}")
        else:
            print(f"  FAILED: {response.status_code} - {response.text[:100]}")

    # Part 2: Update existing rulesets to remove bypass actors
    print("\n" + "=" * 60)
    print("PART 2: Removing bypass actors from existing rulesets")
    print("=" * 60)

    for repo, ruleset_id in REPOS_TO_UPDATE.items():
        print(f"\nUpdating {repo} (ruleset {ruleset_id})...")

        # First get the current ruleset to preserve other settings
        get_response = httpx.get(
            f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/rulesets/{ruleset_id}",
            headers=headers,
            timeout=30,
        )

        if get_response.status_code != 200:
            print(f"  FAILED to fetch: {get_response.status_code}")
            continue

        current = get_response.json()

        # Update with empty bypass_actors
        update_payload = {
            "name": current.get("name", "protect-main"),
            "target": current.get("target", "branch"),
            "enforcement": current.get("enforcement", "active"),
            "conditions": current.get("conditions", {}),
            "rules": current.get("rules", []),
            "bypass_actors": []  # Remove all bypass actors
        }

        put_response = httpx.put(
            f"https://api.github.com/repos/{GITHUB_OWNER}/{repo}/rulesets/{ruleset_id}",
            headers=headers,
            json=update_payload,
            timeout=30,
        )

        if put_response.status_code == 200:
            print(f"  SUCCESS: Removed bypass actors")
        else:
            print(f"  FAILED: {put_response.status_code} - {put_response.text[:100]}")

    print("\n" + "=" * 60)
    print("DONE! Run debug_branch_protection.py to verify changes.")
    print("=" * 60)


if __name__ == "__main__":
    main()
