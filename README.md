# 音频切分Web服务

这是一个简单的Web服务，可以将一个较长的音频文件根据指定的参数切分为多个较短的音频片段。

## 功能

-   通过HTTP POST请求上传音频文件。
-   可自定义每个分片的最大时长（分钟）。
-   可自定义每个分片与其上一个分片之间的重叠时长（秒）。
-   将切分后的所有音频片段打包成一个ZIP文件返回。

## 文件结构

```
.
├── app.py               # FastAPI应用主文件
├── Dockerfile           # 用于构建Docker镜像
├── requirements.txt     # Python依赖
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
    使用以下命令从镜像启动一个容器：
    ```bash
    docker run -d -p 8000:8000 --name audio-splitter-container audio-splitter
    ```
    -   `-d`: 在后台运行容器。
    -   `-p 8000:8000`: 将主机的8000端口映射到容器的8000端口。
    -   `--name`: 为容器指定一个名称。

    服务将在 `http://localhost:8000` 上运行。

---

## 如何使用服务

您可以使用任何HTTP客户端来调用 `/split-audio/` 端点。以下是使用 `curl` 的一个例子。

假设您有一个名为 `my_long_audio.mp3` 的音频文件在当前目录。

-   **file**: `@my_long_audio.mp3` (要上传的文件)
-   **max_duration_minutes**: `8` (每个分片最大8分钟)
-   **overlap_seconds**: `30` (分片间重叠30秒)

运行以下 `curl` 命令：

```bash
curl -X POST "http://localhost:8000/split-audio/" \
     -F "file=@my_long_audio.mp3" \
     -F "max_duration_minutes=8" \
     -F "overlap_seconds=30" \
     -o "output.zip"
```

命令成功执行后，您将在当前目录下得到一个名为 `output.zip` 的文件，其中包含了所有切分后的音频片段。

您也可以在浏览器中访问 `http://localhost:8000/docs` 来查看和测试FastAPI自动生成的交互式API文档。
