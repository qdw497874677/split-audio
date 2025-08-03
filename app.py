import os
import shutil
import zipfile
import uuid
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()

UPLOADS_DIR = "uploads"
os.makedirs(UPLOADS_DIR, exist_ok=True)

# In-memory storage for task status
tasks = {}

def process_audio_split(
    task_id: str,
    input_path: str,
    temp_dir: str,
    original_filename: str,
    file_extension: str,
    max_duration_minutes: int,
    overlap_seconds: int
):
    try:
        tasks[task_id] = {"status": "processing"}
        
        # Load audio file
        audio = AudioSegment.from_file(input_path)

        # Convert durations to milliseconds
        max_duration_ms = max_duration_minutes * 60 * 1000
        overlap_ms = overlap_seconds * 1000
        
        total_duration_ms = len(audio)
        chunks = []
        start_ms = 0

        # Create chunks
        while start_ms < total_duration_ms:
            end_ms = start_ms + max_duration_ms
            chunk = audio[start_ms:end_ms]
            
            chunk_filename = f"chunk_{len(chunks) + 1}{file_extension}"
            chunk_path = os.path.join(temp_dir, chunk_filename)
            
            export_format = file_extension.strip('.').lower()
            if export_format == 'm4a':
                export_format = 'mp4'
            
            chunk.export(chunk_path, format=export_format)
            chunks.append(chunk_path)
            
            if end_ms >= total_duration_ms:
                break
            
            start_ms = end_ms - overlap_ms

        if not chunks:
            raise ValueError("Could not split the audio file. The file might be too short.")

        # The result is the list of chunk files
        chunk_filenames = [os.path.basename(p) for p in chunks]
        tasks[task_id] = {
            "status": "completed",
            "files": chunk_filenames,
            "task_dir": temp_dir
        }

    except Exception as e:
        tasks[task_id] = {"status": "failed", "error": str(e)}
    finally:
        # Clean up the original uploaded file, but keep the directory for the result
        if os.path.exists(input_path):
            os.remove(input_path)

@app.post("/tasks")
async def create_split_task(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    max_duration_minutes: int = Form(10),
    overlap_seconds: int = Form(60)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    file_extension = os.path.splitext(file.filename)[1]
    if not file_extension:
        raise HTTPException(status_code=400, detail="Could not determine file extension.")

    task_id = str(uuid.uuid4())
    task_dir = os.path.join(UPLOADS_DIR, f"task_{task_id}")
    os.makedirs(task_dir, exist_ok=True)
    
    input_path = os.path.join(task_dir, file.filename)
    
    try:
        with open(input_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    tasks[task_id] = {"status": "pending"}
    
    background_tasks.add_task(
        process_audio_split,
        task_id,
        input_path,
        task_dir,
        file.filename,
        file_extension,
        max_duration_minutes,
        overlap_seconds
    )
    
    return {"task_id": task_id}

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.get("/downloads/{task_id}/{filename}")
async def download_chunk(task_id: str, filename: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Task is not yet completed.")

    task_dir = task.get("task_dir")
    if not task_dir:
        raise HTTPException(status_code=404, detail="Task directory not found.")

    file_path = os.path.join(task_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(path=file_path, filename=filename)

@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task_data(task_id: str):
    """
    Deletes the data associated with a completed task to free up space.
    """
    task = tasks.get(task_id)
    if not task:
        # Return 204 even if not found to make the operation idempotent.
        return

    # Remove from in-memory task list
    tasks.pop(task_id, None)

    # Remove the task directory from the filesystem
    task_dir = os.path.join(UPLOADS_DIR, f"task_{task_id}")
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir, ignore_errors=True)
    
    return

@app.get("/")
def read_root():
    return {"message": "Welcome to the Audio Splitting Service. Use the /tasks endpoint to create a splitting task."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
