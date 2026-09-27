"""ACL-based filtering for search results."""

import logging

from ..stores.vector_base import SearchResult

logger = logging.getLogger(__name__)


class ACLFilter:
    """Filters search results based on user ACL labels.

    Documents are stamped with acl_labels during ingestion.
    Only documents whose labels intersect with the user's allowed
    labels are returned.
    """

    def __init__(self, allow_all_if_no_acl: bool = True) -> None:
        """Initialize ACL filter.

        Args:
            allow_all_if_no_acl: If True, documents with no acl_labels
                                  are accessible to all users.
        """
        self._allow_all_if_no_acl = allow_all_if_no_acl

    def filter(
        self,
        results: list[SearchResult],
        user_labels: set[str],
    ) -> list[SearchResult]:
        """Filter results to only those the user can access.

        Args:
            results: Search results to filter.
            user_labels: Set of ACL labels the requesting user possesses.

        Returns:
            Filtered list of accessible results.
        """
        filtered = []
        for result in results:
            doc_labels: list[str] = result.metadata.get("acl_labels", [])

            if not doc_labels:
                if self._allow_all_if_no_acl:
                    filtered.append(result)
                continue

            if user_labels.intersection(set(doc_labels)):
                filtered.append(result)

        return filtered
