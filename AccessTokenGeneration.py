import os
import requests
from dotenv import load_dotenv

# Load from custom .env file
load_dotenv(dotenv_path="credentials.env")

CLIENT_ID = os.getenv("ZOHO_CLIENT_ID")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN")
REDIRECT_URI = os.getenv("ZOHO_REDIRECT_URL")  

# Generate acess token using refresh token 
def generate_access_token():
    url = "https://accounts.zoho.in/oauth/v2/token"  # Authentication Url 
    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "refresh_token"
    }

    response = requests.post(url, params=params) #Sending request for generation of access token 
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data.get("access_token")

        # Update credentials.env file with new token
        update_env_variable("ZOHO_ACCESS_TOKEN", access_token)
        print(f"Access token generated and saved to credentials.env.")
        return access_token
    else:
        print(f"Failed to generate token: {response.status_code}")
        print(response.text)
        return None

# Function for updating the env file when access token is genrated 
def update_env_variable(key, value):
    env_path = "credentials.env"
    # Read existing lines
    with open(env_path, 'r') as f:
        lines = f.readlines()

    # Write back with updated key
    with open(env_path, 'w') as f:
        key_found = False
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                key_found = True
            else:
                f.write(line)
        if not key_found:
            f.write(f"{key}={value}\n")

if __name__ == "__main__":
    generate_access_token()
