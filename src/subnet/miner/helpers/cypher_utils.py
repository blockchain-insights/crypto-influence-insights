from neo4j.graph import Node, Relationship

def escape_value(value):
    """Escapes single quotes in strings and formats other types."""
    if isinstance(value, str):
        return value.replace("'", "\\'")  # Escape single quotes in strings
    return value

def generate_cypher_from_results(results: list) -> str:
    """
    Converts query results into Cypher MERGE statements to avoid duplication.
    Args:
        results (list): A list of query results from Neo4j.
    Returns:
        str: A string of Cypher MERGE statements.
    """
    cypher_statements = set()  # Use a set to avoid duplicate relationships/nodes

    for record in results:
        # Create or update the Tweet node with deduplication
        if "t" in record and record["t"]:
            tweet = record["t"]
            tweet_props = ", ".join(f"{k}: '{escape_value(v)}'" for k, v in tweet.items() if v is not None)
            cypher_statements.add(
                f"MERGE (t:Tweet {{id: '{escape_value(tweet['id'])}'}}) "
                f"ON CREATE SET t += {{{tweet_props}}} "
                f"ON MATCH SET t += {{{tweet_props}}};"
            )

        # Create or update the Token node
        if "tok" in record and record["tok"]:
            token = record["tok"]
            token_props = ", ".join(f"{k}: '{escape_value(v)}'" for k, v in token.items() if v is not None)
            cypher_statements.add(
                f"MERGE (tok:Token {{name: '{escape_value(token['name'])}'}}) "
                f"ON CREATE SET tok += {{{token_props}}} "
                f"ON MATCH SET tok += {{{token_props}}};"
            )

        # Create or update the UserAccount node
        if "u" in record and record["u"]:
            user = record["u"]
            user_props = ", ".join(f"{k}: '{escape_value(v)}'" for k, v in user.items() if v is not None)
            cypher_statements.add(
                f"MERGE (u:UserAccount {{user_id: '{escape_value(user['user_id'])}'}}) "
                f"ON CREATE SET u += {{{user_props}}} "
                f"ON MATCH SET u += {{{user_props}}};"
            )

        # Create or update the Region node
        if "r" in record and record["r"]:
            region = record["r"]
            region_props = ", ".join(f"{k}: '{escape_value(v)}'" for k, v in region.items() if v is not None)
            cypher_statements.add(
                f"MERGE (r:Region {{name: '{escape_value(region['name'])}'}}) "
                f"ON CREATE SET r += {{{region_props}}} "
                f"ON MATCH SET r += {{{region_props}}};"
            )

        # Create relationships
        if "u" in record and "r" in record and record["u"] and record["r"]:
            cypher_statements.add(
                f"MERGE (u:UserAccount {{user_id: '{escape_value(record['u']['user_id'])}'}}) "
                f"-[:LOCATED_IN]-> "
                f"(r:Region {{name: '{escape_value(record['r']['name'])}'}});"
            )

        if "tok" in record and "t" in record and record["tok"] and record["t"]:
            cypher_statements.add(
                f"MERGE (tok:Token {{name: '{escape_value(record['tok']['name'])}'}}) "
                f"-[:MENTIONED_IN]-> "
                f"(t:Tweet {{id: '{escape_value(record['t']['id'])}'}});"
            )

        if "u" in record and "tok" in record and record["u"] and record["tok"]:
            cypher_statements.add(
                f"MERGE (u:UserAccount {{user_id: '{escape_value(record['u']['user_id'])}'}}) "
                f"-[:MENTIONS]-> "
                f"(tok:Token {{name: '{escape_value(record['tok']['name'])}'}});"
            )

        if "u" in record and "t" in record and record["u"] and record["t"]:
            likes = record["t"].get("likes", "null")
            timestamp = record["t"].get("timestamp", "null")
            cypher_statements.add(
                f"MERGE (u:UserAccount {{user_id: '{escape_value(record['u']['user_id'])}'}}) "
                f"-[:POSTED {{likes: {likes}, timestamp: '{escape_value(timestamp)}'}}]-> "
                f"(t:Tweet {{id: '{escape_value(record['t']['id'])}'}});"
            )

    # Return all Cypher statements joined by newline
    return "\n".join(cypher_statements)
