#!/usr/bin/env python3
"""
PR Management Agent

This script manages open pull requests by:
1. Fetching open PRs
2. Attempting to merge each PR into its target branch
3. If merge succeeds: complete merge and delete source branch
4. If conflicts exist: create conflicts/{branch-name} branch and comment on PR

Usage:
    python scripts/manage_prs.py --repo owner/repo --token YOUR_GITHUB_TOKEN

Environment Variables:
    GITHUB_TOKEN: GitHub personal access token (alternative to --token)
"""

import argparse
import os
import subprocess
import sys
from typing import List, Dict, Optional, Tuple
import requests


class PRManager:
    def __init__(self, owner: str, repo: str, token: str):
        self.owner = owner
        self.repo = repo
        self.token = token
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self.successfully_merged = []
        self.moved_to_conflicts = []

    def _api_get(self, endpoint: str) -> requests.Response:
        """Make GET request to GitHub API."""
        url = f"{self.api_base}{endpoint}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response

    def _api_post(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Make POST request to GitHub API."""
        url = f"{self.api_base}{endpoint}"
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response

    def _api_delete(self, endpoint: str) -> requests.Response:
        """Make DELETE request to GitHub API."""
        url = f"{self.api_base}{endpoint}"
        response = requests.delete(url, headers=self.headers)
        response.raise_for_status()
        return response

    def _api_put(self, endpoint: str, data: Optional[Dict] = None) -> requests.Response:
        """Make PUT request to GitHub API."""
        url = f"{self.api_base}{endpoint}"
        response = requests.put(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response

    def get_open_prs(self) -> List[Dict]:
        """Get all open pull requests."""
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls"
        response = self._api_get(endpoint)
        return response.json()

    def get_default_branch(self) -> str:
        """Get the default branch of the repository."""
        endpoint = f"/repos/{self.owner}/{self.repo}"
        response = self._api_get(endpoint)
        return response.json()["default_branch"]

    def check_merge_status(self, pr_number: int) -> Tuple[bool, Optional[str]]:
        """
        Check if PR can be merged without conflicts.
        Returns: (can_merge, merge_status)
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
        response = self._api_get(endpoint)
        pr_data = response.json()
        
        mergeable = pr_data.get("mergeable")
        mergeable_state = pr_data.get("mergeable_state")
        
        return mergeable, mergeable_state

    def get_conflicting_files(self, base_branch: str, head_branch: str) -> List[str]:
        """
        Identify conflicting files by attempting a local merge check.
        Returns list of conflicting file paths.
        """
        try:
            # Validate branch names to prevent command injection
            # Branch names should only contain alphanumeric, -, _, /, and .
            import re
            branch_pattern = re.compile(r'^[a-zA-Z0-9/_.-]+$')
            if not branch_pattern.match(base_branch) or not branch_pattern.match(head_branch):
                print(f"Warning: Invalid branch name format")
                return []
            
            # Get merge base
            merge_base_result = subprocess.run(
                ["git", "merge-base", f"origin/{base_branch}", f"origin/{head_branch}"],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            if merge_base_result.returncode != 0:
                return []
            
            merge_base = merge_base_result.stdout.strip()
            
            # Try merge-tree to detect conflicts
            result = subprocess.run(
                ["git", "merge-tree", merge_base, f"origin/{base_branch}", f"origin/{head_branch}"],
                capture_output=True,
                text=True,
                cwd=os.getcwd()
            )
            
            # Parse merge-tree output for conflicts
            conflicts = []
            if result.returncode == 0 and result.stdout:
                # Look for conflict markers in merge-tree output
                for line in result.stdout.split('\n'):
                    if line.startswith('changed in both'):
                        # Extract filename
                        parts = line.split()
                        if len(parts) > 3:
                            conflicts.append(parts[3])
            
            return conflicts
        except Exception as e:
            print(f"Warning: Could not determine conflicting files: {e}")
            return []

    def merge_pr(self, pr_number: int, commit_message: Optional[str] = None) -> bool:
        """
        Merge a pull request.
        Returns True if successful, False otherwise.
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/pulls/{pr_number}/merge"
        data = {
            "merge_method": "merge"
        }
        if commit_message:
            data["commit_message"] = commit_message
        
        try:
            self._api_put(endpoint, data)
            return True
        except requests.exceptions.HTTPError as e:
            print(f"Failed to merge PR #{pr_number}: {e}")
            return False

    def delete_branch(self, branch_name: str) -> bool:
        """
        Delete a branch.
        Returns True if successful, False otherwise.
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/git/refs/heads/{branch_name}"
        try:
            self._api_delete(endpoint)
            return True
        except requests.exceptions.HTTPError as e:
            print(f"Failed to delete branch {branch_name}: {e}")
            return False

    def create_conflicts_branch(self, source_branch: str, base_branch: str) -> Optional[str]:
        """
        Create a conflicts/{source_branch} branch from the current state.
        Returns the new branch name if successful, None otherwise.
        """
        conflicts_branch_name = f"conflicts/{source_branch}"
        
        try:
            # Get the SHA of the source branch
            endpoint = f"/repos/{self.owner}/{self.repo}/git/ref/heads/{source_branch}"
            response = self._api_get(endpoint)
            source_sha = response.json()["object"]["sha"]
            
            # Create the new branch
            endpoint = f"/repos/{self.owner}/{self.repo}/git/refs"
            data = {
                "ref": f"refs/heads/{conflicts_branch_name}",
                "sha": source_sha
            }
            self._api_post(endpoint, data)
            return conflicts_branch_name
        except requests.exceptions.HTTPError as e:
            print(f"Failed to create conflicts branch for {source_branch}: {e}")
            return None

    def comment_on_pr(self, pr_number: int, comment: str) -> bool:
        """
        Add a comment to a pull request.
        Returns True if successful, False otherwise.
        """
        endpoint = f"/repos/{self.owner}/{self.repo}/issues/{pr_number}/comments"
        data = {"body": comment}
        
        try:
            self._api_post(endpoint, data)
            return True
        except requests.exceptions.HTTPError as e:
            print(f"Failed to comment on PR #{pr_number}: {e}")
            return False

    def process_pr(self, pr: Dict) -> None:
        """Process a single pull request."""
        pr_number = pr["number"]
        pr_title = pr["title"]
        head_branch = pr["head"]["ref"]
        base_branch = pr["base"]["ref"]
        
        print(f"\n{'='*80}")
        print(f"Processing PR #{pr_number}: {pr_title}")
        print(f"  Branch: {head_branch} -> {base_branch}")
        
        # Check merge status
        can_merge, merge_state = self.check_merge_status(pr_number)
        
        print(f"  Mergeable: {can_merge}, State: {merge_state}")
        
        if can_merge:
            # Attempt to merge
            print(f"  Attempting to merge...")
            if self.merge_pr(pr_number):
                print(f"  ✓ Successfully merged PR #{pr_number}")
                
                # Delete the source branch
                print(f"  Deleting branch {head_branch}...")
                if self.delete_branch(head_branch):
                    print(f"  ✓ Successfully deleted branch {head_branch}")
                    self.successfully_merged.append({
                        "pr_number": pr_number,
                        "title": pr_title,
                        "branch": head_branch
                    })
                else:
                    print(f"  ✗ Failed to delete branch {head_branch}")
                    self.successfully_merged.append({
                        "pr_number": pr_number,
                        "title": pr_title,
                        "branch": head_branch,
                        "note": "Merged but branch deletion failed"
                    })
            else:
                print(f"  ✗ Failed to merge PR #{pr_number}")
                self._handle_merge_conflict(pr, head_branch, base_branch)
        else:
            # Handle conflicts
            print(f"  ✗ PR has conflicts or is not mergeable")
            self._handle_merge_conflict(pr, head_branch, base_branch)

    def _handle_merge_conflict(self, pr: Dict, head_branch: str, base_branch: str) -> None:
        """Handle a PR that has merge conflicts."""
        pr_number = pr["number"]
        pr_title = pr["title"]
        
        # Create conflicts branch
        print(f"  Creating conflicts branch...")
        conflicts_branch = self.create_conflicts_branch(head_branch, base_branch)
        
        if conflicts_branch:
            print(f"  ✓ Created branch: {conflicts_branch}")
            
            # Try to get conflicting files
            conflicting_files = self.get_conflicting_files(base_branch, head_branch)
            
            # Prepare comment
            if conflicting_files:
                files_list = "\n".join([f"- `{f}`" for f in conflicting_files])
                comment = f"""## Merge Conflicts Detected

This PR has merge conflicts with `{base_branch}`.

**Conflicting files:**
{files_list}

A conflicts branch has been created: `{conflicts_branch}`

Please resolve the conflicts and update this PR."""
            else:
                comment = f"""## Merge Conflicts Detected

This PR cannot be automatically merged into `{base_branch}`.

A conflicts branch has been created: `{conflicts_branch}`

Please resolve the conflicts and update this PR."""
            
            # Add comment to PR
            print(f"  Adding comment to PR...")
            if self.comment_on_pr(pr_number, comment):
                print(f"  ✓ Comment added to PR #{pr_number}")
            else:
                print(f"  ✗ Failed to add comment to PR #{pr_number}")
            
            self.moved_to_conflicts.append({
                "pr_number": pr_number,
                "title": pr_title,
                "branch": head_branch,
                "conflicts_branch": conflicts_branch,
                "conflicting_files": conflicting_files
            })
        else:
            print(f"  ✗ Failed to create conflicts branch")
            self.moved_to_conflicts.append({
                "pr_number": pr_number,
                "title": pr_title,
                "branch": head_branch,
                "conflicts_branch": None,
                "note": "Failed to create conflicts branch"
            })

    def run(self) -> None:
        """Main execution: process all open PRs."""
        print(f"PR Management Agent for {self.owner}/{self.repo}")
        print(f"{'='*80}\n")
        
        # Get open PRs
        print("Fetching open pull requests...")
        prs = self.get_open_prs()
        
        if not prs:
            print("No open pull requests found.")
            return
        
        print(f"Found {len(prs)} open PR(s)\n")
        
        # Get default branch
        default_branch = self.get_default_branch()
        print(f"Default branch: {default_branch}\n")
        
        # Process each PR
        for pr in prs:
            self.process_pr(pr)
        
        # Print summary
        self.print_summary()

    def print_summary(self) -> None:
        """Print summary of actions taken."""
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}\n")
        
        if self.successfully_merged:
            print("Successfully merged and deleted:")
            for item in self.successfully_merged:
                note = f" ({item['note']})" if 'note' in item else ""
                print(f"  - PR #{item['pr_number']}: {item['title']}")
                print(f"    Branch: {item['branch']}{note}")
        else:
            print("Successfully merged and deleted: None")
        
        print()
        
        if self.moved_to_conflicts:
            print("Moved to conflicts branch:")
            for item in self.moved_to_conflicts:
                print(f"  - PR #{item['pr_number']}: {item['title']}")
                print(f"    Original branch: {item['branch']}")
                if item.get('conflicts_branch'):
                    print(f"    Conflicts branch: {item['conflicts_branch']}")
                    if item.get('conflicting_files'):
                        print(f"    Conflicting files: {', '.join(item['conflicting_files'])}")
                if 'note' in item:
                    print(f"    Note: {item['note']}")
        else:
            print("Moved to conflicts branch: None")


def main():
    parser = argparse.ArgumentParser(
        description="Manage open pull requests: merge clean PRs, handle conflicts"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository in format owner/repo (e.g., sburdges-eng/penta-core)"
    )
    parser.add_argument(
        "--token",
        help="GitHub personal access token (or set GITHUB_TOKEN env var)"
    )
    
    args = parser.parse_args()
    
    # Get token
    token = args.token or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Error: GitHub token required. Use --token or set GITHUB_TOKEN env var.")
        sys.exit(1)
    
    # Parse repo
    if "/" not in args.repo:
        print("Error: Repository must be in format owner/repo")
        sys.exit(1)
    
    owner, repo = args.repo.split("/", 1)
    
    # Run manager
    manager = PRManager(owner, repo, token)
    try:
        manager.run()
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
