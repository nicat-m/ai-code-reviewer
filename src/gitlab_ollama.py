# this code for local model with ollama, if you want to use openai, please check gitlab_openai.py


import os
import gitlab
import requests
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException

# Configuration (reads from Environment Variables)
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.e-taxes.gov.az")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN","")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://IP/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-coder:6.7b")

app = FastAPI()

# GitLab connection
try:
    gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN)
except Exception as e:
    print(f"GitLab connection error: {e}")

def get_mr_diff(project_id, mr_iid):
    """Fetches MR changes (diff) from GitLab"""
    project = gl.projects.get(project_id)
    mr = project.mergerequests.get(mr_iid)
    changes = mr.changes()

    diff_text = ""
    for change in changes['changes']:
        # Only consider new or modified files
        if not change['deleted_file']:
            diff_text += f"\nFile: {change['new_path']}\n"
            diff_text += f"Diff:\n{change['diff']}\n"
            diff_text += "-" * 30

    return mr, diff_text

def analyze_with_ollama(diff_text):
    """Sends query to Ollama API"""
    prompt = f"""
    You are a Senior DevOps and Software Engineer code reviewer.
    Review the following code changes (git diff).

    Focus on:
    1. Potential bugs and logic errors.
    2. Syntax errors.
    3. Security vulnerabilities.
    4. Code quality and maintainability issues.
    5. Best practices and coding standards adherence.
    6. Performance optimization opportunities.
    7. Proper error handling and logging.
    8. Resource management (e.g., closing connections, memory leaks).
    
    Format your response in Markdown using bullet points. Be concise and constructive.

    Code Changes:
    {diff_text}
    """

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        return response.json().get("response", "Error getting response from AI")
    except Exception as e:
        return f"AI Analysis Failed: {str(e)}"

def process_webhook(payload):
    """Main function to run in the background"""
    try:
        project_id = payload['project']['id']
        mr_iid = payload['object_attributes']['iid']
        action = payload['object_attributes']['action']

        print(f"Processing MR #{mr_iid} for Project {project_id} - Action: {action}")

        # 1. Get the diff
        mr, diff_text = get_mr_diff(project_id, mr_iid)

        if not diff_text:
            print("No changes found to analyze.")
            return

        # 2. Analyze with Ollama
        print("Sending to Ollama...")
        review_comment = analyze_with_ollama(diff_text)

        # 3. Post comment to GitLab
        print("Posting comment to GitLab...")
        final_comment = f"🤖 **AI Code Review ({OLLAMA_MODEL})**\n\n{review_comment}"
        mr.notes.create({'body': final_comment})
        print("Done!")

    except Exception as e:
        print(f"Error processing webhook: {e}")

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """GitLab Webhook endpoint"""
    payload = await request.json()

    # Only look at Merge Request events
    if payload.get('object_kind') == 'merge_request':
        action = payload['object_attributes'].get('action')
        # Trigger when MR is opened (open) or updated (update)
        if action in ['open', 'reopen', 'update']:
            background_tasks.add_task(process_webhook, payload)
            return {"status": "Analysis started in background"}

    return {"status": "Event ignored"}
