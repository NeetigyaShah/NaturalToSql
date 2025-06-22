from langchain_google_genai import ChatGoogleGenerativeAI
from app.services.rag_service import rag_service
from app.core.config import settings
import re

class EnhancedLLMService:
    def __init__(self):
        print("🚀 Initializing Enhanced LLM Service...")
        self.llm = self._setup_llm()
        self.rag = rag_service
        
        # Test LLM connection
        self.test_llm_connection()
        
        print("✅ Enhanced LLM Service initialized")
    
    def _setup_llm(self):
        """Setup LLM based on available API keys"""
        print(f"🔑 Checking API key: {settings.google_api_key[:20]}..." if settings.google_api_key else "🔑 No API key found")
        
        if settings.google_api_key and settings.google_api_key != "dummy-key-for-now":
            print("✅ Valid API key found, setting up Gemini...")
            try:
                # Try different model names in order of preference
                models_to_try = [
                    "gemini-1.5-flash",    # Latest and fastest
                    "gemini-1.5-pro",     # Latest pro version
                    "gemini-pro-latest",  # Fallback
                ]
                
                for model_name in models_to_try:
                    try:
                        print(f"🔄 Trying model: {model_name}")
                        llm = ChatGoogleGenerativeAI(
                            model=model_name,
                            temperature=0,
                            google_api_key=settings.google_api_key
                        )
                        
                        # Test the model with a simple request
                        test_response = llm.invoke("Say hello")
                        print(f"✅ Successfully connected to {model_name}")
                        print(f"✅ Test response: {test_response.content}")
                        return llm
                        
                    except Exception as model_error:
                        print(f"❌ Model {model_name} failed: {str(model_error)[:100]}...")
                        continue
                
                print("❌ All models failed")
                return None
                
            except Exception as e:
                print(f"❌ Error creating Gemini LLM: {e}")
                return None
        else:
            print("⚠️  Using dummy LLM - add real API key for AI functionality")
            return None
    
    def test_llm_connection(self):
        """Test if LLM is working"""
        print("🧪 Testing LLM connection...")
        
        if self.llm is None:
            print("❌ LLM is None - API key issue")
            return False
        
        try:
            print("🔄 Sending test message to Gemini...")
            response = self.llm.invoke("Say 'Hello, I am working!'")
            print(f"✅ LLM test response: '{response.content}'")
            return True
        except Exception as e:
            print(f"❌ LLM test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_sql(self, question: str, db_uri: str) -> str:
        """Generate SQL using RAG + Gemini"""
        print(f"🎯 Starting SQL generation for: '{question}'")
        
        try:
            # Check if LLM is available
            if self.llm is None:
                print("❌ LLM is None - no API key configured")
                return f"-- No API key configured\n-- Generated from: {question}\nSELECT * FROM users LIMIT 5;"
            
            print("✅ LLM is available, proceeding with RAG + Gemini")
            
            # Step 1: Retrieve relevant context using RAG
            print(f"🔍 Retrieving context for: {question}")
            context = self.rag.retrieve_context(question, top_k=3)
            print(f"📚 Retrieved {len(context)} context items")
            
            if len(context) > 0:
                print("📋 Context preview:")
                for i, item in enumerate(context[:2]):
                    print(f"   {i+1}. {item['content'][:100]}...")
            else:
                print("⚠️ No context retrieved from RAG")
            
            # Step 2: Build enhanced prompt with context
            prompt = self._build_rag_prompt(question, context)
            print(f"📝 Built prompt (length: {len(prompt)} chars)")
            print(f"📝 Prompt preview: {prompt[:200]}...")
            
            # Step 3: Generate SQL with Gemini
            print("🤖 Calling Gemini API...")
            response = self.llm.invoke(prompt)
            print(f"🤖 RAW Gemini response: '{response.content}'")
            print(f"🤖 Response type: {type(response.content)}")
            
            # Step 4: Clean and return SQL
            sql = self._clean_sql_response(response.content)
            print(f"✅ CLEANED SQL: '{sql}'")
            print(f"✅ SQL length: {len(sql)} chars")
            
            # Check if it's actually AI-generated or fallback
            if "Fallback query for:" in sql:
                print("⚠️ This is a FALLBACK query, not AI-generated!")
            else:
                print("🎉 This is AI-GENERATED SQL!")
            
            return sql
            
        except Exception as e:
            print(f"❌ EXCEPTION in generate_sql:")
            print(f"   Error: {str(e)}")
            print(f"   Type: {type(e).__name__}")
            import traceback
            print("📍 Full traceback:")
            traceback.print_exc()
            
            fallback = self._fallback_sql(question)
            print(f"🔄 Returning fallback: {fallback}")
            return fallback
    
    def _build_rag_prompt(self, question: str, context: list) -> str:
        """Build enhanced prompt with retrieved context"""
        print(f"🔨 Building prompt with {len(context)} context items")
        
        # Format context
        context_sections = []
        for item in context:
            context_sections.append(f"- {item['content']}")
        
        context_text = "\n".join(context_sections)
        
        prompt = f"""You are a PostgreSQL expert. Generate accurate SQL queries based on the provided database knowledge.

RELEVANT DATABASE KNOWLEDGE:
{context_text}

IMPORTANT RULES:
1. Return ONLY the SQL query, no explanations or markdown
2. Use proper PostgreSQL syntax
3. Include appropriate JOINs when querying multiple tables
4. Add LIMIT clause for SELECT * queries (typically LIMIT 10)
5. Use table aliases for better readability
6. For aggregations, use proper GROUP BY clauses
7. Use single quotes for string literals
8. End query with semicolon

USER QUESTION: {question}

SQL QUERY:"""
        
        print(f"✅ Prompt built successfully")
        return prompt
    
    def _clean_sql_response(self, response: str) -> str:
        """Clean SQL response from LLM"""
        print(f"🧹 Cleaning SQL response: '{response[:100]}...'")
        
        sql = response.strip()
        
        # Remove markdown formatting
        if "```sql" in sql:
            sql = sql.split("```sql")[1].split("```")[0].strip()
            print("🔧 Removed SQL markdown formatting")
        elif "```" in sql:
            sql = sql.split("```")[1].strip()
            print("🔧 Removed generic markdown formatting")
        
        # Remove extra explanations
        lines = sql.split('\n')
        sql_lines = []
        for line in lines:
            line = line.strip()
            if line and (not line.startswith('--') or line.startswith('-- ')):
                sql_lines.append(line)
        
        sql = '\n'.join(sql_lines)
        
        # Ensure it ends with semicolon
        if not sql.rstrip().endswith(';'):
            sql = sql.rstrip() + ';'
            print("🔧 Added semicolon")
        
        print(f"✅ SQL cleaned: '{sql}'")
        return sql
    
    # Replace your existing _fallback_sql method with this updated version:

    def _fallback_sql(self, question: str) -> str:
        """Generate fallback SQL when RAG/LLM fails"""
        print(f"🔄 Generating fallback SQL for: '{question}'")
        
        question_lower = question.lower()
        
        # Handle DROP TABLE operations
        if ("delete" in question_lower or "drop" in question_lower) and "table" in question_lower:
            if "all" in question_lower:
                fallback = """-- Drop all tables (CASCADE handles dependencies)
    DROP TABLE IF EXISTS orders CASCADE;
    DROP TABLE IF EXISTS users CASCADE;
    DROP TABLE IF EXISTS query_history CASCADE;"""
            else:
                fallback = "-- Example: DROP TABLE table_name CASCADE;\nSELECT 'Specify which table to drop' as message;"
        elif "users" in question_lower and "city" in question_lower:
            fallback = "SELECT * FROM users WHERE city = 'New York' LIMIT 10;"
        elif "orders" in question_lower and ("amount" in question_lower or "price" in question_lower):
            fallback = "SELECT * FROM orders WHERE amount > 100 ORDER BY amount DESC LIMIT 10;"
        elif "count" in question_lower and "users" in question_lower:
            fallback = "SELECT COUNT(*) as user_count FROM users;"
        elif "join" in question_lower or ("users" in question_lower and "orders" in question_lower):
            fallback = "SELECT u.name, o.product, o.amount FROM users u JOIN orders o ON u.id = o.user_id LIMIT 10;"
        elif "under" in question_lower and "age" in question_lower:
            # Handle age-related queries
            age_match = re.search(r'under\s+(\d+)', question_lower)
            if age_match:
                age = age_match.group(1)
                fallback = f"SELECT * FROM users WHERE age < {age} LIMIT 10;"
            else:
                fallback = "SELECT * FROM users WHERE age < 25 LIMIT 10;"
        else:
            fallback = f"-- Fallback query for: {question}\nSELECT * FROM users LIMIT 10;"
        
        print(f"📋 Generated fallback: {fallback}")
        return fallback
    def learn_from_query(self, question: str, sql: str, success: bool):
        """Learn from query execution results"""
        print(f"📚 Learning from query - Success: {success}")
        if success:
            print(f"✅ Adding successful query to knowledge base")
            self.rag.add_successful_query(question, sql)
        else:
            print("⚠️ Query was not successful, not learning")
    
    def get_llm_status(self):
        """Get current LLM status"""
        return {
            "llm_available": self.llm is not None,
            "api_key_configured": settings.google_api_key != "dummy-key-for-now",
            "rag_available": self.rag is not None
        }

# Global instance
enhanced_llm_service = EnhancedLLMService()