# PR Management Scripts

This directory contains automation scripts for managing pull requests in the repository.

## manage_prs.py

A Python script that automatically manages open pull requests by:

1. **Fetching open PRs** - Retrieves all open pull requests in the repository
2. **Identifying target branch** - Determines the most up-to-date target branch (typically `main` or `master`)
3. **Attempting merges** - For each PR:
   - If merge succeeds with no conflicts:
     - Completes the merge
     - Deletes the source branch immediately after merge
   - If merge conflicts exist:
     - Does NOT merge
     - Creates a new branch named `conflicts/{original-branch-name}`
     - Pushes the conflicting branch state there
     - Adds a comment to the PR listing the conflicting files
     - Leaves the original PR open

### Requirements

- Python 3.8+
- `requests` library (install with `pip install requests`)
- GitHub personal access token with appropriate permissions:
  - `repo` (Full control of private repositories)
  - `write:discussion` (Read/write discussions)

### Usage

```bash
# Using command line argument
python scripts/manage_prs.py --repo owner/repo --token YOUR_GITHUB_TOKEN

# Using environment variable
export GITHUB_TOKEN=YOUR_GITHUB_TOKEN
python scripts/manage_prs.py --repo owner/repo
```

**Example:**

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
python scripts/manage_prs.py --repo sburdges-eng/penta-core
```

### Creating a GitHub Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a descriptive name (e.g., "PR Management Script")
4. Select scopes:
   - `repo` (Full control of private repositories)
   - `write:discussion` (for commenting on PRs)
5. Click "Generate token"
6. Copy the token immediately (you won't be able to see it again!)

### Output

The script provides detailed output showing:
- Each PR being processed
- Merge status and results
- Branch operations (merges, deletions, conflicts branch creation)
- Final summary with:
  - Successfully merged and deleted PRs
  - PRs moved to conflicts branches with details

### Safety Features

- **Never force pushes** - All operations use standard Git workflows
- **Never resolves conflicts automatically** - Conflicts are preserved for human review
- **Creates conflicts branches** - Preserves the conflicting state for investigation
- **Leaves PRs open** - Conflicting PRs remain open for manual resolution

### Error Handling

The script handles various error conditions:
- Network failures
- API rate limits
- Permission issues
- Invalid branches
- Already merged PRs

All errors are logged with descriptive messages.

### Example Output

```
PR Management Agent for sburdges-eng/penta-core
================================================================================

Fetching open pull requests...
Found 2 open PR(s)

Default branch: main

================================================================================
Processing PR #123: Add new feature
  Branch: feature/new-feature -> main
  Mergeable: True, State: clean
  Attempting to merge...
  ✓ Successfully merged PR #123
  Deleting branch feature/new-feature...
  ✓ Successfully deleted branch feature/new-feature

================================================================================
Processing PR #124: Update documentation
  Branch: docs/update -> main
  Mergeable: False, State: dirty
  ✗ PR has conflicts or is not mergeable
  Creating conflicts branch...
  ✓ Created branch: conflicts/docs/update
  Adding comment to PR...
  ✓ Comment added to PR #124

================================================================================
SUMMARY
================================================================================

Successfully merged and deleted:
  - PR #123: Add new feature
    Branch: feature/new-feature

Moved to conflicts branch:
  - PR #124: Update documentation
    Original branch: docs/update
    Conflicts branch: conflicts/docs/update
```

### Troubleshooting

**"Error: GitHub token required"**
- Make sure you've provided a token via `--token` or `GITHUB_TOKEN` environment variable

**"Failed to merge PR"**
- Check that the PR is in a mergeable state
- Verify your token has the necessary permissions
- Ensure the PR doesn't have required status checks that haven't passed

**"Failed to delete branch"**
- The branch might be protected
- Check repository settings for branch protection rules

**"Failed to create conflicts branch"**
- A branch with the same name might already exist
- Verify your token has write permissions to the repository
