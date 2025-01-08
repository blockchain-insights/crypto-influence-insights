from random import random
from typing import Dict
import numpy as np
from random import choice
import re
from src.subnet.validator.validator import Validator
from src.subnet.gateway.services import QueryApi
from loguru import logger

class TwitterFraudDetectionApi(QueryApi):
    def __init__(self, validator: Validator):
        super().__init__()
        self.validator = validator

    async def _execute_query(self, token: str, query: str) -> dict:
        try:
            data = await self.validator.query_memgraph(token, query=query)
            return data
        except Exception as e:
            raise Exception(f"Error executing query: {str(e)}")

    async def get_user_engagement_trends(self, token: str, days: int = 30, region: str = None) -> dict:
        """
        Retrieves engagement trends for a specified token over the last `days`, optionally filtered by region.
        """
        duration_str = f"P{days}D"

        # Construct the query
        query = f"""
        MATCH (u:UserAccount)-[:POSTED]->(t:Tweet)<-[:MENTIONED_IN]-(tok:Token {{name: '{token}'}})
        WHERE datetime(replace(split(t.timestamp, '+')[0], ' ', 'T') + 'Z') >= datetime() - duration('{duration_str}')
        """

        if region:
            query += f"""
            MATCH (u)-[:LOCATED_IN]->(r:Region)
            WHERE r.name = '{region}'
            """

        query += """
        RETURN date(localdatetime(replace(split(t.timestamp, '+')[0], ' ', 'T'))) AS date, 
               COUNT(DISTINCT u.user_id) AS active_users,
               SUM(u.engagement_level) AS daily_engagement
        ORDER BY date ASC
        """

        # Execute the query
        raw_result = await self._execute_query(token, query)

        if not raw_result or not raw_result.get("results"):
            # Return empty results
            return raw_result

        # Convert date objects in the results to strings
        for row in raw_result["results"]:
            if "date" in row:
                row["date"] = str(row["date"])  # Convert neo4j.time.Date to string

        return raw_result

    async def get_influencers(
            self,
            token: str,
            min_follower_count: int = 1000,
            limit: int = 10,
            time_period: int = None,  # Time period in days
            min_tweet_count: int = 0,  # Minimum tweet count
            verified: bool = None  # Filter for verified users
    ) -> dict:
        # Base query
        query = f"""
        MATCH (u:UserAccount)-[:POSTED]->(t:Tweet)<-[:MENTIONED_IN]-(tok:Token {{name: '{token}'}})
        WHERE u.follower_count >= {min_follower_count} AND u.engagement_level > 0
        """

        # Add verified filter if specified
        if verified is not None:
            query += f" AND u.is_blue_verified = {'true' if verified else 'false'}"

        # Add time period filter if specified
        if time_period:
            query += f"""
            AND datetime(replace(split(t.timestamp, '+')[0], ' ', 'T') + 'Z') >= datetime() - duration('P{time_period}D')
            """

        # Ensure DISTINCT users
        query += " WITH DISTINCT u"

        # Add min_tweet_count filter if specified
        if min_tweet_count > 0:
            query += f" WHERE u.total_tweets >= {min_tweet_count}"

        # Add sorting and return clause
        query += f"""
        RETURN u.user_id AS user_id, u.username AS user_name, u.follower_count AS follower_count, u.is_blue_verified AS verified,
               u.engagement_level AS engagement_level, u.total_tweets AS total_tweets,
               (u.follower_count * u.engagement_level) AS combined_score
        ORDER BY combined_score DESC, u.total_tweets DESC
        LIMIT {limit}
        """

        # Execute the query
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

    async def fetch_account_analysis(self, token: str, limit: int = 50) -> dict:
        """
        Fetch account analysis with user classifications flattened directly in the query,
        including the most recent tweet text for each user.
        """
        query = f"""
            MATCH (u:UserAccount)-[:POSTED]->(t:Tweet)<-[:MENTIONED_IN]-(tok:Token {{name: '{token}'}})
            OPTIONAL MATCH (u)-[:LOCATED_IN]->(r:Region)
            WITH u, t, tok, r,
                 COALESCE(u.total_tweets, 0) AS tweet_count, 
                 SUM(t.likes) AS total_likes,
                 AVG(u.engagement_level) AS avg_engagement,
                 MAX(t.likes) AS max_likes,
                 u.follower_count AS follower_count,
                 t.text AS tweet_text,
                 t.url AS tweet_url
            WITH u, r, tweet_text, tweet_url, tweet_count, total_likes, avg_engagement, max_likes, follower_count,
                 CASE 
                     WHEN follower_count > 10000 AND avg_engagement / follower_count < 0.001 THEN 'High Followers Low Engagement'
                     WHEN follower_count < 1000 AND avg_engagement / follower_count > 0.1 THEN 'Low Followers High Engagement'
                     WHEN tweet_count > 10000 AND avg_engagement / tweet_count < 0.01 THEN 'High Tweets Low Engagement'
                     WHEN tweet_count < 100 AND avg_engagement / tweet_count > 0.1 THEN 'Low Tweets High Engagement'
                     WHEN follower_count > 10000 AND tweet_count < 100 THEN 'High Followers Few Tweets'
                     WHEN tweet_count > 10000 AND follower_count < 1000 THEN 'High Tweets Few Followers'
                     ELSE NULL
                 END AS user_classification
            WHERE user_classification IS NOT NULL
            WITH user_classification, u, r, tweet_text, tweet_url, tweet_count, total_likes, avg_engagement, max_likes, follower_count
            ORDER BY user_classification, follower_count DESC
            WITH user_classification, COLLECT({{
                user_id: u.user_id,
                username: u.username,
                follower_count: follower_count,
                avg_engagement: avg_engagement,
                tweet_count: tweet_count,
                total_likes: total_likes,
                max_likes: max_likes,
                region_name: r.name,
                tweet_text: tweet_text,
                tweet_url: tweet_url
            }})[0..{limit}] AS users_per_class
            UNWIND users_per_class AS user
            RETURN 
                user_classification,
                user.user_id AS user_id,
                user.username AS username,
                user.follower_count AS follower_count,
                user.avg_engagement AS avg_engagement,
                user.tweet_count AS tweet_count,
                user.total_likes AS total_likes,
                user.max_likes AS max_likes,
                user.region_name AS region_name,
                user.tweet_text AS tweet_text,
                user.tweet_url AS tweet_url
            ORDER BY user_classification, follower_count DESC
        """
        try:
            # Execute the Cypher query and fetch the result
            return await self.validator.query_memgraph(
                token=token,
                query=query
            )
        except Exception as e:
            raise Exception(f"Error fetching account analysis: {str(e)}")
