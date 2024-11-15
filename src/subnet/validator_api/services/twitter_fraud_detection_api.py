from typing import Dict
import numpy as np
import re
from src.subnet.validator.validator import Validator
from src.subnet.validator_api.services import QueryApi
from loguru import logger

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

    async def get_user_engagement_trends(self, token: str, days: int = 30) -> dict:
        """
        Retrieves engagement trends for a specified token over the last `days`.
        """

        # Duration string for Cypher query
        duration_str = f"P{days}D"

        # Cypher query to aggregate engagement per day for a specified token
        query = f"""
        MATCH (u:UserAccount)-[:POSTED]->(t:Tweet)<-[:MENTIONED_IN]-(tok:Token {{name: '{token}'}})
        WHERE datetime(replace(t.timestamp, " ", "T")) >= datetime() - duration('{duration_str}')
        RETURN toString(date(datetime(replace(t.timestamp, " ", "T")))) AS date, 
               COUNT(DISTINCT u.user_id) AS active_users,
               SUM(u.engagement_level) AS daily_engagement
        ORDER BY date ASC
        """

        # Execute the query
        result = await self._execute_query(token, query)

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

    async def get_similarity(self, token: str, similarity_threshold: float, similarity_type: str,
                             limit: int = 10) -> dict:
        # Define Cypher queries for the two similarity types
        if similarity_type == "activity-based":
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
            RETURN u1.user_id AS user1_id, u1.username AS user1_name, 
                   u2.user_id AS user2_id, u2.username AS user2_name, similarity
            ORDER BY similarity DESC
            LIMIT {limit}
            """
        elif similarity_type == "engagement-based":
            query = f"""
            MATCH (u1:UserAccount)-[:POSTED]->(t1:Tweet)<-[:MENTIONED_IN]-(:Token {{name: '{token}'}}),
                  (u2:UserAccount)-[:POSTED]->(t2:Tweet)<-[:MENTIONED_IN]-(:Token {{name: '{token}'}})
            WHERE id(u1) < id(u2)
            WITH u1, u2, 
                 COUNT(t1) AS tweets_u1, COUNT(t2) AS tweets_u2,
                 u1.follower_count AS followers_u1, u2.follower_count AS followers_u2,
                 u1.engagement_level AS engagement_u1, u2.engagement_level AS engagement_u2
            WITH u1, u2,
                 (followers_u1 * followers_u2 + engagement_u1 * engagement_u2 + tweets_u1 * tweets_u2) /
                 (sqrt(followers_u1^2 + engagement_u1^2 + tweets_u1^2) * sqrt(followers_u2^2 + engagement_u2^2 + tweets_u2^2)) AS similarity
            WHERE similarity > {similarity_threshold}
            RETURN u1.user_id AS user1_id, u1.username AS user1_name, 
                   u2.user_id AS user2_id, u2.username AS user2_name, similarity
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
        # Query to extract key behavioral metrics, including follower count
        query = f"""
        MATCH (u:UserAccount)-[:POSTED]->(t:Tweet)<-[:MENTIONED_IN]-(:Token {{name: '{token}'}})
        WITH u, COUNT(t) AS post_count, AVG(u.engagement_level) AS avg_engagement, 
             u.follower_count AS follower_count
        RETURN u.user_id AS user_id, u.username AS username, post_count, avg_engagement, follower_count
        """
        # Execute the query to get the metrics
        result = await self._execute_query(token, query)

        # Log the result to inspect its structure
        logger.info(f"Result from _execute_query: {result}")

        # Step 2: Process results to identify anomalies
        processed_results = self._detect_anomalies(result)
        return processed_results

    def _detect_anomalies(self, data: dict) -> dict:
        # Check if 'response' key contains the rows as expected
        if "response" not in data or not isinstance(data["response"], list):
            logger.error("Unexpected data format: %s", data)
            return data  # Return the original data if format is unexpected

        # Extract the rows from response
        rows = data["response"]

        # Extract follower counts and average engagement for calculation
        follower_counts = [row['follower_count'] for row in rows if row.get('follower_count') is not None]
        avg_engagements = [row['avg_engagement'] for row in rows if row.get('avg_engagement') is not None]

        # Calculate quantile thresholds for anomaly detection
        if len(follower_counts) > 1 and len(avg_engagements) > 1:
            low_follower_threshold = np.percentile(follower_counts, 15)
            high_follower_threshold = np.percentile(follower_counts, 85)
            low_engagement_threshold = np.percentile(avg_engagements, 15)
            high_engagement_threshold = np.percentile(avg_engagements, 85)

            # Detect anomalies based on disproportionate engagement to follower count
            for user in rows:
                followers = user.get('follower_count', 0)
                engagement = user.get('avg_engagement', 0)

                # Check for high followers with low engagement or low followers with high engagement
                is_anomalous = (
                        (followers >= high_follower_threshold and engagement <= low_engagement_threshold) or
                        (followers <= low_follower_threshold and engagement >= high_engagement_threshold)
                )

                # Label based on anomaly status directly in the original response data
                user['anomaly_label'] = "Anomalous" if is_anomalous else "Normal"

        # Return the modified data with labeled anomalies
        return data