from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class QueryRequest(BaseModel):
    natural_query: str

class QueryResponse(BaseModel):
    sql: str
    status: str
    error: Optional[str] = None

class QueryExecuteRequest(BaseModel):
    sql: str

class QueryExecuteResponse(BaseModel):
    results: list
    columns: list
    status: str
    error: Optional[str] = None