"""ACL label stamper for access control on retrieved documents."""


class ACLStamper:
    """Stamps ACL labels on documents based on source and content classification.

    ACL labels are used downstream to filter retrieval results based on
    user permissions.
    """

    DEFAULT_LABEL = "public"
    SENSITIVE_PATTERNS = ["production", "prod", "secret", "credential", "password"]

    def stamp(
        self,
        content: str,
        metadata: dict,
        source: str = "",
        tenant_id: str = "",
    ) -> dict:
        """Add ACL labels to metadata.

        Args:
            content: Document content for sensitivity classification.
            metadata: Existing metadata to update.
            source: Source path or URL.
            tenant_id: Owning tenant identifier.

        Returns:
            Updated metadata with acl_labels field.
        """
        labels: list[str] = [self.DEFAULT_LABEL]

        if tenant_id:
            labels.append(f"tenant:{tenant_id}")

        content_lower = content.lower()
        source_lower = source.lower()

        for pattern in self.SENSITIVE_PATTERNS:
            if pattern in content_lower or pattern in source_lower:
                labels.append("sensitive")
                break

        if metadata.get("contains_pii"):
            labels.append("pii")

        metadata["acl_labels"] = list(set(labels))
        return metadata
