from fastapi import FastAPI, WebSocket, Depends, HTTPException, Header
from passlib.context import CryptContext
import asyncpg
import uvicorn
from typing import Optional

app = FastAPI()

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Database connection pool
# DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"
DATABASE_URL = "postgresql://postgres:postgres_pass@localhost:5432/dexter"

db_pool: Optional[asyncpg.Pool] = None

async def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
    return db_pool

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                content TEXT NOT NULL,
                user_id INTEGER REFERENCES users(id)
            );
        ''')

@app.post("/register")
async def register(
    x_username: str = Header(..., alias="X-Username"),
    x_password: str = Header(..., alias="X-Password")
):    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow('SELECT * FROM users WHERE username = $1', x_username)
        if user:
            print(f"Username {x_username} exists, will try to login")
            return {"msg": "User already exists", "user_id": user['id']}

        hashed_password = pwd_context.hash(x_password)
        await conn.execute('''
            INSERT INTO users (username, password)
            VALUES ($1, $2)
        ''', x_username, hashed_password)
    
    return {"msg": "User registered successfully!"}

@app.post("/login")
async def login(
    x_username: str = Header(..., alias="X-Username"),
    x_password: str = Header(..., alias="X-Password")
):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow('SELECT * FROM users WHERE username = $1', x_username)
        if not user or not pwd_context.verify(x_password, user['password']):
            raise HTTPException(status_code=400, detail="Invalid credentials")
    
    return {"msg": "Login successful!", "user_id": user['id']}

@app.post("/pair")
async def pair(
    x_username: str = Header(..., alias="X-Username"),
):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow('SELECT * FROM users WHERE username = $1', x_username)
        if user:
            return {"msg": "Friend found!", "user_id": user['id']}
        elif not user:
            return {"msg": "Friend not found!", "user_id": None}
    

@app.websocket("/ws/{pair_id}")
async def websocket_endpoint(websocket: WebSocket, pair_id: int):
    await websocket.accept()
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        messages = await conn.fetch('SELECT content FROM messages WHERE pair_id = $1', pair_id)
        for message in messages:
            await websocket.send_text(f"[History] {message['content']}")
    
    while True:
        data = await websocket.receive_text()
        async with pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO messages (content, p)
                VALUES ($1, $2)
            ''', data, pair_id)
            await websocket.send_text(f"You said: {data}")

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
