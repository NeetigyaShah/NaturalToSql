from sqlalchemy import create_engine, text
from app.core.config import settings

def create_sample_tables():
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Create sample tables for testing
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100),
                age INTEGER,
                city VARCHAR(50)
            );
        """))
        
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                product VARCHAR(100),
                amount DECIMAL(10,2),
                order_date DATE
            );
        """))
        
        # Insert sample data
        conn.execute(text("""
            INSERT INTO users (name, email, age, city) VALUES
            ('John Doe', 'john@email.com', 25, 'New York'),
            ('Jane Smith', 'jane@email.com', 30, 'Los Angeles'),
            ('Bob Johnson', 'bob@email.com', 35, 'Chicago')
            ON CONFLICT DO NOTHING;
        """))
        
        conn.execute(text("""
            INSERT INTO orders (user_id, product, amount, order_date) VALUES
            (1, 'Laptop', 999.99, '2024-01-15'),
            (2, 'Phone', 599.99, '2024-01-16'),
            (1, 'Mouse', 29.99, '2024-01-17')
            ON CONFLICT DO NOTHING;
        """))
        
        conn.commit()
        print("✅ Sample tables and data created!")

if __name__ == "__main__":
    create_sample_tables()