from typing import Dict
import re
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
        WITH communityId, nodeId, COUNT(nodeId) AS communitySize
        WHERE communitySize >= {min_size}
        MATCH (n) WHERE id(n) = nodeId
        RETURN communityId, communitySize, n.id AS node
        """
        result = await self._execute_query(token, query)
        await self._drop_in_memory_graph(token, graph_name)
        return result

    async def get_influencers(self, token: str, min_follower_count: int = 1000, limit: int = 10) -> dict:
        query = f"""
        MATCH (u:UserAccount)-[:POSTED]->(t:Tweet)<-[:MENTIONED_IN]-(:Token {{name: '{token}'}})
        WHERE u.follower_count >= {min_follower_count} AND u.engagement_level > 0
        RETURN u.user_id AS user_id, u.username AS user_name, u.follower_count AS follower_count, 
               COUNT(t) AS tweet_count, AVG(u.engagement_level) AS avg_engagement_level
        ORDER BY avg_engagement_level DESC, tweet_count DESC
        LIMIT {limit}
        """
        result = await self._execute_query(token, query)
        return result

    async def get_similarity(self, token: str, similarity_threshold: float, type: str, limit: int) -> dict:
        # Define Cypher queries for the two similarity types
        if type == "activity-based":
            # Manually calculate Euclidean distance similarity
            query = f"""
            MATCH (u1:UserAccount)-[:POSTED]->(t1:Tweet)<-[:MENTIONED_IN]-(:Token {{name: '{token}'}}),
                  (u2:UserAccount)-[:POSTED]->(t2:Tweet)<-[:MENTIONED_IN]-(:Token {{name: '{token}'}})
            WHERE id(u1) < id(u2)
            WITH u1, u2, 
                 COUNT(t1) AS tweets_u1, COUNT(t2) AS tweets_u2,
                 u1.engagement_level AS engagement_u1, u2.engagement_level AS engagement_u2
            WITH u1, u2,
                 1 / (1 + sqrt((tweets_u1 - tweets_u2)^2 + (engagement_u1 - engagement_u2)^2)) AS similarity
            WHERE similarity > {similarity_threshold}
            RETURN u1.user_id AS user1, u2.user_id AS user2, similarity
            ORDER BY similarity DESC
            LIMIT {limit}
            """
        elif type == "engagement-based":
            # Manually calculate cosine similarity
            query = f"""
            MATCH (u1:UserAccount)-[:POSTED]->(t1:Tweet)<-[:MENTIONED_IN]-(:Token {{name: '{token}'}}),
                  (u2:UserAccount)-[:POSTED]->(t2:Tweet)<-[:MENTIONED_IN]-(:Token {{name: '{token}'}})
            WHERE id(u1) < id(u2)
            WITH u1, u2, 
                 COUNT(t1) AS tweet_count_u1, COUNT(t2) AS tweet_count_u2,
                 u1.follower_count AS follower_count_u1, u2.follower_count AS follower_count_u2,
                 u1.engagement_level AS engagement_u1, u2.engagement_level AS engagement_u2
            WITH u1, u2,
                 (follower_count_u1 * follower_count_u2 + engagement_u1 * engagement_u2 + tweet_count_u1 * tweet_count_u2) /
                 (sqrt(follower_count_u1^2 + engagement_u1^2 + tweet_count_u1^2) * sqrt(follower_count_u2^2 + engagement_u2^2 + tweet_count_u2^2)) AS similarity
            WHERE similarity > {similarity_threshold}
            RETURN u1.user_id AS user1, u2.user_id AS user2, similarity
            ORDER BY similarity DESC
            LIMIT {limit}
            """
        else:
            raise ValueError("Invalid type specified. Expected 'activity-based' or 'engagement-based'.")

        result = await self._execute_query(token, query)
        return result

    async def get_scam_mentions(self, token: str, timeframe: str) -> dict:
        # Parse the hours from the timeframe string, e.g., "24h" to 24
        match = re.match(r"(\d+)h", timeframe)
        if not match:
            raise ValueError("Invalid timeframe format. Expected format like '24h'.")

        # Convert the hours to an integer
        hours = int(match.group(1))

        # Construct the duration string for Neo4j (e.g., 'PT24H' for 24 hours)
        duration_str = f'PT{hours}H'

        # Adjust the Cypher query to handle datetime comparison
        query = f"""
        MATCH (t:Token {{name: '{token}'}})-[:MENTIONED_IN]->(tweet:Tweet)
        WHERE datetime(replace(tweet.timestamp, " ", "T")) >= datetime() - duration('{duration_str}')
        RETURN tweet.id AS tweet_id, tweet.text as tweet_text, tweet.timestamp AS timestamp
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
