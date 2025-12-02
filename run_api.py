import uvicorn
import multiprocessing
import sys
import os

# --- 关键部分：路径处理 ---
# 这部分对于打包后的 .exe 能找到模块至关重要
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
    # 在打包模式下，我们将 src 目录添加到 sys.path，这样 Uvicorn 才能找到 webui
    sys.path.insert(0, os.path.join(base_path, 'src'))
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
    # 在开发模式下，也将 src 目录添加到 sys.path
    sys.path.insert(0, os.path.join(base_path, 'src'))

# --- 将内置的 FFmpeg 添加到 PATH 作为备用 ---
ffmpeg_bin_path = os.path.join(base_path, 'ffmpeg_bin')
os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + ffmpeg_bin_path

if __name__ == '__main__':
    # 对于使用多进程的打包程序，必须调用此函数。
    multiprocessing.freeze_support()

    print("Super Whisper API Server is starting...")
    print("Listening on http://0.0.0.0:5000")
    print("Press CTRL+C to stop.")

    # 启动 Uvicorn 服务器，作为后台 API 服务运行
    uvicorn.run(
        "webui.app:app",
        host="0.0.0.0",
        port=5000,
        reload=False
    )
