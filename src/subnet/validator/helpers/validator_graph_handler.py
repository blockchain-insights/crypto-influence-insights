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

                    # Upsert Tweet node with all fields
                    session.run(
                        """
                        MERGE (tw:Tweet {id: $tweet_id})
                        ON CREATE SET 
                            tw.url = $url,
                            tw.text = $text,
                            tw.likes = $likes,
                            tw.retweets = $retweets,
                            tw.timestamp = $timestamp
                        ON MATCH SET 
                            tw.url = $url,
                            tw.text = $text,
                            tw.likes = $likes,
                            tw.retweets = $retweets,
                            tw.timestamp = $timestamp,
                            tw.updated_at = timestamp()
                        """,
                        tweet_id=tweet['id'],
                        url=tweet.get('url'),
                        text=tweet.get('text'),
                        likes=tweet.get('likes', 0),
                        retweets=tweet.get('retweets', 0),
                        timestamp=tweet.get('timestamp')
                    )

                    # Upsert UserAccount node with all fields
                    session.run(
                        """
                        MERGE (ua:UserAccount {user_id: $user_id})
                        ON CREATE SET 
                            ua.username = $username,
                            ua.is_verified = $is_verified,
                            ua.is_blue_verified = $is_blue_verified,
                            ua.follower_count = $follower_count,
                            ua.account_age = $account_age,
                            ua.engagement_level = $engagement_level,
                            ua.total_tweets = $total_tweets,
                            ua.created_at = timestamp()
                        ON MATCH SET 
                            ua.username = $username,
                            ua.is_verified = $is_verified,
                            ua.is_blue_verified = $is_blue_verified,
                            ua.follower_count = $follower_count,
                            ua.account_age = $account_age,
                            ua.engagement_level = $engagement_level,
                            ua.total_tweets = $total_tweets,
                            ua.updated_at = timestamp()
                        """,
                        user_id=user_account['user_id'],
                        username=user_account.get('username'),
                        is_verified=user_account.get('is_verified', False),
                        is_blue_verified=user_account.get('is_blue_verified', False),
                        follower_count=user_account.get('follower_count', 0),
                        account_age=user_account.get('account_age', 0),
                        engagement_level=user_account.get('engagement_level', 0.0),
                        total_tweets=user_account.get('total_tweets', 0)
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

                    # Upsert relationships with unique variables
                    for edge in edges:
                        if edge['type'] == 'MENTIONS':
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (t:Token {name: $token_name})
                                MERGE (ua)-[mentions_rel:MENTIONS]->(t)
                                ON CREATE SET 
                                    mentions_rel.timestamp = $timestamp, 
                                    mentions_rel.hashtag_count = $hashtag_count
                                ON MATCH SET 
                                    mentions_rel.timestamp = $timestamp, 
                                    mentions_rel.hashtag_count = $hashtag_count
                                """,
                                user_id=user_account['user_id'],
                                token_name=token,
                                timestamp=edge['attributes']['timestamp'],
                                hashtag_count=edge['attributes'].get('hashtag_count', 0)
                            )
                        elif edge['type'] == 'POSTED':
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (tw:Tweet {id: $tweet_id})
                                MERGE (ua)-[posted_rel:POSTED]->(tw)
                                ON CREATE SET 
                                    posted_rel.timestamp = $timestamp, 
                                    posted_rel.likes = $likes
                                ON MATCH SET 
                                    posted_rel.timestamp = $timestamp, 
                                    posted_rel.likes = $likes
                                """,
                                user_id=user_account['user_id'],
                                tweet_id=tweet['id'],
                                timestamp=edge['attributes']['timestamp'],
                                likes=edge['attributes'].get('likes', 0)
                            )
                        elif edge['type'] == 'LOCATED_IN' and region.get('name') != "Unknown":
                            session.run(
                                """
                                MATCH (ua:UserAccount {user_id: $user_id}), (r:Region {name: $region_name})
                                MERGE (ua)-[located_in_rel:LOCATED_IN]->(r)
                                """,
                                user_id=user_account['user_id'],
                                region_name=region['name']
                            )
                        elif edge['type'] == 'MENTIONED_IN':
                            session.run(
                                """
                                MATCH (t:Token {name: $token_name}), (tw:Tweet {id: $tweet_id})
                                MERGE (t)-[mentioned_in_rel:MENTIONED_IN]->(tw)
                                """,
                                token_name=token,
                                tweet_id=tweet['id']
                            )

                logger.info(f"Successfully merged {len(dataset)} entries into the graph database.")
            except Exception as e:
                logger.error(f"Error merging data into Memgraph: {str(e)}")
