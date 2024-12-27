from neo4j import GraphDatabase
from loguru import logger
from typing import List, Dict

class ValidatorGraphHandler:
    def __init__(self, settings):
        """
        Initialize the graph handler using settings for Memgraph connection.
        """
        self.driver = GraphDatabase.driver(
            settings.GRAPH_DB_URL,
            auth=(settings.GRAPH_DB_USER, settings.GRAPH_DB_PASSWORD)
        )

    def close(self):
        """
        Close the Memgraph driver connection.
        """
        self.driver.close()

    def merge_data(self, dataset: List[Dict], scrape_token: str) -> None:
        """
        Merge new data into the graph database (insert or update).

        Args:
            dataset (List[Dict]): List of validated dataset entries.
            scrape_token (str): Identifier for the scrape session.
        """
        with self.driver.session() as session:
            try:
                for entry in dataset:
                    token = entry['token']
                    tweet = entry['tweet']
                    user_account = entry['user_account']
                    region = entry['region']
                    edges = entry['edges']

                    # Upsert Token node
                    session.run(
                        """
                        MERGE (t:Token {name: $token_name})
                        ON CREATE SET t.created_at = timestamp()
                        ON MATCH SET t.updated_at = timestamp()
                        """,
                        token_name=token
                    )

                    # Upsert Tweet node
                    session.run(
                        """
                        MERGE (tw:Tweet {id: $tweet_id})
                        ON CREATE SET tw.text = $text, tw.timestamp = $timestamp
                        ON MATCH SET tw.text = $text, tw.timestamp = $timestamp, tw.updated_at = timestamp()
                        """,
                        tweet_id=tweet['id'], text=tweet['text'], timestamp=tweet['timestamp']
                    )

                    # Upsert UserAccount node
                    session.run(
                        """
                        MERGE (ua:UserAccount {user_id: $user_id})
                        ON CREATE SET ua.username = $username, ua.follower_count = $follower_count
                        ON MATCH SET ua.username = $username, ua.follower_count = $follower_count, ua.updated_at = timestamp()
                        """,
                        user_id=user_account['user_id'], username=user_account['username'],
                        follower_count=user_account['follower_count']
                    )

                    # Upsert Region node
                    if region.get('name') and region['name'] != "Unknown":
                        session.run(
                            """
                            MERGE (r:Region {name: $region_name})
                            ON CREATE SET r.created_at = timestamp()
                            ON MATCH SET r.updated_at = timestamp()
                            """,
                            region_name=region['name']
                        )

                    # Upsert relationships
                    for edge in edges:
                        if edge['type'] == 'MENTIONS':
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (t:Token {name: $token_name})
                                MERGE (ua)-[r:MENTIONS]->(t)
                                ON CREATE SET r.timestamp = $timestamp
                                ON MATCH SET r.timestamp = $timestamp
                                """,
                                user_id=user_account['user_id'], token_name=token,
                                timestamp=edge['attributes']['timestamp']
                            )
                        elif edge['type'] == 'POSTED':
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (tw:Tweet {id: $tweet_id})
                                MERGE (ua)-[r:POSTED]->(tw)
                                ON CREATE SET r.timestamp = $timestamp
                                ON MATCH SET r.timestamp = $timestamp
                                """,
                                user_id=user_account['user_id'], tweet_id=tweet['id'],
                                timestamp=edge['attributes']['timestamp']
                            )

                logger.info(f"Successfully merged {len(dataset)} entries into the graph database.")
            except Exception as e:
                logger.error(f"Error merging data into Memgraph: {str(e)}")
