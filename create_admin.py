import sys
import psycopg2
from app.core.security import hash_password
from app.core.config import settings
from urllib.parse import urlparse

def create_admin_user(username: str, password: str) -> bool:
    try:
        db_url = urlparse(settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
        
        conn = psycopg2.connect(
            host=db_url.hostname or "localhost",
            port=db_url.port or 5432,
            user=db_url.username or "postgres",
            password=db_url.password or "postgres",
            database=db_url.path.lstrip("/") or "postgres"
        )
        
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"Error: User '{username}' already exists")
            cursor.close()
            conn.close()
            return False
        
        hashed_password = hash_password(password)
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) RETURNING id",
            (username, hashed_password, "ADMIN")
        )
        
        user_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"Admin user '{username}' created successfully")
        print(f"User ID: {user_id}")
        print(f"Role: admin")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        return False


def main():
    if len(sys.argv) < 3:
        print("Usage: python create_admin.py <username> <password>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    
    if not username or not password:
        print("Error: username and password cannot be empty")
        sys.exit(1)
    
    success = create_admin_user(username, password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
