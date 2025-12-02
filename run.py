import uvicorn
import multiprocessing
import sys
import os
import webbrowser
from threading import Timer

# --- 关键部分：路径处理 ---
# 如果程序被打包了，sys._MEIPASS 会指向解压后的临时文件夹
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


def open_browser():
    """
    在默认浏览器中打开指定的 URL。
    """
    try:
        webbrowser.open_new("http://127.0.0.1:5000")
    except Exception as e:
        print(f"自动打开浏览器失败: {e}")

if __name__ == '__main__':
    multiprocessing.freeze_support()

    Timer(1.5, open_browser).start()

    # 启动 Uvicorn 服务器
    # 运行时，上面的 sys.path.insert 会确保 "webui.app:app" 能被找到
    uvicorn.run(
        "webui.app:app",
        host="0.0.0.0",
        port=5000,
        reload=False
    )
