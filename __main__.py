import asyncio
from nio import AsyncClient, MatrixRoom, RoomMessageText
from github import Github
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")
MATRIX_USERNAME = os.getenv("MATRIX_USERNAME")
MATRIX_PASSWORD = os.getenv("MATRIX_PASSWORD")
MATRIX_CHANNEL_ID = os.getenv("MATRIX_CHANNEL_ID")
GITHUB_PERSONAL_ACCESS_TOKEN = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
GITHUB_ORGANIZATION_NAME = os.getenv("GITHUB_ORGANIZATION_NAME")

IGNORED_MESSAGES = (
    "Failed to process the request. Please check the username and try again."
)


async def main():
    # Initialize Matrix client
    matrix_client = AsyncClient(MATRIX_HOMESERVER, MATRIX_USERNAME)
    await matrix_client.login(MATRIX_PASSWORD)

    # Initialize GitHub client
    github_client = Github(GITHUB_PERSONAL_ACCESS_TOKEN)
    organization = github_client.get_organization(GITHUB_ORGANIZATION_NAME)

    async def process_message(room: MatrixRoom, event: RoomMessageText):
        messages = await matrix_client.room_messages(
            MATRIX_CHANNEL_ID, limit=1
        )  # Get the most recent message

        # Extract the latest message
        if not messages.chunk:

            return

        try:
            github_username = messages.chunk[0].body
            print(github_username)
            # Ignore predefined messages to prevent recursion
            if github_username == IGNORED_MESSAGES:
                print("Error last")
                return

            try:
                # Add user to GitHub organization
                user = github_client.get_user(github_username)
                organization.add_to_members(user)
                await matrix_client.room_send(
                    room_id=MATRIX_CHANNEL_ID,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": f"Successfully added @{github_username} to the GitHub organization!",
                    },
                )
            except Exception as e:
                # print(f"Failed to add @{github_username}: {str(e)}")
                await matrix_client.room_send(
                    room_id=MATRIX_CHANNEL_ID,
                    message_type="m.room.message",
                    content={
                        "msgtype": "m.text",
                        "body": "Failed to process the request. Please check the username and try again.",
                    },
                )

        except Exception as e:
            print(e)

    # Register callback for new messages
    matrix_client.add_event_callback(process_message, RoomMessageText)

    print("Bot is now running. Listening for messages in the specified channel...")
    await matrix_client.sync_forever(timeout=30000, full_state=True)


if __name__ == "__main__":
    asyncio.run(main())
