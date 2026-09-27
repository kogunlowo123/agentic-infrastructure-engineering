"""Grounding check to verify generated HCL references retrieved templates."""

import logging
import re

logger = logging.getLogger(__name__)

RESOURCE_PATTERN = re.compile(r'resource\s+"([^"]+)"')


class GroundingChecker:
    """Verifies generated HCL is grounded in retrieved templates."""

    def check(
        self,
        generated_hcl: str,
        retrieved_templates: list[dict],
    ) -> tuple[bool, float]:
        """Check how grounded the generated HCL is in source templates.

        Returns:
            (is_grounded, grounding_score 0-1)
        """
        if not retrieved_templates:
            return True, 0.5

        generated_resources = set(RESOURCE_PATTERN.findall(generated_hcl))
        if not generated_resources:
            return True, 1.0

        template_text = " ".join(t.get("content", "") for t in retrieved_templates)
        template_resources = set(RESOURCE_PATTERN.findall(template_text))

        if not template_resources:
            return True, 0.5

        intersection = generated_resources.intersection(template_resources)
        score = len(intersection) / len(generated_resources)

        is_grounded = score >= 0.5
        return is_grounded, score
