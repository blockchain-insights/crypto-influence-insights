import time
from typing import Optional, Dict

from src.subnet.validator.database import db_manager
from src.subnet.miner._config import MinerSettings
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from neo4j import WRITE_ACCESS, READ_ACCESS, GraphDatabase
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

    def solve_twitter_challenge(self, token: str) -> Optional[Dict]:
        start_time = time.time()
        try:
            with self.driver.session() as session:
                # Execute the Cypher query to find the latest tweet for the token
                query = f"""
                    MATCH (u:UserAccount)-[:MENTIONS]->(token:Token {{name: "{token}"}})
                    MATCH (token)-[:MENTIONED_IN]->(t:Tweet)
                    MATCH (u)-[:POSTED]->(t)
                    RETURN 
                        t.id AS tweet_id, 
                        u.user_id AS user_id, 
                        t.timestamp AS tweet_date, 
                        u.follower_count AS follower_count, 
                        u.is_verified AS verified
                    ORDER BY t.timestamp DESC
                    LIMIT 1
                """

                # Run query without additional parameters, as token is embedded directly in the query string
                result = session.run(query)
                single_result = result.single()

                if not single_result:
                    logger.warning(f"No tweet found for token {token}")
                    return None

                # Structure result in a dictionary to match the TwitterChallenge output format
                return {
                    "tweet_id": single_result["tweet_id"],
                    "user_id": single_result["user_id"],
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