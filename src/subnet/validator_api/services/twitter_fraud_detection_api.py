from datetime import datetime
from typing import Optional, List
from src.subnet.validator.validator import Validator
from src.subnet.validator_api.services import QueryApi

class TwitterFraudDetectionApi(QueryApi):
    def __init__(self, validator: Validator):
        super().__init__()
        self.validator = validator

    async def _execute_query(self, query: str) -> dict:
        try:
            data = await self.validator.query_miner(query=query)
            return data
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")

    async def get_communities(self, min_size: int) -> dict:
        query = f"""
        CALL gds.louvain.stream({{
            nodeProjection: ['User', 'Token', 'Tweet'],
            relationshipProjection: 'MENTIONS'
        }})
        YIELD nodeId, communityId
        WHERE communityId.size >= {min_size}
        RETURN gds.util.asNode(nodeId).id AS node, communityId
        """
        return await self._execute_query(query)

    async def get_influencers(self, threshold: float) -> dict:
        query = f"""
        CALL gds.pageRank.stream({{
            nodeProjection: 'User',
            relationshipProjection: 'MENTIONS'
        }})
        YIELD nodeId, score
        WHERE score > {threshold}
        RETURN gds.util.asNode(nodeId).id AS node, score
        """
        return await self._execute_query(query)

    async def get_similarity(self, similarity_threshold: float) -> dict:
        query = f"""
        CALL gds.nodeSimilarity.stream({{
            nodeProjection: 'User',
            relationshipProjection: 'LOCATED_IN'
        }})
        YIELD node1, node2, similarity
        WHERE similarity > {similarity_threshold}
        RETURN gds.util.asNode(node1).id AS user1, gds.util.asNode(node2).id AS user2, similarity
        """
        return await self._execute_query(query)

    async def get_scam_mentions(self, token: str, timeframe: str) -> dict:
        query = f"""
        MATCH (t:Token {{name: '{token}'}})<-[:MENTIONED_IN]-(tweet:Tweet)
        WHERE tweet.timestamp >= datetime().epochMillis - duration('{timeframe}').toMillis()
        RETURN tweet.id AS tweet, tweet.timestamp AS timestamp
        """
        return await self._execute_query(query)

    async def get_anomalies(self) -> dict:
        query = """
        CALL gds.beta.node2vec.stream({
            nodeProjection: ['User', 'Token'],
            relationshipProjection: {
                MENTIONS: {type: 'MENTIONS', orientation: 'UNDIRECTED'}
            }
        })
        YIELD nodeId, embedding
        RETURN gds.util.asNode(nodeId).id AS node, embedding
        """
        return await self._execute_query(query)
