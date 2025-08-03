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

        # Create a zip file with the chunks
        zip_filename = f"split_audio_{uuid.uuid4().hex}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for chunk_file in chunks:
                zipf.write(chunk_file, os.path.basename(chunk_file))

        tasks[task_id] = {
            "status": "completed",
            "result_path": zip_path,
            "result_filename": f"split_{os.path.splitext(original_filename)[0]}.zip"
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

@app.get("/tasks/{task_id}/download")
async def download_result(task_id: str, background_tasks: BackgroundTasks):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task["status"] != "completed":
        return JSONResponse(
            status_code=400,
            content={"status": task["status"], "message": "Task is not yet completed."}
        )

    result_path = task.get("result_path")
    result_filename = task.get("result_filename")
    
    if not result_path or not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="Result file not found.")

    # Clean up the temp directory in the background after the response is sent
    temp_dir = os.path.dirname(result_path)
    background_tasks.add_task(shutil.rmtree, temp_dir, ignore_errors=True)

    return FileResponse(
        path=result_path,
        media_type='application/zip',
        filename=result_filename
    )

@app.get("/")
def read_root():
    return {"message": "Welcome to the Audio Splitting Service. Use the /tasks endpoint to create a splitting task."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
