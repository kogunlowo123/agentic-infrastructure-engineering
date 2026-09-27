"""Git repository connector for IaC document ingestion."""

import logging
import tempfile
from pathlib import Path
from typing import Iterator

from ..loader_registry import Document

logger = logging.getLogger(__name__)

TERRAFORM_EXTENSIONS = {".tf", ".hcl", ".tfvars"}
DOCS_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".json"}
SUPPORTED_EXTENSIONS = TERRAFORM_EXTENSIONS | DOCS_EXTENSIONS


class GitConnector:
    """Clones or updates a git repository and yields documents from it.

    Prioritizes Terraform HCL files (.tf, .hcl) but also ingests
    documentation, YAML configs, and JSON schemas.
    """

    def __init__(
        self,
        repo_url: str,
        branch: str = "main",
        include_extensions: set[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_file_size_bytes: int = 1_000_000,
    ) -> None:
        self._repo_url = repo_url
        self._branch = branch
        self._include_extensions = include_extensions or SUPPORTED_EXTENSIONS
        self._exclude_patterns = exclude_patterns or [
            ".terraform",
            "node_modules",
            ".git",
            "__pycache__",
            "*.tfstate",
            "*.tfplan",
        ]
        self._max_file_size_bytes = max_file_size_bytes

    def stream_documents(
        self,
        local_path: str | None = None,
    ) -> Iterator[Document]:
        """Clone repo and yield documents from matched files.

        Args:
            local_path: If provided, use this path instead of cloning.
                        Useful for local repositories.

        Yields:
            Document objects for each matched file.
        """
        import git  # type: ignore[import]

        if local_path:
            repo_path = Path(local_path)
        else:
            tmp_dir = tempfile.mkdtemp(prefix="rag_git_")
            logger.info("Cloning %s into %s", self._repo_url, tmp_dir)
            try:
                git.Repo.clone_from(
                    self._repo_url,
                    tmp_dir,
                    branch=self._branch,
                    depth=1,
                )
            except git.exc.GitCommandError as exc:
                logger.error("Git clone failed: %s", exc)
                return
            repo_path = Path(tmp_dir)

        yield from self._walk_repository(repo_path)

    def _walk_repository(self, repo_path: Path) -> Iterator[Document]:
        """Walk repository tree and yield documents for matching files."""
        for file_path in repo_path.rglob("*"):
            if not file_path.is_file():
                continue

            if self._is_excluded(file_path, repo_path):
                continue

            if file_path.suffix.lower() not in self._include_extensions:
                continue

            if file_path.stat().st_size > self._max_file_size_bytes:
                logger.debug("Skipping oversized file: %s", file_path)
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
                relative_path = str(file_path.relative_to(repo_path))

                metadata = {
                    "source_path": relative_path,
                    "repo_url": self._repo_url,
                    "branch": self._branch,
                    "extension": file_path.suffix.lower(),
                    "file_type": self._classify_file(file_path),
                    "file_size_bytes": file_path.stat().st_size,
                }

                yield Document(
                    content=content,
                    metadata=metadata,
                    source=relative_path,
                )
            except Exception as exc:
                logger.warning("Failed to read %s: %s", file_path, exc)

    def _is_excluded(self, file_path: Path, base: Path) -> bool:
        """Check if a file should be excluded based on patterns."""
        relative = str(file_path.relative_to(base))
        for pattern in self._exclude_patterns:
            if pattern.lstrip("*.") in relative:
                return True
        return False

    def _classify_file(self, file_path: Path) -> str:
        """Classify file type for metadata."""
        suffix = file_path.suffix.lower()
        if suffix in TERRAFORM_EXTENSIONS:
            return "terraform"
        if suffix in {".md", ".txt"}:
            return "documentation"
        if suffix in {".yaml", ".yml"}:
            return "configuration"
        return "other"
