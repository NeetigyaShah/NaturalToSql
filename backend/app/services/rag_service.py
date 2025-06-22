import chromadb
from sentence_transformers import SentenceTransformer
import json
import decimal
import datetime
from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

class RAGService:
    def __init__(self):
        print("🔧 Initializing RAG Service...")
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(path="./chroma_db")
        
        # Create or get collection
        try:
            self.collection = self.client.get_collection("sql_knowledge")
            print("📚 Found existing knowledge base")
        except:
            self.collection = self.client.create_collection("sql_knowledge")
            print("📚 Created new knowledge base")
        
        # Initialize sentence transformer
        print("🤖 Loading sentence transformer model...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Populate knowledge base
        self.populate_knowledge_base()
    
    def populate_knowledge_base(self):
        """Populate vector DB with database knowledge"""
        
        # Check if already populated
        if self.collection.count() > 0:
            print("✅ Knowledge base already populated with", self.collection.count(), "items")
            return
        
        print("🔄 Populating knowledge base...")
        
        # Get dynamic schema information
        schema_info = self._get_schema_info()
        sample_data = self._get_sample_data()
        
        knowledge_items = []
        
        # Add schema information
        print("📊 Adding schema information...")
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
        print("📝 Adding sample data...")
        for table_name, samples in sample_data.items():
            if samples:
                try:
                    sample_str = json.dumps(samples[:3], default=str)
                    knowledge_items.append({
                        "id": f"{table_name}_samples",
                        "content": f"Sample data from {table_name} table: {sample_str}",
                        "metadata": {"type": "sample_data", "table": table_name}
                    })
                except Exception as e:
                    print(f"⚠️ Warning: Could not serialize sample data for {table_name}: {e}")
        
        # Add relationship information
        print("🔗 Adding table relationships...")
        knowledge_items.extend([
            {
                "id": "users_orders_relationship",
                "content": "users and orders tables are related through user_id. orders.user_id is a foreign key referencing users.id. To get user information with their orders, use JOIN: SELECT u.name, o.product FROM users u JOIN orders o ON u.id = o.user_id",
                "metadata": {"type": "relationship", "tables": "users,orders"}
            }
        ])
        
        # Add common query patterns
        print("🎯 Adding query patterns...")
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
            },
            {
                "id": "sorting",
                "content": "To sort results: SELECT * FROM table_name ORDER BY column_name ASC/DESC. For latest records: ORDER BY date_column DESC LIMIT 10",
                "metadata": {"type": "pattern", "intent": "sorting"}
            }
        ]
        
        knowledge_items.extend(query_patterns)
        
        # Add specific examples based on your data
        print("💡 Adding query examples...")
        examples = [
            {
                "id": "users_by_city",
                "content": "To find users from a specific city: SELECT * FROM users WHERE city = 'New York'. To find users from multiple cities: SELECT * FROM users WHERE city IN ('New York', 'Chicago')",
                "metadata": {"type": "example", "intent": "location_filter"}
            },
            {
                "id": "orders_by_amount",
                "content": "To find orders above certain amount: SELECT * FROM orders WHERE amount > 500. To find expensive orders with user info: SELECT u.name, o.product, o.amount FROM users u JOIN orders o ON u.id = o.user_id WHERE o.amount > 500",
                "metadata": {"type": "example", "intent": "amount_filter"}
            },
            {
                "id": "recent_orders",
                "content": "To find recent orders: SELECT * FROM orders ORDER BY order_date DESC LIMIT 10. To find orders from specific date: SELECT * FROM orders WHERE order_date >= '2024-01-01'",
                "metadata": {"type": "example", "intent": "recent_data"}
            },
            {
                "id": "user_order_summary",
                "content": "To get user order summary: SELECT u.name, COUNT(o.id) as order_count, SUM(o.amount) as total_spent FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name",
                "metadata": {"type": "example", "intent": "user_summary"}
            },
            {
                "id": "top_customers",
                "content": "To find top customers by spending: SELECT u.name, SUM(o.amount) as total_spent FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name ORDER BY total_spent DESC LIMIT 10",
                "metadata": {"type": "example", "intent": "top_customers"}
            },
            {
                "id": "age_filter",
                "content": "To filter users by age: SELECT * FROM users WHERE age > 25. To find users in age range: SELECT * FROM users WHERE age BETWEEN 25 AND 50",
                "metadata": {"type": "example", "intent": "age_filter"}
            }
        ]
        
        knowledge_items.extend(examples)
        
        # Add PostgreSQL specific tips
        print("🐘 Adding PostgreSQL tips...")
        postgres_tips = [
            {
                "id": "postgres_string_matching",
                "content": "For PostgreSQL string matching: Use LIKE for patterns (LIKE '%pattern%'), ILIKE for case-insensitive matching, or ~ for regex matching",
                "metadata": {"type": "tip", "intent": "string_matching"}
            },
            {
                "id": "postgres_date_functions",
                "content": "PostgreSQL date functions: Use CURRENT_DATE for today, EXTRACT(YEAR FROM date_column) for year, DATE_TRUNC('month', date_column) for month grouping",
                "metadata": {"type": "tip", "intent": "date_functions"}
            },
            {
                "id": "postgres_limits",
                "content": "Always use LIMIT in PostgreSQL for large result sets. For pagination, use LIMIT with OFFSET: SELECT * FROM table LIMIT 10 OFFSET 20",
                "metadata": {"type": "tip", "intent": "pagination"}
            }
        ]
        
        knowledge_items.extend(postgres_tips)
        
        try:
            # Prepare data for ChromaDB
            documents = [item["content"] for item in knowledge_items]
            metadatas = [item["metadata"] for item in knowledge_items]
            ids = [item["id"] for item in knowledge_items]
            
            # Validate and clean metadata
            cleaned_metadatas = []
            for metadata in metadatas:
                cleaned_metadata = {}
                for key, value in metadata.items():
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        cleaned_metadata[key] = value
                    elif isinstance(value, list):
                        cleaned_metadata[key] = ",".join(map(str, value))
                    else:
                        cleaned_metadata[key] = str(value)
                cleaned_metadatas.append(cleaned_metadata)
            
            # Add to ChromaDB
            self.collection.add(
                documents=documents,
                metadatas=cleaned_metadatas,
                ids=ids
            )
            
            print(f"✅ Added {len(knowledge_items)} items to knowledge base")
            
        except Exception as e:
            print(f"❌ Error adding to knowledge base: {e}")
            # Fallback: try adding items one by one
            print("🔄 Trying to add items individually...")
            success_count = 0
            for item in knowledge_items:
                try:
                    # Clean metadata for individual item
                    cleaned_metadata = {}
                    for key, value in item["metadata"].items():
                        if isinstance(value, (str, int, float, bool)) or value is None:
                            cleaned_metadata[key] = value
                        elif isinstance(value, list):
                            cleaned_metadata[key] = ",".join(map(str, value))
                        else:
                            cleaned_metadata[key] = str(value)
                    
                    self.collection.add(
                        documents=[item["content"]],
                        metadatas=[cleaned_metadata],
                        ids=[item["id"]]
                    )
                    success_count += 1
                except Exception as item_error:
                    print(f"⚠️ Failed to add item {item['id']}: {item_error}")
            
            print(f"✅ Successfully added {success_count} items individually")
    
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
            print(f"❌ Error getting schema: {e}")
            return {}
    
    def _get_sample_data(self):
        """Get sample data from each table"""
        try:
            engine = create_engine(settings.database_url)
            sample_data = {}
            
            with engine.connect() as conn:
                # Get sample from users
                try:
                    result = conn.execute(text("SELECT * FROM users LIMIT 3"))
                    sample_data["users"] = [self._convert_row_to_json(dict(row._mapping)) for row in result]
                except Exception as e:
                    print(f"⚠️ Could not get sample data from users: {e}")
                    sample_data["users"] = []
                
                # Get sample from orders
                try:
                    result = conn.execute(text("SELECT * FROM orders LIMIT 3"))
                    sample_data["orders"] = [self._convert_row_to_json(dict(row._mapping)) for row in result]
                except Exception as e:
                    print(f"⚠️ Could not get sample data from orders: {e}")
                    sample_data["orders"] = []
            
            return sample_data
        except Exception as e:
            print(f"❌ Error getting sample data: {e}")
            return {"users": [], "orders": []}
    
    def _convert_row_to_json(self, row):
        """Convert database row to JSON-serializable format"""
        converted = {}
        for key, value in row.items():
            if isinstance(value, decimal.Decimal):
                converted[key] = float(value)
            elif isinstance(value, datetime.date):
                converted[key] = value.isoformat()
            elif isinstance(value, datetime.datetime):
                converted[key] = value.isoformat()
            elif value is None:
                converted[key] = None
            else:
                converted[key] = value
        
        return converted
    
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
            print(f"🔍 Searching knowledge base for: '{query[:50]}...'")
            
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            context = []
            if results['documents'] and results['documents'][0]:
                for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                    context.append({
                        "content": doc,
                        "metadata": metadata
                    })
                
                print(f"✅ Found {len(context)} relevant context items")
            else:
                print("⚠️ No context found in knowledge base")
            
            return context
        except Exception as e:
            print(f"❌ Error retrieving context: {e}")
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
                documents=[f"Question: '{question}' generates SQL: {sql}"],
                metadatas=[{"type": "learned_example", "success": True}],
                ids=[query_id]
            )
            print(f"✅ Learned new query pattern from: '{question[:30]}...'")
        except Exception as e:
            print(f"❌ Error adding learned query: {e}")
    
    def get_knowledge_stats(self):
        """Get statistics about the knowledge base"""
        try:
            total_items = self.collection.count()
            
            # Get breakdown by type
            all_items = self.collection.get()
            type_counts = {}
            
            if all_items['metadatas']:
                for metadata in all_items['metadatas']:
                    item_type = metadata.get('type', 'unknown')
                    type_counts[item_type] = type_counts.get(item_type, 0) + 1
            
            return {
                "total_items": total_items,
                "breakdown": type_counts
            }
        except Exception as e:
            print(f"❌ Error getting knowledge stats: {e}")
            return {"total_items": 0, "breakdown": {}}

# Global instance
rag_service = RAGService()