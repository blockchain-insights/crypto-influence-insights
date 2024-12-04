import time
from typing import Optional, Dict
from src.subnet.validator.database import db_manager
from src.subnet.miner._config import MinerSettings
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from neo4j import WRITE_ACCESS, GraphDatabase
from neo4j.exceptions import Neo4jError
from neo4j.graph import Node, Relationship


class GraphSearch:
    # Define prohibited clauses to prevent data modification
    MODIFICATION_CLAUSES = {"CREATE", "DELETE", "SET", "MERGE", "REMOVE"}

    # Define allowed GDS modification commands
    ALLOWED_GDS_COMMANDS = {"CALL GDS.GRAPH.PROJECT", "CALL GDS.GRAPH.DROP"}

    # Define allowed APOC procedures
    ALLOWED_APOC_COMMANDS = {"CALL APOC.EXPORT.CYPHER.QUERY"}

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
        """
        Executes a Cypher query after validating it against allowed commands.
        Supports GDS commands and specific APOC procedures.
        """
        query_upper = query.upper().strip()

        # Check if query contains prohibited modification clauses
        if any(clause in query_upper for clause in self.MODIFICATION_CLAUSES):
            # Allow only explicitly permitted commands
            if not any(command in query_upper for command in self.ALLOWED_GDS_COMMANDS | self.ALLOWED_APOC_COMMANDS):
                raise ValueError(
                    "Modification queries are not allowed. Only GDS project/drop, APOC export, and read-only queries are permitted."
                )

        with self.driver.session(default_access_mode=WRITE_ACCESS) as session:
            try:
                print("Executing query:", query)
                result = session.run(query)

                raw_data = result.data()
                print("Raw result:", raw_data)

                if not raw_data:
                    return []

                results_data = []
                for record in raw_data:
                    processed_record = {}
                    for key, value in record.items():
                        if value is None:
                            processed_record[key] = None
                        elif isinstance(value, Node):
                            processed_record[key] = {
                                "id": value.id,
                                "labels": list(value.labels),
                                "properties": dict(value),
                            }
                        elif isinstance(value, Relationship):
                            processed_record[key] = {
                                "id": value.id,
                                "start": value.start_node.id,
                                "end": value.end_node.id,
                                "label": value.type,
                                "properties": dict(value),
                            }
                        else:
                            processed_record[key] = value

                    results_data.append(processed_record)

                return results_data

            except Neo4jError as e:
                raise ValueError(f"Error executing query: {e.message}")

    def solve_twitter_challenge(self, token: str) -> Optional[Dict]:
        """
        Solves a Twitter challenge by finding the latest tweet mentioning a token.
        """
        start_time = time.time()
        try:
            with self.driver.session(default_access_mode=WRITE_ACCESS) as session:
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
                result = session.run(query)
                single_result = result.single()

                if not single_result:
                    logger.warning(f"No tweet found for token {token}")
                    return None

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
            logger.info(f"Execution time for solve_twitter_challenge: {end_time - start_time} seconds")

    def close(self):
        """
        Closes the Neo4j driver connection.
        """
        self.driver.close()
