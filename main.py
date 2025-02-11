from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import subprocess
import json
from fastapi.templating import Jinja2Templates
import requests

app = FastAPI()

# Helper function to get the Azure CLI token
def get_azure_cli_token():
    try:
        result = subprocess.run(
            ["az", "account", "get-access-token", "--resource", "https://graph.microsoft.com"],
            capture_output=True,
            text=True
        )

        # Log the output and errors
        print("Command Output:", result.stdout)
        print("Command Error:", result.stderr)

        if result.returncode == 0:
            token_data = json.loads(result.stdout)
            return token_data["accessToken"]
        else:
            print("Command failed with return code:", result.returncode)
            return None
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

# @app.get("/")
# async def root():
#     return {"message": "Welcome to the Microsoft Graph API Web App"}

@app.get("/graph/user-cli")
async def get_user_with_cli_token():
    # Get access token from Azure CLI
    access_token = get_azure_cli_token()
    if not access_token:
        return JSONResponse({"error": "Could not acquire token from Azure CLI"}, status_code=500)

    # Make API request to Microsoft Graph
    graph_response = requests.get(
        "https://graph.microsoft.com/v1.0/users/jianrong@jp.com.sg",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if graph_response.status_code == 200:
        return graph_response.json()
    else:
        return JSONResponse(
            {"error": "Error calling Graph API", "details": graph_response.text},
            status_code=graph_response.status_code
        )


@app.post("/graph/send-teams-chat-message")
async def send_teams_chat_message(request: Request):
    data = await request.json()

    # Validate required fields
    required_fields = ["chat_id", "message"]
    if not all(field in data for field in required_fields):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Acquire access token
    access_token = get_azure_cli_token()
    if not access_token:
        raise HTTPException(status_code=500, detail="Could not acquire token from Azure CLI")

    # Send POST request to Microsoft Graph for Teams chat message
    chat_id = data["chat_id"]
    message_content = data["message"]

    graph_url = f"https://graph.microsoft.com/v1.0/chats/{chat_id}/messages"
    message_data = {
        "body": {
            "content": message_content
        }
    }

    response = requests.post(
        graph_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json=message_data
    )

    if response.status_code == 201:
        return {"message": "Message sent successfully"}
    else:
        return JSONResponse(
            {"error": "Error sending message", "details": response.text},
            status_code=response.status_code
        )

# Mount static directory for static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=FileResponse)
async def serve_index():
    # Serve the static index.html file
    return FileResponse("static/index.html")

@app.get("/send-teams-chat")
async def get_send_teams_chat_page():
    return FileResponse("static/sendteamschat.html")

templates = Jinja2Templates(directory="templates")

# @app.get("/", response_class=HTMLResponse)
# async def index(request: Request):
#     # Render hello.html with a name value
#     return templates.TemplateResponse("hello.html", {"request": request, "name": "Azure Developer"})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=8000)
