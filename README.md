# 音频切分Web服务

这是一个简单的Web服务，可以将一个较长的音频文件根据指定的参数切分为多个较短的音频片段。

## 功能

-   **异步处理**: 上传音频文件后，服务会立即返回一个任务ID，并在后台进行切分处理，不会阻塞请求。
-   **任务状态查询**: 可以随时通过任务ID查询音频切分的进度（如：处理中、已完成、失败）。
-   **结果下载**: 任务成功后，会返回所有切分后音频片段的文件名列表，您可以根据需要单独下载每一个文件。
-   **自定义参数**:
    -   可自定义每个分片的最大时长（分钟）。
    -   可自定义分片间的重叠时长（秒）。
-   **文件归档**: 所有任务文件会存储在服务器的 `uploads/` 目录下，并按任务ID进行隔离，方便管理和归档。

## 文件结构

```
.
├── app.py               # FastAPI应用主文件
├── Dockerfile           # 用于构建Docker镜像
├── requirements.txt     # Python依赖
├── uploads/             # 上传和处理文件的存储目录
└── README.md            # 本说明文件
```

## 如何运行

您可以选择两种方式来运行此服务：**本地直接运行** 或 **通过Docker容器运行**。

---

### 1. 本地直接运行

#### 先决条件

-   Python 3.7+
-   pip
-   **FFmpeg**: `pydub` 库需要 `ffmpeg` 来处理音频文件。您必须在您的系统上安装它。
    -   **macOS**: `brew install ffmpeg`
    -   **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
    -   **Windows**: 从 [官网](https://ffmpeg.org/download.html) 下载并将其添加到系统PATH。

#### 步骤

1.  **安装Python依赖**:
    在项目根目录下打开终端，运行以下命令：
    ```bash
    pip install -r requirements.txt
    ```

2.  **启动服务**:
    ```bash
    python app.py
    ```
    或者使用uvicorn：
    ```bash
    uvicorn app:app --host 0.0.0.0 --port 8000
    ```
    服务将在 `http://localhost:8000` 上运行。

---

### 2. 通过Docker运行

#### 先决条件

-   Docker 已安装并正在运行。

#### 步骤

1.  **构建Docker镜像**:
    在项目根目录下打开终端，运行以下命令来构建镜像。将 `audio-splitter` 替换为您喜欢的镜像名称。
    ```bash
    docker build -t audio-splitter .
    ```

2.  **运行Docker容器**:
    使用以下命令从镜像启动一个容器。我们强烈建议您将容器内的 `/app/uploads` 目录挂载到宿主机的一个目录上，以便永久保存处理完的文件。

    ```bash
    docker run -d -p 8000:8000 \
      -v /path/on/your/host:/app/uploads \
      --name audio-splitter-container \
      audio-splitter
    ```
    -   `-d`: 在后台运行容器。
    -   `-p 8000:8000`: 将主机的8000端口映射到容器的8000端口。
    -   `-v /path/on/your/host:/app/uploads`: **(重要)** 将您宿主机上的一个目录（例如 `/home/user/audio_files`）挂载到容器内的 `/app/uploads` 目录。**请务必将 `/path/on/your/host` 替换为您自己服务器上的真实路径。**
    -   `--name`: 为容器指定一个名称。

    服务将在 `http://localhost:8000` 上运行。

**例子**：
```bash
# 创建一个用于存储文件的本地目录
mkdir -p /services/audio-splitter-data

# 运行容器，并将本地目录挂载
docker run -d -p 18001:8000 \
  -v /services/audio-splitter-data:/app/uploads \
  --name audio-splitter-container \
  audio-splitter
```
此设置可确保即使容器被删除或重建，您的所有音频文件和处理结果都将保留在宿主机的 `/services/audio-splitter-data` 目录中。


---

## 如何使用服务

服务采用异步任务模型。您需要按顺序调用三个API端点来完成一次完整的音频切分。

您可以在浏览器中访问 `http://localhost:8000/docs` 来查看和测试FastAPI自动生成的交互式API文档。

---

### 第1步：创建切分任务

使用 `POST /tasks` 端点上传您的音频文件并启动一个切分任务。

**参数**:
-   `file`: (文件) 您要上传的音频文件 (例如: `my_audio.mp3`)。
-   `max_duration_minutes`: (表单) 每个分片的最大时长（分钟），默认为 `10`。
-   `overlap_seconds`: (表单) 分片间的重叠时长（秒），默认为 `60`。

**`curl` 示例**:
假设您有一个名为 `my_long_audio.mp3` 的文件。

```bash
curl -X POST "http://localhost:8000/tasks" \
     -F "file=@my_long_audio.mp3" \
     -F "max_duration_minutes=8" \
     -F "overlap_seconds=30"
```

**成功响应**:
服务会立即返回一个JSON对象，其中包含您的任务ID。请记下这个ID。

```json
{
  "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```

---

### 第2步：检查任务状态

使用 `GET /tasks/{task_id}` 端点来查询任务的当前状态。将 `{task_id}` 替换为您在上一步中获取的ID。

**`curl` 示例**:

```bash
curl -X GET "http://localhost:8000/tasks/a1b2c3d4-e5f6-7890-1234-567890abcdef"
```

**响应**:
响应会显示任务的当前状态。
-   **处理中**:
    ```json
    {
      "status": "processing"
    }
    ```
-   **处理完成**:
    ```json
    {
      "status": "completed",
      "files": [
        "chunk_1.mp3",
        "chunk_2.mp3",
        "chunk_3.mp3"
      ],
      "task_dir": "uploads/task_a1b2c3d4-e5f6-7890-1234-567890abcdef"
    }
    ```
-   **处理失败**:
    ```json
    {
      "status": "failed",
      "error": "具体的错误信息..."
    }
    ```
请重复查询此端点，直到状态变为 `completed`。

---

### 第3步：下载结果文件

一旦任务状态变为 `completed`，您就可以根据上一步返回的 `files` 列表，使用 `GET /downloads/{task_id}/{filename}` 端点来下载您需要的任意一个音频片段。

**`curl` 示例**:
假设您想下载列表中的第一个文件 `chunk_1.mp3`：

```bash
curl -X GET "http://localhost:8000/downloads/a1b2c3d4-e5f6-7890-1234-567890abcdef/chunk_1.mp3" \
     -o "chunk_1.mp3"
```

此命令会将指定的音频片段保存到本地。您可以对列表中的任何文件重复此操作。所有文件都会**保留**在服务器上，直到您手动删除整个任务。

---

### 第4步（可选）：清理任务数据

为了释放服务器存储空间，当您确认不再需要某个任务的数据后，可以使用 `DELETE /tasks/{task_id}` 端点将其从服务器上删除。

**`curl` 示例**:

```bash
curl -X DELETE "http://localhost:8000/tasks/a1b2c3d4-e5f6-7890-1234-567890abcdef"
```

**成功响应**:
此请求成功后不会返回任何内容，HTTP状态码为 `204 No Content`。该任务的所有相关文件（包括上传的源文件和生成的ZIP包）都将被删除。
