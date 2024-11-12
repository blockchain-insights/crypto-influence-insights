from typing import Dict
from src.subnet.validator.validator import Validator
from src.subnet.validator_api.services import QueryApi

class TwitterFraudDetectionApi(QueryApi):
    def __init__(self, validator: Validator):
        super().__init__()
        self.validator = validator

    async def _execute_query(self, token: str, query: str) -> dict:
        try:
            data = await self.validator.query_miner(token, query=query, miner_key=None)
            return data
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")

    async def _create_in_memory_graph(self, token: str, graph_name: str) -> None:
        query = f"""
        CALL gds.graph.project(
            '{graph_name}',
            ['UserAccount', 'Token', 'Tweet'],
            {{
                MENTIONS: {{
                    type: 'MENTIONS',
                    orientation: 'NATURAL'
                }},
                MENTIONED_IN: {{
                    type: 'MENTIONED_IN',
                    orientation: 'NATURAL'
                }},
                POSTED: {{
                    type: 'POSTED',
                    orientation: 'NATURAL'
                }}
            }}
        )
        """
        await self._execute_query(token, query)

    async def _drop_in_memory_graph(self, token: str, graph_name: str) -> None:
        query = f"CALL gds.graph.drop('{graph_name}')"
        await self._execute_query(token, query)

    async def get_communities(self, token: str, min_size: int) -> dict:
        graph_name = "communityGraph"
        await self._create_in_memory_graph(token, graph_name)
        query = f"""
        CALL gds.louvain.stream('{graph_name}')
        YIELD nodeId, communityId
        WHERE communityId.size >= {min_size}
        RETURN gds.util.asNode(nodeId).id AS node, communityId
        """
        result = await self._execute_query(token, query)
        await self._drop_in_memory_graph(token, graph_name)
        return result

    async def get_influencers(self, token: str, threshold: float) -> dict:
        graph_name = "influencerGraph"
        await self._create_in_memory_graph(token, graph_name)
        query = f"""
        CALL gds.pageRank.stream('{graph_name}')
        YIELD nodeId, score
        WHERE score > {threshold}
        RETURN gds.util.asNode(nodeId).id AS node, score
        """
        result = await self._execute_query(token, query)
        await self._drop_in_memory_graph(token, graph_name)
        return result

    async def get_similarity(self, token: str, similarity_threshold: float) -> dict:
        graph_name = "similarityGraph"
        await self._create_in_memory_graph(token, graph_name)
        query = f"""
        CALL gds.nodeSimilarity.stream('{graph_name}')
        YIELD node1, node2, similarity
        WHERE similarity > {similarity_threshold}
        RETURN gds.util.asNode(node1).id AS user1, gds.util.asNode(node2).id AS user2, similarity
        """
        result = await self._execute_query(token, query)
        await self._drop_in_memory_graph(token, graph_name)
        return result

    async def get_scam_mentions(self, token: str, timeframe: str) -> dict:
        # No in-memory graph needed for regular Cypher MATCH queries
        query = f"""
        MATCH (t:Token {{name: '{token}'}})<-[:MENTIONED_IN]-(tweet:Tweet)
        WHERE tweet.timestamp >= datetime().epochMillis - duration('{timeframe}').toMillis()
        RETURN tweet.id AS tweet, tweet.timestamp AS timestamp
        """
        return await self._execute_query(token, query)

    async def get_anomalies(self, token: str) -> dict:
        graph_name = "anomalyGraph"
        await self._create_in_memory_graph(token, graph_name)
        query = f"""
        CALL gds.beta.node2vec.stream('{graph_name}')
        YIELD nodeId, embedding
        RETURN gds.util.asNode(nodeId).id AS node, embedding
        """
        result = await self._execute_query(token, query)
        await self._drop_in_memory_graph(token, graph_name)
        return result
