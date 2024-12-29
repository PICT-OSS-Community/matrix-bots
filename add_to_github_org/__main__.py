import asyncio
from nio import AsyncClient, MatrixRoom, RoomMessageText, RoomMemberEvent
from github import Github
from dotenv import load_dotenv
import os
import json

# Load environment variables
load_dotenv()
MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")
MATRIX_USERNAME = os.getenv("MATRIX_USERNAME")
MATRIX_PASSWORD = os.getenv("MATRIX_PASSWORD")
MATRIX_CHANNEL_ID = os.getenv("MATRIX_CHANNEL_ID")
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
GITHUB_ORGANIZATION_NAME = os.getenv("GITHUB_ORGANIZATION_NAME")

# To store initial list of joined people in room
joined = []

async def main():
    global joined
    # Initialize Matrix client
    matrix_client = AsyncClient(MATRIX_HOMESERVER, MATRIX_USERNAME)
    await matrix_client.login(MATRIX_PASSWORD)
    joined = (await matrix_client.joined_members(MATRIX_CHANNEL_ID)).members

    # Initialize GitHub client
    github_client = Github(GITHUB_PERSONAL_ACCESS_TOKEN)
    organization = github_client.get_organization(GITHUB_ORGANIZATION_NAME)

    async def process_message(room: MatrixRoom, event: RoomMessageText):
        # Get the most recent message
        messages = await matrix_client.room_messages(
            MATRIX_CHANNEL_ID, limit=1
        )

        try:
            github_username = messages.chunk[0].body
            # Only making requests to github if input adheres to a format to prevent recursion through predefined messages
            if github_username[:5] == "user:":
                github_username = github_username[5:].strip()
                try:
                    # Add user to GitHub organization
                    user = github_client.get_user(github_username)
                    organization.add_to_members(user)
                    await matrix_client.room_send(
                        room_id=MATRIX_CHANNEL_ID,
                        message_type="m.room.message",
                        content={
                            "msgtype": "m.text",
                            "body": f"Successfully invited @{github_username} to the GitHub organization!",
                        }
                    )
                    print(f"Successfully invited @{github_username} to the GitHub organization!")
                except Exception as e:
                    errorObj = json.loads(str(e)[4:])
                    print(f"Failed to add @{github_username}! Error: {errorObj['status']} {errorObj['message']}")
                    await matrix_client.room_send(
                        room_id=MATRIX_CHANNEL_ID,
                        message_type="m.room.message",
                        content={
                            "msgtype": "m.text",
                            "body": f"Failed to add @{github_username}\nCode: {errorObj['status']}\nMessage: {errorObj['message']}",
                        }
                    )

        except Exception as e:
            print(e)

    # To handle users joining (and leaving) the room
    async def process_new_joins(room: MatrixRoom, event: RoomMemberEvent):
        global joined

        # Only process for the same room id; prevents pinging random users
        if room.room_id != MATRIX_CHANNEL_ID:
            return

        currentlyJoined = (await matrix_client.joined_members(MATRIX_CHANNEL_ID)).members
        if joined != currentlyJoined:
            # If someone leaves/joins, update the joined members list
            # Not currently handling the membership values "invite", "ban" and "knock"
            if event.membership == "leave":
                joined = currentlyJoined
                print(f"{event.sender} left the room!")
            elif event.membership == "join":
                joined = currentlyJoined
                print(f"{event.sender} joined the room!")
                await matrix_client.room_send(
                    room_id=MATRIX_CHANNEL_ID,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": f"Welcome to the room {event.sender}!\nTo invite yourself to the organization, send the command as user:{{username}}\nExample: user:yokelman"
                    }
                )

    # Register callbacks for new messages and new joins
    matrix_client.add_event_callback(process_message, RoomMessageText)
    matrix_client.add_event_callback(process_new_joins, RoomMemberEvent)

    print("Bot is now running. Listening for messages in the specified channel...")
    await matrix_client.sync_forever(timeout=30000, full_state=True)


if __name__ == "__main__":
    asyncio.run(main())
