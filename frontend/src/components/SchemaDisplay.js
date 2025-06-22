import React, { useState } from 'react';
import { Database, RefreshCw, Terminal } from 'lucide-react';

const SchemaDisplay = ({ schema, setSchema, setError }) => {
  const [loading, setLoading] = useState(false);
  const [customSql, setCustomSql] = useState('');
  const [sqlResult, setSqlResult] = useState(null);
  const [showCustomSql, setShowCustomSql] = useState(false);

  // FIXED: Direct fetch call instead of sqlApi
  const reloadSchema = async () => {
    setLoading(true);
    try {
      console.log('Calling reload schema...');
      const response = await fetch('http://localhost:8000/api/schema/reload');
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Reload response:', data);
      
      if (data.success) {
        const schemaObj = data.tables.reduce((acc, table) => {
          acc[table.name] = table.columns;
          return acc;
        }, {});
        
        setSchema(schemaObj);
        setError('');
        alert(`✅ Schema reloaded! Found ${data.tables.length} tables.`);
      } else {
        const errorMsg = data.message || 'Failed to reload schema';
        setError(errorMsg);
        alert('❌ ' + errorMsg);
      }
    } catch (error) {
      console.error('Reload schema error:', error);
      const errorMsg = 'Failed to reload schema: ' + error.message;
      setError(errorMsg);
      alert('❌ ' + errorMsg);
    } finally {
      setLoading(false);
    }
  };

  // FIXED: Direct fetch call instead of sqlApi
  const executeCustomSql = async () => {
    if (!customSql.trim()) return;
    
    setLoading(true);
    setSqlResult(null);
    
    try {
      console.log('Executing SQL:', customSql);
      const response = await fetch('http://localhost:8000/api/execute-custom-sql', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sql: customSql })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('SQL execution response:', data);
      setSqlResult(data);
      
      // If schema-changing operation, reload schema
      const sqlUpper = customSql.toUpperCase();
      if (sqlUpper.includes('CREATE TABLE') || 
          sqlUpper.includes('DROP TABLE') ||
          sqlUpper.includes('ALTER TABLE')) {
        setTimeout(() => {
          reloadSchema();
        }, 1000);
      }
    } catch (error) {
      console.error('SQL execution error:', error);
      setSqlResult({ success: false, error: error.message });
    } finally {
      setLoading(false);
    }
  };

  const clearSql = () => {
    setCustomSql('');
    setSqlResult(null);
  };

  const insertSampleSql = (sql) => {
    setCustomSql(sql);
  };

  return (
    <>
      {/* Enhanced Header */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '20px',
        padding: '15px',
        backgroundColor: '#f8f9fa',
        borderRadius: '8px'
      }}>
        <h3 style={{ margin: 0, color: '#333' }}>📊 Database Schema</h3>
        <div>
          <button 
            onClick={() => setShowCustomSql(!showCustomSql)}
            style={{ 
              marginRight: '10px', 
              padding: '8px 16px', 
              backgroundColor: '#28a745', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px'
            }}
          >
            <Terminal size={16} />
            {showCustomSql ? 'Hide SQL' : 'Custom SQL'}
          </button>
          <button 
            onClick={reloadSchema}
            disabled={loading}
            style={{ 
              padding: '8px 16px', 
              backgroundColor: loading ? '#6c757d' : '#007bff', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px'
            }}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            {loading ? 'Loading...' : 'Reload'}
          </button>
        </div>
      </div>

      {/* Custom SQL Panel */}
      {showCustomSql && (
        <div style={{ 
          marginBottom: '25px', 
          padding: '20px', 
          backgroundColor: '#f8f9fa', 
          borderRadius: '8px',
          border: '1px solid #dee2e6'
        }}>
          <h4 style={{ marginTop: 0, color: '#495057' }}>⚡ Execute Custom PostgreSQL Commands</h4>
          
          {/* Sample SQL Buttons */}
          <div style={{ marginBottom: '15px' }}>
            <h5>Quick Examples:</h5>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              <button 
                onClick={() => insertSampleSql('CREATE TABLE products (\n    id SERIAL PRIMARY KEY,\n    name VARCHAR(100) NOT NULL,\n    price NUMERIC(10,2),\n    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n);')}
                style={{ padding: '5px 10px', fontSize: '12px', backgroundColor: '#17a2b8', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer' }}
              >
                Create Products Table
              </button>
              <button 
                onClick={() => insertSampleSql('INSERT INTO users (name, email, age, city) VALUES (\'Test User\', \'test@example.com\', 25, \'Boston\');')}
                style={{ padding: '5px 10px', fontSize: '12px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer' }}
              >
                Insert Sample User
              </button>
              <button 
                onClick={() => insertSampleSql('SELECT * FROM users LIMIT 5;')}
                style={{ padding: '5px 10px', fontSize: '12px', backgroundColor: '#6f42c1', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer' }}
              >
                View Users
              </button>
              <button 
                onClick={() => insertSampleSql('DROP TABLE IF EXISTS products CASCADE;')}
                style={{ padding: '5px 10px', fontSize: '12px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer' }}
              >
                Drop Table
              </button>
            </div>
          </div>

          <textarea
            value={customSql}
            onChange={(e) => setCustomSql(e.target.value)}
            placeholder="Enter your PostgreSQL commands here...

Examples:
• CREATE TABLE customers (id SERIAL PRIMARY KEY, name VARCHAR(100));
• INSERT INTO users (name, email) VALUES ('John', 'john@example.com');
• SELECT * FROM users WHERE age > 25;
• UPDATE users SET city = 'Boston' WHERE id = 1;
• DROP TABLE products CASCADE;"
            style={{ 
              width: '100%', 
              height: '150px', 
              padding: '12px', 
              fontFamily: 'Consolas, Monaco, monospace',
              fontSize: '14px',
              border: '1px solid #ced4da',
              borderRadius: '4px',
              resize: 'vertical'
            }}
          />
          
          <div style={{ marginTop: '12px', display: 'flex', gap: '10px' }}>
            <button 
              onClick={executeCustomSql}
              disabled={loading || !customSql.trim()}
              style={{ 
                padding: '10px 20px', 
                backgroundColor: loading || !customSql.trim() ? '#6c757d' : '#fd7e14', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px',
                cursor: loading || !customSql.trim() ? 'not-allowed' : 'pointer',
                fontWeight: 'bold'
              }}
            >
              {loading ? '⏳ Executing...' : '🚀 Execute SQL'}
            </button>
            
            <button 
              onClick={clearSql}
              style={{ 
                padding: '10px 20px', 
                backgroundColor: '#6c757d', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              🗑️ Clear
            </button>
          </div>

          {/* SQL Results */}
          {sqlResult && (
            <div style={{ 
              marginTop: '20px', 
              padding: '15px', 
              backgroundColor: sqlResult.success ? '#d1edff' : '#f8d7da', 
              border: `1px solid ${sqlResult.success ? '#bee5eb' : '#f5c6cb'}`,
              borderRadius: '4px'
            }}>
              {sqlResult.success ? (
                <div>
                  <h5 style={{ margin: '0 0 10px 0', color: '#155724' }}>✅ Success!</h5>
                  {sqlResult.type === 'select' ? (
                    <div>
                      <p style={{ margin: '5px 0', fontWeight: 'bold' }}>
                        📊 Found {sqlResult.row_count} rows
                      </p>
                      {sqlResult.data && sqlResult.data.length > 0 && (
                        <pre style={{ 
                          backgroundColor: 'white', 
                          padding: '10px', 
                          borderRadius: '4px', 
                          overflow: 'auto',
                          maxHeight: '300px',
                          fontSize: '12px'
                        }}>
                          {JSON.stringify(sqlResult.data.slice(0, 10), null, 2)}
                        </pre>
                      )}
                    </div>
                  ) : (
                    <p style={{ margin: '5px 0', color: '#155724' }}>
                      {sqlResult.message}
                    </p>
                  )}
                </div>
              ) : (
                <div>
                  <h5 style={{ margin: '0 0 10px 0', color: '#721c24' }}>❌ Error</h5>
                  <p style={{ margin: '5px 0', color: '#721c24' }}>
                    {sqlResult.error}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Schema Display */}
      {schema ? (
        <div className="schema-container">
          {Object.entries(schema).map(([tableName, columns]) => (
            <div key={tableName} className="table-schema">
              <h4>{tableName}</h4>
              <div className="columns">
                {columns.map((col, i) => (
                  <div key={i} className="column">
                    <span className="column-name">{col.name}</span>
                    <span className="column-type">{col.type}</span>
                    {!col.nullable && <span className="not-null">NOT NULL</span>}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <Database size={48} />
          <p>Loading schema...</p>
        </div>
      )}
    </>
  );
};

export default SchemaDisplay;