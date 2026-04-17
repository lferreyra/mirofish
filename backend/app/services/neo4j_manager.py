import os
from neo4j import GraphDatabase, SessionExpired,

class Neo4jManager:
    def __init__(self, uri, user, password):
        self.uri = uri
        self.user = user
        self.password = password
        self._driver = None

    def connect(self):
        if self._driver is None:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self):
        if self._driver is not None:
            self._driver.close()

    def execute_with_retry(self, query, parameters=None, retries=3):
        self.connect()
        with self._driver.session() as session:
            for attempt in range(retries):
                try:
                    result = session.run(query, parameters)
                    return result.data()  # Or process as required
                except SessionExpired:
                    if attempt < retries - 1:
                        self.connect()  # Re-establish connection on expiry
                    else:
                        raise  # Reraise last exception

# Usage Example:
# neo4j_manager = Neo4jManager(uri="neo4j://localhost:7687", user="neo4j", password="password")
# result = neo4j_manager.execute_with_retry("MATCH (n) RETURN n", {})