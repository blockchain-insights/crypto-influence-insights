from typing import Optional, List, Dict

class QueryApi:
    """Interface for querying fraud detection and Twitter analysis data."""

    async def get_communities(self, min_size: int) -> Dict:
        """Retrieve communities of interconnected users, tweets, or tokens."""
        raise NotImplementedError("Method 'get_communities' must be implemented by subclass.")

    async def get_influencers(self, threshold: float) -> Dict:
        """Identify influential nodes, such as users or tokens with high centrality scores."""
        raise NotImplementedError("Method 'get_influencers' must be implemented by subclass.")

    async def get_similarity(self, similarity_threshold: float) -> Dict:
        """Detect similar patterns or behaviors between nodes based on a similarity threshold."""
        raise NotImplementedError("Method 'get_similarity' must be implemented by subclass.")

    async def get_scam_mentions(self, token: str, timeframe: str) -> Dict:
        """Identify mentions of a token across multiple tweets within a specific timeframe."""
        raise NotImplementedError("Method 'get_scam_mentions' must be implemented by subclass.")

    async def get_anomalies(self) -> Dict:
        """Detect anomalies in node behavior, which may indicate potential fraud."""
        raise NotImplementedError("Method 'get_anomalies' must be implemented by subclass.")
