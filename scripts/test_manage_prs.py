#!/usr/bin/env python3
"""
Unit tests for the PR Management script.

Run with: python -m pytest scripts/test_manage_prs.py
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from manage_prs import PRManager


class TestPRManager(unittest.TestCase):
    """Test cases for PRManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.manager = PRManager("test-owner", "test-repo", "test-token")

    def test_init(self):
        """Test PRManager initialization."""
        self.assertEqual(self.manager.owner, "test-owner")
        self.assertEqual(self.manager.repo, "test-repo")
        self.assertEqual(self.manager.token, "test-token")
        self.assertEqual(self.manager.successfully_merged, [])
        self.assertEqual(self.manager.moved_to_conflicts, [])

    @patch('manage_prs.requests.get')
    def test_get_open_prs(self, mock_get):
        """Test getting open pull requests."""
        mock_response = Mock()
        mock_response.json.return_value = [
            {"number": 1, "title": "Test PR 1"},
            {"number": 2, "title": "Test PR 2"}
        ]
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        prs = self.manager.get_open_prs()

        self.assertEqual(len(prs), 2)
        self.assertEqual(prs[0]["number"], 1)
        self.assertEqual(prs[1]["title"], "Test PR 2")
        mock_get.assert_called_once()

    @patch('manage_prs.requests.get')
    def test_get_default_branch(self, mock_get):
        """Test getting default branch."""
        mock_response = Mock()
        mock_response.json.return_value = {"default_branch": "main"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        branch = self.manager.get_default_branch()

        self.assertEqual(branch, "main")

    @patch('manage_prs.requests.get')
    def test_check_merge_status_clean(self, mock_get):
        """Test checking merge status for a clean PR."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "mergeable": True,
            "mergeable_state": "clean"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        can_merge, state = self.manager.check_merge_status(1)

        self.assertTrue(can_merge)
        self.assertEqual(state, "clean")

    @patch('manage_prs.requests.get')
    def test_check_merge_status_conflicted(self, mock_get):
        """Test checking merge status for a conflicted PR."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "mergeable": False,
            "mergeable_state": "dirty"
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        can_merge, state = self.manager.check_merge_status(1)

        self.assertFalse(can_merge)
        self.assertEqual(state, "dirty")

    @patch('manage_prs.requests.put')
    def test_merge_pr_success(self, mock_put):
        """Test successful PR merge."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response

        result = self.manager.merge_pr(1)

        self.assertTrue(result)
        mock_put.assert_called_once()

    @patch('manage_prs.requests.put')
    def test_merge_pr_failure(self, mock_put):
        """Test failed PR merge."""
        import requests
        mock_put.side_effect = requests.exceptions.HTTPError("Merge conflict")

        result = self.manager.merge_pr(1)

        self.assertFalse(result)

    @patch('manage_prs.requests.delete')
    def test_delete_branch_success(self, mock_delete):
        """Test successful branch deletion."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response

        result = self.manager.delete_branch("test-branch")

        self.assertTrue(result)

    @patch('manage_prs.requests.delete')
    def test_delete_branch_failure(self, mock_delete):
        """Test failed branch deletion."""
        import requests
        mock_delete.side_effect = requests.exceptions.HTTPError("Branch protected")

        result = self.manager.delete_branch("test-branch")

        self.assertFalse(result)

    @patch('manage_prs.requests.post')
    @patch('manage_prs.requests.get')
    def test_create_conflicts_branch(self, mock_get, mock_post):
        """Test creating a conflicts branch."""
        # Mock getting source branch SHA
        mock_get_response = Mock()
        mock_get_response.json.return_value = {
            "object": {"sha": "abc123"}
        }
        mock_get_response.raise_for_status = Mock()
        mock_get.return_value = mock_get_response

        # Mock creating branch
        mock_post_response = Mock()
        mock_post_response.raise_for_status = Mock()
        mock_post.return_value = mock_post_response

        result = self.manager.create_conflicts_branch("feature-branch", "main")

        self.assertEqual(result, "conflicts/feature-branch")
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @patch('manage_prs.requests.post')
    def test_comment_on_pr(self, mock_post):
        """Test adding a comment to PR."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = self.manager.comment_on_pr(1, "Test comment")

        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch.object(PRManager, 'check_merge_status')
    @patch.object(PRManager, 'merge_pr')
    @patch.object(PRManager, 'delete_branch')
    def test_process_pr_successful_merge(self, mock_delete, mock_merge, mock_check):
        """Test processing a PR that can be merged successfully."""
        mock_check.return_value = (True, "clean")
        mock_merge.return_value = True
        mock_delete.return_value = True

        pr = {
            "number": 1,
            "title": "Test PR",
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"}
        }

        self.manager.process_pr(pr)

        self.assertEqual(len(self.manager.successfully_merged), 1)
        self.assertEqual(self.manager.successfully_merged[0]["pr_number"], 1)
        self.assertEqual(len(self.manager.moved_to_conflicts), 0)

    @patch.object(PRManager, 'check_merge_status')
    @patch.object(PRManager, '_handle_merge_conflict')
    def test_process_pr_with_conflicts(self, mock_handle_conflict, mock_check):
        """Test processing a PR that has conflicts."""
        mock_check.return_value = (False, "dirty")

        pr = {
            "number": 1,
            "title": "Test PR",
            "head": {"ref": "feature-branch"},
            "base": {"ref": "main"}
        }

        self.manager.process_pr(pr)

        mock_handle_conflict.assert_called_once()

    def test_print_summary_empty(self):
        """Test printing summary with no actions."""
        # Should not raise any exceptions
        self.manager.print_summary()

    def test_print_summary_with_data(self):
        """Test printing summary with data."""
        self.manager.successfully_merged = [{
            "pr_number": 1,
            "title": "Test PR",
            "branch": "feature-branch"
        }]
        self.manager.moved_to_conflicts = [{
            "pr_number": 2,
            "title": "Conflicted PR",
            "branch": "conflict-branch",
            "conflicts_branch": "conflicts/conflict-branch"
        }]

        # Should not raise any exceptions
        self.manager.print_summary()


class TestCommandLineArgs(unittest.TestCase):
    """Test command line argument parsing."""

    @patch('manage_prs.PRManager')
    @patch('sys.argv', ['manage_prs.py', '--repo', 'owner/repo', '--token', 'test-token'])
    def test_main_with_token_arg(self, mock_manager_class):
        """Test main function with token argument."""
        from manage_prs import main

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        main()

        mock_manager_class.assert_called_once_with('owner', 'repo', 'test-token')
        mock_manager.run.assert_called_once()

    @patch('manage_prs.PRManager')
    @patch.dict(os.environ, {'GITHUB_TOKEN': 'env-token'})
    @patch('sys.argv', ['manage_prs.py', '--repo', 'owner/repo'])
    def test_main_with_env_token(self, mock_manager_class):
        """Test main function with environment variable token."""
        from manage_prs import main

        mock_manager = Mock()
        mock_manager_class.return_value = mock_manager

        main()

        mock_manager_class.assert_called_once_with('owner', 'repo', 'env-token')
        mock_manager.run.assert_called_once()


if __name__ == '__main__':
    unittest.main()
