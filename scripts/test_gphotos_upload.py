import os
import argparse
from dotenv import load_dotenv
from app.infrastructure.google_photos_sink_client import GooglePhotosSinkClient

# Load environment variables from .env file
load_dotenv()

def main():
    parser = argparse.ArgumentParser(description="Upload a photo to Google Photos.")
    parser.add_argument("photo_path", type=str, help="Path to the photo file.")
    args = parser.parse_args()

    # Get credentials from environment variables
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("Error: Ensure GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN are in your .env file.")
        return

    try:
        # Read the photo bytes
        with open(args.photo_path, "rb") as f:
            photo_bytes = f.read()

        # Initialize the client
        client = GooglePhotosSinkClient(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
        )

        # Upload the photo
        file_name = os.path.basename(args.photo_path)
        description = "A test photo uploaded via the GooglePhotosSinkClient."
        result = client.upload_photo(
            photo_bytes=photo_bytes,
            file_name=file_name,
            description=description,
        )
        print(f"Successfully uploaded photo: {result['productUrl']}")

    except FileNotFoundError:
        print(f"Error: The file '{args.photo_path}' was not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
