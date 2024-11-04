import time
from typing import Optional

from src.subnet.validator.database import db_manager
from src.subnet.miner._config import MinerSettings
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from neo4j import READ_ACCESS, GraphDatabase
from neo4j.exceptions import Neo4jError

class GraphSearch:

    def __init__(self, settings: MinerSettings):
        self.driver = GraphDatabase.driver(
            settings.GRAPH_DATABASE_URL,
            auth=(settings.GRAPH_DATABASE_USER, settings.GRAPH_DATABASE_PASSWORD),
            connection_timeout=60,
            max_connection_lifetime=60,
            max_connection_pool_size=128,
            fetch_size=1000,
            encrypted=False,
        )

    def execute_query(self, query: str):
        with self.driver.session(default_access_mode=READ_ACCESS) as session:
            try:
                result = session.run(query)

                # If no results are found, return an empty list
                if not result:
                    return []

                results_data = []

                # Iterate through the query result
                for record in result:
                    processed_record = {}

                    # Iterate over the key-value pairs in each record
                    for key in record.keys():
                        value = record[key]

                        if value is None:
                            # Handle null values gracefully
                            processed_record[key] = None

                        # Process nodes
                        elif hasattr(value, "id") and hasattr(value, "labels"):
                            processed_record[key] = {
                                "id": value.id,
                                "labels": list(value.labels),
                                "properties": dict(value),
                            }

                        # Process relationships
                        elif hasattr(value, "id") and hasattr(value, "type"):
                            processed_record[key] = {
                                "id": value.id,
                                "start": value.start_node.id,
                                "end": value.end_node.id,
                                "label": value.type,
                                "properties": dict(value),
                            }

                        # Handle primitive or other values
                        else:
                            processed_record[key] = value

                    results_data.append(processed_record)

                return results_data

            except Neo4jError as e:
                raise ValueError("Query attempted to modify data, which is not allowed.") from e

    def solve_twitter_challenge(self, token: str, tweet_id: Optional[str] = None, user_id: Optional[str] = None,
                                engagement_score: Optional[int] = None, tweet_date: Optional[str] = None,
                                follower_count: Optional[int] = None, verified: Optional[bool] = None) -> Optional[Dict]:
        start_time = time.time()
        try:
            with self.driver.session() as session:
                # Dynamic query building to handle optional parameters
                query = """
                    MATCH (t:Tweet)-[:POSTED_BY]->(u:UserAccount)
                    WHERE t.token = $token
                """
                params = {'token': token}

                # Add conditions based on provided challenge fields
                if tweet_id:
                    query += " AND t.tweet_id = $tweet_id"
                    params['tweet_id'] = tweet_id
                if user_id:
                    query += " AND u.user_id = $user_id"
                    params['user_id'] = user_id
                if engagement_score:
                    query += " AND t.engagement_score >= $engagement_score"
                    params['engagement_score'] = engagement_score
                if tweet_date:
                    query += " AND t.timestamp >= $tweet_date"
                    params['tweet_date'] = tweet_date
                if follower_count:
                    query += " AND u.follower_count >= $follower_count"
                    params['follower_count'] = follower_count
                if verified is not None:
                    query += " AND u.verified = $verified"
                    params['verified'] = verified

                # Return statement
                query += """
                    RETURN t.tweet_id AS tweet_id, u.user_id AS user_id, t.engagement_score AS engagement_score,
                           t.timestamp AS tweet_date, u.follower_count AS follower_count, u.verified AS verified
                    LIMIT 1;
                """

                # Run query with parameters
                result = session.run(query, **params)
                single_result = result.single()

                if not single_result:
                    return None

                # Structure result in a dictionary
                return {
                    "tweet_id": single_result["tweet_id"],
                    "user_id": single_result["user_id"],
                    "engagement_score": single_result["engagement_score"],
                    "tweet_date": single_result["tweet_date"],
                    "follower_count": single_result["follower_count"],
                    "verified": single_result["verified"],
                }

        except Exception as e:
            logger.error(f"Error in solve_twitter_challenge: {e}")
            return None
        finally:
            end_time = time.time()
            execution_time = end_time - start_time
            logger.info(f"Execution time for solve_twitter_challenge: {execution_time} seconds")

    def close(self):
        self.driver.close()