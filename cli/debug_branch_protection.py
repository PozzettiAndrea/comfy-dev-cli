#!/usr/bin/env python3
"""Debug script to fetch branch protection rules and rulesets for ComfyUI repos."""

import os
import httpx
from github import Github
from config import get_all_repos, GITHUB_OWNER

def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN not set")
        return

    g = Github(token)
    # Filter to comfyui category only
    repos = [r for r in get_all_repos() if r.category == "comfyui"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    output_lines = []
    output_lines.append("=" * 100)
    output_lines.append("BRANCH PROTECTION RULES & RULESETS FOR COMFYUI REPOS")
    output_lines.append("=" * 100)
    output_lines.append(f"Total repos: {len(repos)}")
    output_lines.append("")

    for repo in repos:
        print(f"Fetching: {repo.name}...")
        gh_repo = g.get_repo(f"{GITHUB_OWNER}/{repo.name}")
        output_lines.append(f"\n{'='*80}")
        output_lines.append(f"REPO: {repo.name}")
        output_lines.append(f"{'='*80}")

        # Check traditional branch protection
        for branch_name in ["main", "dev"]:
            try:
                branch = gh_repo.get_branch(branch_name)
                output_lines.append(f"\n  Branch: {branch_name}")
                output_lines.append(f"    Protected: {branch.protected}")

                if branch.protected:
                    try:
                        protection = branch.get_protection()
                        output_lines.append(f"    Enforce admins: {protection.enforce_admins}")

                        if protection.required_pull_request_reviews:
                            pr_reviews = protection.required_pull_request_reviews
                            output_lines.append(f"    Required PR reviews: Yes")
                            output_lines.append(f"      - Required approving count: {pr_reviews.required_approving_review_count}")
                        else:
                            output_lines.append(f"    Required PR reviews: No")

                        if protection.required_status_checks:
                            output_lines.append(f"    Required status checks: Yes")
                        else:
                            output_lines.append(f"    Required status checks: No")
                    except Exception as e:
                        if "404" in str(e):
                            output_lines.append(f"    (Protected via Rulesets, not traditional branch protection)")
                        else:
                            output_lines.append(f"    Error fetching protection details: {str(e)[:60]}")

            except Exception as e:
                output_lines.append(f"\n  Branch: {branch_name}")
                output_lines.append(f"    Not found or error: {str(e)[:50]}")

        # Fetch Rulesets via REST API
        output_lines.append(f"\n  RULESETS:")
        try:
            response = httpx.get(
                f"https://api.github.com/repos/{GITHUB_OWNER}/{repo.name}/rulesets",
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                rulesets = response.json()
                if rulesets:
                    for ruleset in rulesets:
                        output_lines.append(f"\n    Ruleset: {ruleset.get('name', 'Unknown')}")
                        output_lines.append(f"      ID: {ruleset.get('id')}")
                        output_lines.append(f"      Enforcement: {ruleset.get('enforcement', 'Unknown')}")
                        output_lines.append(f"      Source: {ruleset.get('source_type', 'Unknown')} - {ruleset.get('source', 'Unknown')}")

                        # Fetch detailed ruleset info
                        detail_response = httpx.get(
                            f"https://api.github.com/repos/{GITHUB_OWNER}/{repo.name}/rulesets/{ruleset['id']}",
                            headers=headers,
                            timeout=30,
                        )

                        if detail_response.status_code == 200:
                            details = detail_response.json()

                            # Target branches
                            target = details.get('target', 'Unknown')
                            output_lines.append(f"      Target: {target}")

                            conditions = details.get('conditions', {})
                            if conditions:
                                ref_name = conditions.get('ref_name', {})
                                include = ref_name.get('include', [])
                                exclude = ref_name.get('exclude', [])
                                if include:
                                    output_lines.append(f"      Includes branches: {include}")
                                if exclude:
                                    output_lines.append(f"      Excludes branches: {exclude}")

                            # Rules
                            rules = details.get('rules', [])
                            if rules:
                                output_lines.append(f"      Rules:")
                                for rule in rules:
                                    rule_type = rule.get('type', 'Unknown')
                                    params = rule.get('parameters', {})
                                    if params:
                                        output_lines.append(f"        - {rule_type}: {params}")
                                    else:
                                        output_lines.append(f"        - {rule_type}")

                            # Bypass actors
                            bypass_actors = details.get('bypass_actors', [])
                            if bypass_actors:
                                output_lines.append(f"      Bypass actors:")
                                for actor in bypass_actors:
                                    actor_type = actor.get('actor_type', 'Unknown')
                                    actor_id = actor.get('actor_id', 'Unknown')
                                    bypass_mode = actor.get('bypass_mode', 'Unknown')
                                    output_lines.append(f"        - {actor_type} (id={actor_id}): {bypass_mode}")
                else:
                    output_lines.append(f"    No rulesets found")
            elif response.status_code == 404:
                output_lines.append(f"    No rulesets (404)")
            else:
                output_lines.append(f"    Error fetching rulesets: {response.status_code}")

        except Exception as e:
            output_lines.append(f"    Error fetching rulesets: {str(e)[:60]}")

    # Write to file
    with open("/home/shadeform/branchprotection.txt", "w") as f:
        f.write("\n".join(output_lines))

    print(f"\nWritten to /home/shadeform/branchprotection.txt")

if __name__ == "__main__":
    main()
