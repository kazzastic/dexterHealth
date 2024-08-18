import asyncio
import httpx
import websockets

BASE_URL = "http://localhost:8000"  # Change this if your server is running on a different URL

class ChatClient:
    def __init__(self):
        self.user_id = None
        self.username = None
        self.friend_id = None
        self.pair_id = None
        self.websocket_url = None

    async def register(self, username: str, password: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
            f"{BASE_URL}/register",
            headers={
                "X-Username": username,
                "X-Password": password
            }
        )
            if response.status_code == 200:
                print("Registration successful!")
            elif response.status_code == 400 and response.json().get('detail') == "Username already taken":
                print("Username already taken. Please choose another one.")
            else:
                print(f"Registration failed: {response.json().get('detail')}")

    async def login(self, username: str, password: str):
        async with httpx.AsyncClient() as client:
            # response = await client.post(f"{BASE_URL}/login", json={"username": username, "password": password})
            response = await client.post(
            f"{BASE_URL}/login",
            headers={
                "X-Username": username,
                "X-Password": password
            }
        )
            if response.status_code == 200:
                print("Login successful!")
                data = response.json()
                self.user_id = data["user_id"]
                self.username = username
                # self.websocket_url = f"ws://{BASE_URL}/ws/{self.user_id}"
            else:
                print(f"Login failed: {response.json().get('detail')}")
            return self.user_id

    async def pair(self, my_userid: str, friend_username: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
            f"{BASE_URL}/pair",
            headers={
                "X-Username": friend_username
            }
        )
            if response.status_code == 200:
                print("Successful pair attempt")
                data = response.json()
                self.friend_id = data["user_id"]
                if self.friend_id:
                    print(f"Pair {friend_username} exists with id: {self.friend_id}")
                    self.pair_id = my_userid + self.friend_id
                    self.websocket_url = f"ws://localhost:8000/ws/{self.pair_id}"
                else:
                    print(f"Pair {friend_username} does not exist")
                
            else:
                print(f"Failed while connecting to pair with response {response.status_code}")

    async def connect(self):
        if not self.websocket_url:
            raise Exception("You must log in first!")

        async with websockets.connect(self.websocket_url) as websocket:
            print(f"Connected as {self.username}. Chat history loaded.")
            try:
                while True:
                    message = await websocket.recv()
                    print(f"Received message: {message}")
            except Exception as e:
                print(f"WebSocket connection closed: {e}")

    async def send_message(self, message: str):
        if not self.websocket_url:
            raise Exception("You must log in first!")

        async with websockets.connect(self.websocket_url) as websocket:
            await websocket.send(message)
            print(f"Message sent: {message}")

client = ChatClient()

async def main():
    # Register a new user
    my_user_name = str(input("Enter your username: "))
    my_password = str(input("Enter your password: "))
    await client.register(username=my_user_name, password=my_password)

    # Login with the user
    my_user_id = await client.login(my_user_name, my_password)

    if my_user_id:
        friend_username = str(input("Friend Username: "))
        await client.pair(my_userid=my_user_id, friend_username=friend_username)

    asyncio.create_task(client.connect())

    await asyncio.sleep(5)
    await client.send_message("hey1")
    await client.send_message("hey2")

    # while True:
    #     input_msg = str(input("your input: "))
    #     await client.send_message(input_msg)

if __name__ == "__main__":
    asyncio.run(main())
