from neo4j.graph import Node, Relationship

def generate_cypher_from_results(results: list) -> str:
    """
    Converts query results into Cypher CREATE statements.

    Args:
        results (list): A list of query results from Neo4j.

    Returns:
        str: A string of Cypher CREATE statements.
    """
    cypher_statements = []
    for record in results:
        for key, value in record.items():
            if isinstance(value, Node):
                labels = ":".join(value["labels"])
                props = ", ".join(f"{k}: '{v}'" for k, v in value["properties"].items())
                cypher_statements.append(f"CREATE ({key}:{labels} {{{props}}});")
            elif isinstance(value, Relationship):
                props = ", ".join(f"{k}: '{v}'" for k, v in value["properties"].items())
                cypher_statements.append(
                    f"CREATE ({value['start']})-[:{value['label']} {{{props}}}]->({value['end']});"
                )
    return "\n".join(cypher_statements)
