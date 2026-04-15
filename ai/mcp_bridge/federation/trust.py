"""Trust scoring for external MCP servers for P105.

Computes trust scores based on server characteristics, history,
and policy factors without executing remote code.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from ai.mcp_bridge.federation.discovery import ExternalServerDiscovery
from ai.mcp_bridge.federation.models import (
    CapabilityMap,
    ServerToolManifest,
    TrustScore,
    TrustState,
)

logger = logging.getLogger("ai.mcp_bridge.federation.trust")


class TrustScorer:
    """Computes trust scores for external MCP servers.

    Analyzes server characteristics without executing remote code.
    """

    DEFAULT_TIMEOUT = 10.0

    def __init__(self, discovery: ExternalServerDiscovery):
        """Initialize trust scorer.

        Args:
            discovery: Server discovery instance
        """
        self._discovery = discovery

    def compute_trust_score(
        self,
        server_id: str,
        manifest: ServerToolManifest | None = None,
        capability_map: CapabilityMap | None = None,
    ) -> TrustScore:
        """Compute trust score for server.

        Args:
            server_id: Server identifier
            manifest: Optional tool manifest
            capability_map: Optional capability map

        Returns:
            Trust score with factors
        """
        factors: dict[str, float] = {}

        factors["https"] = self._score_https(server_id)
        factors["verified"] = self._score_verified(server_id)
        factors["transparency"] = self._score_transparency(server_id, manifest)
        factors["capabilities"] = self._score_capabilities(server_id, capability_map)
        factors["history"] = self._score_history(server_id)

        overall = self._calculate_overall_score(factors)

        return TrustScore(
            server_id=server_id,
            overall_score=overall,
            factors=factors,
            last_calculated=datetime.utcnow(),
        )

    def _score_https(self, server_id: str) -> float:
        """Score based on HTTPS usage."""
        server = self._discovery.get_server(server_id)
        if not server:
            return 0.0

        if server.url.startswith("https://"):
            return 50.0

        return 0.0

    def _score_verified(self, server_id: str) -> float:
        """Score based on verification status."""
        server = self._discovery.get_server(server_id)
        if not server:
            return 0.0

        if server.trust_state == TrustState.VERIFIED:
            return 30.0
        elif server.trust_state == TrustState.PENDING:
            return 15.0
        elif server.trust_state == TrustState.SUSPECTED:
            return -20.0
        elif server.trust_state == TrustState.BLOCKED:
            return -50.0

        return 0.0

    def _score_transparency(self, server_id: str, manifest: ServerToolManifest | None) -> float:
        """Score based on manifest transparency."""
        if not manifest:
            return 0.0

        score = 0.0

        if manifest.tools:
            score += 5.0

        has_descriptions = sum(1 for t in manifest.tools if t.description)
        if manifest.tools:
            score += (has_descriptions / len(manifest.tools)) * 10.0

        if manifest.resource_templates:
            score += 3.0

        if manifest.prompt_templates:
            score += 2.0

        return min(score, 20.0)

    def _score_capabilities(self, server_id: str, capability_map: CapabilityMap | None) -> float:
        """Score based on capability analysis."""
        if not capability_map:
            return 0.0

        score = 0.0

        if not capability_map.has_destructive_tools:
            score += 10.0
        else:
            score -= 15.0

        if not capability_map.has_system_tools:
            score += 10.0
        else:
            score -= 20.0

        if not capability_map.network_access:
            score += 5.0

        if not capability_map.file_access:
            score += 5.0

        return max(min(score, 30.0), -30.0)

    def _score_history(self, server_id: str) -> float:
        """Score based on server history."""
        server = self._discovery.get_server(server_id)
        if not server:
            return 0.0

        score = 0.0

        age = datetime.utcnow() - server.first_seen
        if age > timedelta(days=30):
            score += 10.0
        elif age > timedelta(days=7):
            score += 5.0

        if server.last_verified:
            verified_age = datetime.utcnow() - server.last_verified
            if verified_age < timedelta(days=1):
                score += 10.0
            elif verified_age < timedelta(days=7):
                score += 5.0

        return min(score, 20.0)

    def _calculate_overall_score(self, factors: dict[str, float]) -> float:
        """Calculate overall trust score from factors.

        Args:
            factors: Score factors

        Returns:
            Overall score 0-100
        """
        weights = {
            "https": 0.1,
            "verified": 0.25,
            "transparency": 0.2,
            "capabilities": 0.25,
            "history": 0.2,
        }

        weighted_sum = sum(factors.get(factor, 0) * weight for factor, weight in weights.items())

        return max(min(weighted_sum, 100.0), 0.0)

    def determine_trust_state(self, score: TrustScore) -> TrustState:
        """Determine trust state from score.

        Args:
            score: Trust score

        Returns:
            Trust state
        """
        if score.overall_score >= 70:
            return TrustState.VERIFIED
        elif score.overall_score >= 40:
            return TrustState.PENDING
        elif score.overall_score >= 20:
            return TrustState.SUSPECTED
        else:
            return TrustState.BLOCKED
