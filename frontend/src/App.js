import React, { useState, useEffect } from 'react';
import SchemaDisplay from './components/SchemaDisplay';
import { Send, Database, Play, Table, Loader2 } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { sqlApi } from './services/api';
import './App.css';

function App() {
  const [naturalQuery, setNaturalQuery] = useState('');
  const [generatedSql, setGeneratedSql] = useState('');
  const [queryResults, setQueryResults] = useState(null);
  const [schema, setSchema] = useState(null);
  const [activeTab, setActiveTab] = useState('query');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

// Replace the useEffect and loadSchema function
useEffect(() => {
  // Add a small delay to ensure backend is ready
  const timer = setTimeout(() => {
    loadSchema();
  }, 1000);
  
  return () => clearTimeout(timer);
}, []);

const loadSchema = async () => {
  try {
    console.log('Loading schema...');
    const response = await sqlApi.getSchema();
    console.log('Schema response:', response);
    
    if (response && response.schema) {
      setSchema(response.schema);
      console.log('Schema loaded successfully');
    } else {
      console.warn('No schema data in response');
      setSchema({});
    }
  } catch (err) {
    console.error('Failed to load schema:', err.message);
    setError(`Schema loading failed: ${err.message}`);
    setSchema({});
  }
};

  const handleGenerateSql = async () => {
    if (!naturalQuery.trim()) return;
    
    setIsLoading(true);
    setError('');
    try {
      const response = await sqlApi.generateSql(naturalQuery);
      if (response.status === 'success') {
        setGeneratedSql(response.sql);
        setActiveTab('sql');
      } else {
        setError(response.error || 'Failed to generate SQL');
      }
    } catch (err) {
      setError('Failed to connect to server');
    } finally {
      setIsLoading(false);
    }
  };

  const handleExecuteSql = async () => {
    if (!generatedSql.trim()) return;
    
    setIsLoading(true);
    setError('');
    try {
      const response = await sqlApi.executeSql(generatedSql);
      if (response.status === 'success') {
        setQueryResults(response);
        setActiveTab('results');
      } else {
        setError(response.error || 'Failed to execute SQL');
      }
    } catch (err) {
      setError('Failed to execute query');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      handleGenerateSql();
    }
  };
  
const testConnection = async () => {
  try {
    const response = await fetch('http://localhost:8000/');
    const data = await response.json();
    console.log('Connection test:', data);
    return true;
  } catch (err) {
    console.error('Connection test failed:', err);
    return false;
  }
};

// REPLACE the existing useEffect with this:
useEffect(() => {
  const initializeApp = async () => {
    console.log('Testing backend connection...');
    const isConnected = await testConnection();
    
    if (isConnected) {
      console.log('Backend connected, loading schema...');
      loadSchema();
    } else {
      setError('Cannot connect to backend server. Make sure it\'s running on port 8000.');
    }
  };
  
  initializeApp();
}, []);


  return (
    <div className="app">
      <div className="header">
        <div className="header-content">
          <div className="logo">
            <Database className="logo-icon" />
            <h1>NaturaltoSQL</h1>
          </div>
          <p className="subtitle">AI-Powered SQL Query Generator</p>
        </div>
      </div>

      <div className="main-content">
        {/* Query Input Section */}
        <div className="query-section">
          <div className="input-container">
            <textarea
              value={naturalQuery}
              onChange={(e) => setNaturalQuery(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Describe what you want to query in natural language...
Example: 'Show me all users from New York' or 'Find orders over $500'"
              className="query-input"
              rows={4}
            />
            <button 
              onClick={handleGenerateSql}
              disabled={isLoading || !naturalQuery.trim()}
              className="generate-btn"
            >
              {isLoading ? <Loader2 className="spin" /> : <Send />}
              Generate SQL
            </button>
          </div>
          
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="tabs">
          <button 
            className={`tab ${activeTab === 'query' ? 'active' : ''}`}
            onClick={() => setActiveTab('query')}
          >
            <Send size={16} />
            Query
          </button>
          <button 
            className={`tab ${activeTab === 'sql' ? 'active' : ''}`}
            onClick={() => setActiveTab('sql')}
          >
            <Database size={16} />
            Generated SQL
          </button>
          <button 
            className={`tab ${activeTab === 'results' ? 'active' : ''}`}
            onClick={() => setActiveTab('results')}
          >
            <Table size={16} />
            Results
          </button>
          <button 
            className={`tab ${activeTab === 'schema' ? 'active' : ''}`}
            onClick={() => setActiveTab('schema')}
          >
            <Database size={16} />
            Schema
          </button>
        </div>

        {/* Content Panels */}
        <div className="content-panel">
          {activeTab === 'query' && (
            <div className="panel">
              <h3>Welcome to NaturaltoSQL</h3>
              <p>Enter your query above in plain English to get started.</p>
              <div className="examples">
                <h4>Example Queries:</h4>
                <ul>
                  <li>"Show me all users"</li>
                  <li>"Find users older than 25"</li>
                  <li>"Get all orders from last month"</li>
                  <li>"Show me the total sales by product"</li>
                </ul>
              </div>
            </div>
          )}

          {activeTab === 'sql' && (
            <div className="panel">
              <div className="sql-header">
                <h3>Generated SQL</h3>
                {generatedSql && (
                  <button 
                    onClick={handleExecuteSql}
                    disabled={isLoading}
                    className="execute-btn"
                  >
                    {isLoading ? <Loader2 className="spin" /> : <Play />}
                    Execute Query
                  </button>
                )}
              </div>
              {generatedSql ? (
                <SyntaxHighlighter 
                  language="sql" 
                  style={vscDarkPlus}
                  customStyle={{
                    background: '#1e1e1e',
                    borderRadius: '8px',
                    padding: '16px'
                  }}
                >
                  {generatedSql}
                </SyntaxHighlighter>
              ) : (
                <div className="empty-state">
                  <Database size={48} />
                  <p>Generate a SQL query first</p>
                </div>
              )}
            </div>
          )}

          {activeTab === 'results' && (
            <div className="panel">
              <h3>Query Results</h3>
              {queryResults ? (
                <div className="results-container">
                  <div className="results-info">
                    <span>{queryResults.results.length} rows returned</span>
                  </div>
                  <div className="table-container">
                    <table className="results-table">
                      <thead>
                        <tr>
                          {queryResults.columns.map((col, i) => (
                            <th key={i}>{col}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {queryResults.results.map((row, i) => (
                          <tr key={i}>
                            {queryResults.columns.map((col, j) => (
                              <td key={j}>{row[col]}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="empty-state">
                  <Table size={48} />
                  <p>Execute a SQL query to see results</p>
                </div>
              )}
            </div>
          )}

        {activeTab === 'schema' && (
            <div className="panel">
                <SchemaDisplay 
                  schema={schema} 
                  setSchema={setSchema} 
                  setError={setError} 
                />
            </div>
        )}
        </div>
      </div>
    </div>
  );
}

export default App;