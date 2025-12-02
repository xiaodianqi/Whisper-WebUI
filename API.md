## Super Whisper WebUI - API 接口说明文档

本文档旨在为希望通过编程方式与 Super Whisper WebUI 后端服务进行交互的开发者提供指导。

### 启动 API 服务器

在开始之前，请确保您已根据 `README.md` 中的开发者指南安装好所有依赖，然后运行以下命令来启动纯 API 服务器：

```sh
uv run python run_api.py
```

服务器成功启动后，将监听 `http://127.0.0.1:5000`。

### 总体工作流程

与 API 的交互通常遵循以下三步：
1.  **上传文件**: 通过调用 `POST /upload` 接口，上传音频文件并提交一个转写任务，获取一个唯一的 `task_id`。
2.  **轮询状态**: 使用上一步获取的 `task_id`，周期性地调用 `GET /tasks/<task_id>/status` 接口，查询任务的实时状态。
3.  **获取结果**: 当任务状态变为 `SUCCESS` 时，调用 `GET /tasks/<task_id>/result/{format}` 接口下载转写结果文件。

---

### 接口详解

#### 1. 提交转写任务

- **Endpoint**: `POST /upload`
- **说明**: 上传一个音频文件，并创建一个新的语音转写任务。
- **请求格式**: `multipart/form-data`

##### 请求参数 (Form Data)

| 参数名 | 类型 | 是否必需 | 描述 |
| :--- | :--- | :--- | :--- |
| `audioFile` | File | **是** | 要进行转写的音频文件，支持 `.mp3`, `.wav`, `.flac`, `.m4a` 等格式。 |
| `model` | String | 否 | 指定使用的 Whisper 模型。默认为 `medium`。可选值: `tiny`, `base`, `small`, `medium`, `large`。 |
| `language` | String | 否 | 指定音频的语言，如 `Chinese`, `English`。如果留空，则自动检测。 |
| `vad` | String | 否 | 指定使用的 VAD 引擎。`"true"` 表示使用 Silero-VAD，`"false"` (默认) 表示使用 Whisper 原生 VAD。 |
| `no_speech_threshold`| String | 否 | 原生 VAD 的灵敏度，一个 0.0 到 1.0 之间的小数。仅在 `vad` 为 `"false"` 时生效。 |
| `demucs` | String | 否 | 是否开启 Demucs 强力降噪。`"true"` 表示开启，`"false"` (默认) 表示关闭。 |
| `gpu` | String | 否 | 是否使用 GPU 加速。`"true"` 表示尝试使用，`"false"` (默认) 表示仅使用 CPU。 |

##### 返回结果

- **成功 (200 OK)**:
  ```json
  {
      "success": true,
      "task_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
  ```
- **失败 (4xx/5xx)**:
  ```json
  {
      "success": false,
      "error": "具体的错误信息，例如：没有上传文件。"
  }
  ```

##### `curl` 示例
```sh
curl -X POST \
  -F "audioFile=@/path/to/your/audio.mp3" \
  -F "model=medium" \
  -F "language=Chinese" \
  http://127.0.0.1:5000/upload
```

---

#### 2. 查询任务状态

- **Endpoint**: `GET /tasks/<task_id>/status`
- **说明**: 根据任务 ID 查询一个任务的当前处理状态。
- **URL 参数**:
  - `<task_id>`: 从 `/upload` 接口返回的唯一任务 ID。

##### 返回结果

- **任务正在运行**:
  ```json
  {
      "state": "RUNNING"
  }
  ```
- **任务成功**:
  ```json
  {
      "state": "SUCCESS"
  }
  ```
- **任务失败**:
  ```json
  {
      "state": "FAILURE",
      "error": "识别过程中发生的具体错误信息。"
  }
  ```

##### `curl` 示例
```sh
curl http://127.0.0.1:5000/tasks/a1b2c3d4-e5f6-7890-1234-567890abcdef/status
```

---

#### 3. 获取结果文件

- **Endpoint**: `GET /tasks/<task_id>/result/<format>`
- **说明**: 在任务成功后，下载指定格式的转写结果。
- **URL 参数**:
  - `<task_id>`: 任务 ID。
  - `<format>`: 文件格式，可以是 `srt` 或 `txt`。

##### 返回结果

- **成功 (200 OK)**:
  - **Headers**: `Content-Type: text/plain; charset=utf-8`
  - **Body**: 纯文本的 `.srt` 或 `.txt` 文件内容。
- **失败 (404 Not Found)**: 如果任务不存在或未成功完成。

##### `curl` 示例
```sh
# 下载 .srt 文件并保存为 result.srt
curl -o result.srt http://127.0.0.1:5000/tasks/a1b2c3d4-e5f6-7890-1234-567890abcdef/result/srt

# 下载 .txt 文件并保存为 result.txt
curl -o result.txt http://127.0.0.1:5000/tasks/a1b2c3d4-e5f6-7890-1234-567890abcdef/result/txt
```

---

### Python 完整示例 (`test_api.py`)

这是一个完整的 Python 脚本，演示了如何使用 `requests` 库完成从上传到下载的全过程。

```python
import requests
import time
import os

# --- 配置 ---
API_URL = "http://127.0.0.1:5000"
AUDIO_FILE_PATH = "path/to/your/audio.mp3" # 替换成你的音频文件路径

def main():
    if not os.path.exists(AUDIO_FILE_PATH):
        print(f"错误: 音频文件不存在 -> {AUDIO_FILE_PATH}")
        return

    # 1. 上传文件并提交任务
    print(f"正在上传文件: {AUDIO_FILE_PATH}")
    with open(AUDIO_FILE_PATH, 'rb') as f:
        files = {'audioFile': (os.path.basename(AUDIO_FILE_PATH), f)}
        payload = {
            'model': 'medium',
            'language': 'Chinese',
            'gpu': 'true'
        }
        try:
            response = requests.post(f"{API_URL}/upload", files=files, data=payload)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException as e:
            print(f"上传失败: {e}")
            return

    if not result.get('success'):
        print(f"提交任务失败: {result.get('error', '未知错误')}")
        return

    task_id = result['task_id']
    print(f"任务提交成功! Task ID: {task_id}")

    # 2. 轮询任务状态
    while True:
        print("正在查询任务状态...")
        try:
            response = requests.get(f"{API_URL}/tasks/{task_id}/status")
            response.raise_for_status()
            status_data = response.json()
        except requests.exceptions.RequestException as e:
            print(f"查询状态失败: {e}")
            break

        if status_data['state'] == 'SUCCESS':
            print("任务处理成功!")
            # 3. 获取结果
            try:
                txt_response = requests.get(f"{API_URL}/tasks/{task_id}/result/txt")
                txt_response.raise_for_status()
                print("\n--- TXT 结果 ---")
                # 确保以 UTF-8 解码
                print(txt_response.content.decode('utf-8'))
            except requests.exceptions.RequestException as e:
                print(f"获取 TXT 结果失败: {e}")
            break
        elif status_data['state'] == 'FAILURE':
            print(f"任务处理失败: {status_data.get('error', '未知错误')}")
            break
        
        print(f"当前状态: {status_data['state']}，5秒后再次查询...")
        time.sleep(5)

if __name__ == "__main__":
    main()
```
