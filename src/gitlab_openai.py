import os
import gitlab
import time
import threading
import re
from fastapi import FastAPI, Request, BackgroundTasks
from openai import OpenAI

# -------------------------
# CONFIG
# -------------------------
GITLAB_URL = os.getenv("GITLAB_URL")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4-turbo") 

ALLOWED_EXT = (".java", ".py", ".js", ".ts", ".jsx", ".tsx", ".xml", ".yaml")
PROMPT_FILE = "prompt.txt"

client = OpenAI(api_key=OPENAI_API_KEY)
app = FastAPI()
gl = gitlab.Gitlab(GITLAB_URL, private_token=GITLAB_TOKEN)

processing_lock = threading.Lock()
currently_processing_shas = set()

# -------------------------
# UTILS
# -------------------------
def load_prompt(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "You are a Senior Developer. Review the code for security and logic issues. If no serious issue exists, respond exactly with: No critical issues found."

def parse_first_new_line(diff_content):
    """
    Diff mətni daxilindən ilk əlavə edilmiş (+) sətirin nömrəsini tapır.
    """
    lines = diff_content.split('\n')
    current_new_line = 0
    
    for line in lines:
        # Hunk header-i tapırıq: @@ -1,4 +15,6 @@
        if line.startswith('@@'):
            match = re.search(r'\+(\d+)', line)
            if match:
                current_new_line = int(match.group(1)) - 1
            continue
        
        # Əgər sətir dəyişməyibsə və ya yeni əlavədirsə sətir sayını artır
        if not line.startswith('-'):
            current_new_line += 1
            
        # İlk yeni əlavə edilmiş sətiri tapdıqda onun nömrəsini qaytar
        if line.startswith('+') and not line.startswith('+++'):
            return current_new_line
            
    return 1

def check_if_already_reviewed(mr, file_path, sha):
    """Fayl və SHA əsasında təkrar rəy yoxlaması."""
    try:
        discussions = mr.discussions.list(get_all=True)
        search_pattern = f"`{file_path}`"
        sha_pattern = f"SHA: {sha}"
        
        for d in discussions:
            for note in d.attributes.get('notes', []):
                body = note.get('body', '')
                if search_pattern in body and sha_pattern in body:
                    return True
    except:
        pass
    return False

def analyze_chunk(chunk):
    system_prompt = load_prompt(PROMPT_FILE)
    resp = client.chat.completions.create(
        model=AI_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chunk},
        ],
        max_completion_tokens=400,
    )
    return resp.choices[0].message.content.strip()

# -------------------------
# MAIN PROCESSOR
# -------------------------
def process_webhook(payload):
    project_id = payload["project"]["id"]
    mr_iid = payload["object_attributes"]["iid"]
    last_commit_sha = payload["object_attributes"]["last_commit"]["id"]
    
    process_key = f"{mr_iid}_{last_commit_sha}"

    with processing_lock:
        if process_key in currently_processing_shas:
            print(f"Skipping: {process_key} is already processing.")
            return
        currently_processing_shas.add(process_key)

    try:
        project = gl.projects.get(project_id)
        mr = project.mergerequests.get(mr_iid)
        
        if mr.state != 'opened':
            return

        mr = project.mergerequests.get(mr_iid)
        diff_refs = mr.diff_refs
        if not diff_refs:
            print("Diff refs not found.")
            return

        changes_data = mr.changes()
        reviewed_any = False
        
        for ch in changes_data["changes"]:
            new_path = ch.get("new_path")
            diff_text = ch.get("diff")

            # Filtrasiya
            if (ch.get("deleted_file") or not new_path or 
                not any(new_path.endswith(ext) for ext in ALLOWED_EXT) or 
                not diff_text or not diff_text.strip()):
                continue

            # Təkrar yoxlaması
            if check_if_already_reviewed(mr, new_path, last_commit_sha):
                print(f"Already reviewed: {new_path}")
                continue

            print(f"Reviewing: {new_path}")
            review_comment = analyze_chunk(f"FILE: {new_path}\n{diff_text}")

            if "No critical issues found" in review_comment or len(review_comment) < 15:
                continue

            target_line = parse_first_new_line(diff_text)
            
            comment_body = (
               # f"🤖 **AI Code Review for `{new_path}`**\n\n"
                f"{review_comment}\n\n"
                f"---\n"
                #f"SHA: {last_commit_sha}"
            )

            # Changes bölməsində şərh yaratmağa cəhd (Discussion)
            try:
                mr.discussions.create({
                    'body': comment_body,
                    'position': {
                        'base_sha': diff_refs['base_sha'],
                        'start_sha': diff_refs['start_sha'],
                        'head_sha': diff_refs['head_sha'],
                        'position_type': 'text',
                        'new_path': new_path,
                        'old_path': ch.get('old_path', new_path),
                        'new_line': target_line
                    }
                })
                print(f"Successfully commented on {new_path} at line {target_line}")
                reviewed_any = True
            except Exception as diff_err:
                # Əgər 400 xətası verərsə (sətir tapılmazsa), fallback olaraq Overview-a yaz
                print(f"Diff error for {new_path}: {diff_err}. Falling back to general note.")
                mr.notes.create({'body': comment_body})
                reviewed_any = True

            time.sleep(1)

        if reviewed_any:
            # Etiket əlavə et
            labels = mr.labels or []
            if "AI-reviewed" not in labels:
                labels.append("AI-reviewed")
                mr.labels = labels
                mr.save()

    except Exception as e:
        print(f"General processing error: {e}")
    finally:
        with processing_lock:
            currently_processing_shas.discard(process_key)

# -------------------------
# WEBHOOK ENDPOINT
# -------------------------
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    
    if payload.get("object_kind") != "merge_request":
        return {"status": "ignored"}

    action = payload["object_attributes"].get("action")
    if action not in ["open", "reopen", "update"]:
        return {"status": "ignored"}

    background_tasks.add_task(process_webhook, payload)
    return {"status": "AI review process started"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)