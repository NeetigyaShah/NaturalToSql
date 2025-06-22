import chromadb
from sentence_transformers import SentenceTransformer
import json
from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

class RAGService:
    def __init__(self):
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Create or get collection
        try:
            self.collection = self.client.get_collection("sql_knowledge")
        except:
            self.collection = self.client.create_collection("sql_knowledge")
        
        # Initialize sentence transformer
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Populate knowledge base
        self.populate_knowledge_base()
    
    def populate_knowledge_base(self):
        """Populate vector DB with database knowledge"""
        
        # Check if already populated
        if self.collection.count() > 0:
            print("✅ Knowledge base already populated")
            return
        
        print("🔄 Populating knowledge base...")
        
        # Get dynamic schema information
        schema_info = self._get_schema_info()
        sample_data = self._get_sample_data()
        
        knowledge_items = []
        
        # Add schema information
        for table_name, columns in schema_info.items():
            column_details = []
            for col in columns:
                col_desc = f"{col['name']} ({col['type']}"
                if not col['nullable']:
                    col_desc += ", NOT NULL"
                if col['name'] == 'id':
                    col_desc += ", PRIMARY KEY"
                col_desc += ")"
                column_details.append(col_desc)
            
            knowledge_items.append({
                "id": f"{table_name}_schema",
                "content": f"{table_name} table contains columns: {', '.join(column_details)}. This table is used for storing {self._get_table_description(table_name)}.",
                "metadata": {"type": "schema", "table": table_name}
            })
        
        # Add sample data context
        for table_name, samples in sample_data.items():
            if samples:
                sample_str = json.dumps(samples[:3])  # First 3 rows
                knowledge_items.append({
                    "id": f"{table_name}_samples",
                    "content": f"Sample data from {table_name} table: {sample_str}",
                    "metadata": {"type": "sample_data", "table": table_name}
                })
        
        # Add relationship information
        knowledge_items.extend([
            {
                "id": "users_orders_relationship",
                "content": "users and orders tables are related through user_id. orders.user_id is a foreign key referencing users.id. To get user information with their orders, use JOIN: SELECT u.name, o.product FROM users u JOIN orders o ON u.id = o.user_id",
                "metadata": {"type": "relationship", "tables": ["users", "orders"]}
            }
        ])
        
        # Add common query patterns
        query_patterns = [
            {
                "id": "basic_select",
                "content": "To show all records from a table: SELECT * FROM table_name LIMIT 10",
                "metadata": {"type": "pattern", "intent": "basic_select"}
            },
            {
                "id": "filter_by_column",
                "content": "To filter records by a column value: SELECT * FROM table_name WHERE column_name = 'value'",
                "metadata": {"type": "pattern", "intent": "filter"}
            },
            {
                "id": "count_records",
                "content": "To count records: SELECT COUNT(*) FROM table_name. To count by group: SELECT column_name, COUNT(*) FROM table_name GROUP BY column_name",
                "metadata": {"type": "pattern", "intent": "count"}
            },
            {
                "id": "join_tables",
                "content": "To join users with orders: SELECT u.name, u.email, o.product, o.amount FROM users u JOIN orders o ON u.id = o.user_id",
                "metadata": {"type": "pattern", "intent": "join"}
            },
            {
                "id": "aggregation",
                "content": "For aggregations like sum, average: SELECT SUM(amount) as total, AVG(amount) as average FROM orders. Group by user: SELECT u.name, SUM(o.amount) as total FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name",
                "metadata": {"type": "pattern", "intent": "aggregation"}
            }
        ]
        
        knowledge_items.extend(query_patterns)
        
        # Add specific examples based on your data
        examples = [
            {
                "id": "users_by_city",
                "content": "To find users from a specific city: SELECT * FROM users WHERE city = 'New York'. Available cities include: New York, Los Angeles, Chicago",
                "metadata": {"type": "example", "intent": "location_filter"}
            },
            {
                "id": "orders_by_amount",
                "content": "To find orders above certain amount: SELECT * FROM orders WHERE amount > 500. To find expensive orders with user info: SELECT u.name, o.product, o.amount FROM users u JOIN orders o ON u.id = o.user_id WHERE o.amount > 500",
                "metadata": {"type": "example", "intent": "amount_filter"}
            },
            {
                "id": "recent_orders",
                "content": "To find recent orders: SELECT * FROM orders ORDER BY order_date DESC LIMIT 10",
                "metadata": {"type": "example", "intent": "recent_data"}
            }
        ]
        
        knowledge_items.extend(examples)
        
        # Add all items to vector database
        documents = [item["content"] for item in knowledge_items]
        metadatas = [item["metadata"] for item in knowledge_items]
        ids = [item["id"] for item in knowledge_items]
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"✅ Added {len(knowledge_items)} items to knowledge base")
    
    def _get_schema_info(self):
        """Get schema information from database"""
        try:
            engine = create_engine(settings.database_url)
            inspector = inspect(engine)
            
            schema_info = {}
            for table_name in inspector.get_table_names():
                columns = inspector.get_columns(table_name)
                schema_info[table_name] = columns
            
            return schema_info
        except Exception as e:
            print(f"Error getting schema: {e}")
            return {}
    
    def _get_sample_data(self):
        """Get sample data from each table"""
        try:
            engine = create_engine(settings.database_url)
            sample_data = {}
            
            with engine.connect() as conn:
                # Get sample from users
                result = conn.execute(text("SELECT * FROM users LIMIT 3"))
                sample_data["users"] = [dict(row._mapping) for row in result]
                
                # Get sample from orders
                result = conn.execute(text("SELECT * FROM orders LIMIT 3"))
                sample_data["orders"] = [dict(row._mapping) for row in result]
            
            return sample_data
        except Exception as e:
            print(f"Error getting sample data: {e}")
            return {}
    
    def _get_table_description(self, table_name):
        """Get description for table"""
        descriptions = {
            "users": "customer information including personal details and location",
            "orders": "purchase records with product details and amounts",
            "query_history": "system log of generated SQL queries"
        }
        return descriptions.get(table_name, "data records")
    
    def retrieve_context(self, query: str, top_k: int = 5):
        """Retrieve relevant context for user query"""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            context = []
            for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                context.append({
                    "content": doc,
                    "metadata": metadata
                })
            
            return context
        except Exception as e:
            print(f"Error retrieving context: {e}")
            return []
    
    def add_successful_query(self, question: str, sql: str):
        """Learn from successful queries"""
        try:
            query_id = f"learned_{hash(question + sql)}"
            
            # Check if already exists
            try:
                existing = self.collection.get(ids=[query_id])
                if existing['ids']:
                    return  # Already learned this query
            except:
                pass
            
            self.collection.add(
                documents=[f"Question: '{question}' -> SQL: {sql}"],
                metadatas=[{"type": "learned_example", "success": True}],
                ids=[query_id]
            )
            print(f"✅ Learned new query pattern")
        except Exception as e:
            print(f"Error adding learned query: {e}")

# Global instance
rag_service = RAGService()