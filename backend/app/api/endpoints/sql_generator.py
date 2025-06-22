from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from app.core.config import settings
from app.schemas.query import QueryRequest, QueryResponse, QueryExecuteRequest, QueryExecuteResponse
from app.services.llm_service import enhanced_llm_service
from app.db.database import get_db, get_db_uri, engine
from app.db.models import QueryHistory
import pandas as pd

router = APIRouter()

@router.post("/generate-sql", response_model=QueryResponse)
async def generate_sql_endpoint(request: QueryRequest, db: Session = Depends(get_db)):
    try:
        # Generate SQL using RAG + LLM
        sql = enhanced_llm_service.generate_sql(request.natural_query, get_db_uri())
        
        # Save to history
        history = QueryHistory(
            natural_query=request.natural_query,
            generated_sql=sql,
            status="success"
        )
        db.add(history)
        db.commit()
        
        return QueryResponse(sql=sql, status="success")
    
    except Exception as e:
        print(f"SQL Generation Error: {str(e)}")
        return QueryResponse(sql="", status="error", error=str(e))

@router.post("/execute-sql", response_model=QueryExecuteResponse)
async def execute_sql_endpoint(request: QueryExecuteRequest):
    try:
        # Execute SQL and return results
        df = pd.read_sql(request.sql, engine)
        results = df.to_dict('records')
        columns = df.columns.tolist()
        
        return QueryExecuteResponse(
            results=results,
            columns=columns,
            status="success"
        )
    
    except Exception as e:
        print(f"SQL Execution Error: {str(e)}")
        return QueryExecuteResponse(
            results=[],
            columns=[],
            status="error",
            error=str(e)
        )

@router.get("/schema")
async def get_schema():
    """Get database schema information"""
    try:
        inspector = inspect(engine)
        
        schema_info = {}
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            schema_info[table_name] = [
                {
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"]
                }
                for col in columns
            ]
        
        return {"schema": schema_info, "status": "success"}
    
    except Exception as e:
        return {"schema": {}, "status": "error", "error": str(e)}

@router.get("/schema/reload")
async def reload_schema():
    """Reload database schema"""
    try:
        # Import here to avoid circular imports
        from app.services.rag_service import rag_service
        
        # Clear and repopulate knowledge base
        try:
            rag_service.populate_knowledge_base()
        except Exception as e:
            print(f"Warning: Could not refresh knowledge base: {e}")
        
        # Get fresh schema info
        engine_local = create_engine(settings.database_url)
        inspector = inspect(engine_local)
        
        schema_info = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            schema_info.append({
                "name": table_name,
                "columns": [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "primary_key": col.get("primary_key", False)
                    }
                    for col in columns
                ]
            })
        
        return {
            "success": True,
            "message": f"Schema reloaded successfully. Found {len(schema_info)} tables.",
            "tables": schema_info
        }
    except Exception as e:
        print(f"Schema reload error: {e}")
        raise HTTPException(status_code=500, detail=f"Schema reload failed: {str(e)}")

@router.post("/execute-custom-sql")
async def execute_custom_sql(request: dict):
    """Execute custom PostgreSQL commands"""
    try:
        sql_query = request.get("sql", "").strip()
        
        if not sql_query:
            raise HTTPException(status_code=400, detail="SQL query is required")
        
        # Security check
        dangerous_keywords = ["DROP DATABASE", "CREATE DATABASE", "ALTER SYSTEM"]
        sql_upper = sql_query.upper()
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise HTTPException(status_code=403, detail=f"Command '{keyword}' is not allowed")
        
        engine_local = create_engine(settings.database_url)
        
        with engine_local.connect() as conn:
            if sql_upper.strip().startswith("SELECT"):
                # SELECT query
                result = conn.execute(text(sql_query))
                rows = result.fetchall()
                columns = list(result.keys()) if rows else []
                
                data = []
                for row in rows:
                    row_dict = {}
                    for i, col in enumerate(columns):
                        value = row[i]
                        # Handle datetime and decimal types
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        elif hasattr(value, '__float__'):
                            value = float(value)
                        row_dict[col] = value
                    data.append(row_dict)
                
                return {
                    "success": True,
                    "type": "select",
                    "columns": columns,
                    "data": data,
                    "row_count": len(data)
                }
            else:
                # Non-SELECT query
                result = conn.execute(text(sql_query))
                conn.commit()
                
                return {
                    "success": True,
                    "type": "modification",
                    "message": f"Query executed successfully. Rows affected: {result.rowcount if hasattr(result, 'rowcount') else 'N/A'}",
                    "rows_affected": result.rowcount if hasattr(result, 'rowcount') else None
                }
                
    except Exception as e:
        print(f"SQL execution error: {e}")
        raise HTTPException(status_code=500, detail=f"SQL execution failed: {str(e)}")