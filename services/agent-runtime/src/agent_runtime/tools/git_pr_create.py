"""Git PR creation tool for IaC changes."""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Any

from .base import BaseTool, ToolScope

logger = logging.getLogger(__name__)


@dataclass
class GitPRRequest:
    """Request to create a PR with generated IaC."""

    repo_owner: str
    repo_name: str
    branch_name: str
    hcl_content: str
    file_path: str
    title: str
    description: str
    base_branch: str = "main"


@dataclass
class GitPRResult:
    """Result of PR creation."""

    pr_url: str
    pr_number: int
    branch_name: str


class GitPRCreateTool(BaseTool):
    """Creates a GitHub PR with generated Terraform HCL content."""

    def __init__(self) -> None:
        self._github_token = os.getenv("GITHUB_TOKEN", "")

    @property
    def name(self) -> str:
        return "git_pr_create"

    @property
    def description(self) -> str:
        return (
            "Create a GitHub pull request with generated Terraform HCL content. "
            "Requires GITHUB_TOKEN environment variable."
        )

    @property
    def scope(self) -> ToolScope:
        return ToolScope.READ_WRITE

    def invoke(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Create a Git PR with the specified HCL content.

        Args:
            input_data: GitPRRequest fields.

        Returns:
            GitPRResult as dict with pr_url, pr_number, branch_name.
        """
        req = GitPRRequest(
            repo_owner=input_data.get("repo_owner", os.getenv("GITHUB_REPO_OWNER", "")),
            repo_name=input_data.get("repo_name", os.getenv("GITHUB_REPO_NAME", "")),
            branch_name=input_data.get("branch_name", ""),
            hcl_content=input_data.get("hcl_content", ""),
            file_path=input_data.get("file_path", "infra/generated/main.tf"),
            title=input_data.get("title", "feat(iac): generated infrastructure"),
            description=input_data.get("description", ""),
            base_branch=input_data.get("base_branch", "main"),
        )

        if not self._github_token:
            logger.warning("GITHUB_TOKEN not set, returning mock PR result")
            return {
                "pr_url": f"https://github.com/{req.repo_owner}/{req.repo_name}/pull/0",
                "pr_number": 0,
                "branch_name": req.branch_name,
                "mock": True,
            }

        if not req.branch_name:
            raise ValueError("branch_name is required")

        return self._create_github_pr(req)

    def _create_github_pr(self, req: GitPRRequest) -> dict[str, Any]:
        """Execute git operations and create PR via GitHub API."""
        import git  # type: ignore[import]
        import requests

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                repo_url = (
                    f"https://{self._github_token}@github.com/"
                    f"{req.repo_owner}/{req.repo_name}.git"
                )
                repo = git.Repo.clone_from(repo_url, tmpdir, depth=1)
                repo.git.checkout("-b", req.branch_name)

                # Write the HCL file
                file_full_path = os.path.join(
                    tmpdir, req.file_path.replace("/", os.sep)
                )
                os.makedirs(os.path.dirname(file_full_path), exist_ok=True)
                with open(file_full_path, "w") as f:
                    f.write(req.hcl_content)

                repo.git.add(req.file_path)
                repo.git.commit(
                    "-m",
                    f"{req.title}\n\nAuto-generated Terraform IaC.",
                )
                repo.git.push("origin", req.branch_name)

            except Exception as exc:
                logger.error("Git operations failed: %s", exc)
                return {
                    "pr_url": None,
                    "pr_number": None,
                    "branch_name": req.branch_name,
                    "error": str(exc),
                }

        try:
            headers = {
                "Authorization": f"token {self._github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            pr_payload = {
                "title": req.title,
                "body": req.description,
                "head": req.branch_name,
                "base": req.base_branch,
            }
            response = requests.post(
                f"https://api.github.com/repos/{req.repo_owner}/{req.repo_name}/pulls",
                headers=headers,
                json=pr_payload,
                timeout=30,
            )
            response.raise_for_status()
            pr_data = response.json()

            return {
                "pr_url": pr_data["html_url"],
                "pr_number": pr_data["number"],
                "branch_name": req.branch_name,
            }
        except Exception as exc:
            logger.error("GitHub API call failed: %s", exc)
            return {
                "pr_url": None,
                "pr_number": None,
                "branch_name": req.branch_name,
                "error": str(exc),
            }
