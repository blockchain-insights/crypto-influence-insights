from src.subnet.validator._config import ValidatorSettings
from neo4j import WRITE_ACCESS, GraphDatabase
from neo4j.exceptions import Neo4jError
from neo4j.graph import Node, Relationship


class GraphSearch:
    # Define prohibited clauses to prevent data modification
    MODIFICATION_CLAUSES = {"CREATE", "DELETE", "SET", "MERGE", "REMOVE"}

    def __init__(self, settings: ValidatorSettings):
        self.driver = GraphDatabase.driver(
            settings.GRAPH_DB_URL,
            auth=(settings.GRAPH_DB_USER, settings.GRAPH_DB_PASSWORD),
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

    def close(self):
        """
        Closes the Neo4j driver connection.
        """
        self.driver.close()