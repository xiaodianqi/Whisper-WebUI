import uvicorn
import multiprocessing
import sys
import os
import webbrowser
from threading import Timer

# --- 关键部分：帮助 PyInstaller 找到正确的路径 ---
# 如果程序被打包了，sys._MEIPASS 会指向解压后的临时文件夹
if getattr(sys, 'frozen', False):
    # 将打包后的 src 目录添加到 Python 路径中
    base_path = sys._MEIPASS
    sys.path.append(os.path.join(base_path, 'src'))
else:
    # 在开发模式下，直接将 src 目录添加到路径
    base_path = os.path.dirname(__file__)
    sys.path.append(os.path.join(base_path, 'src'))

# --- 新增部分：将内置的 FFmpeg 添加到 PATH 作为备用 ---
# 构造 ffmpeg_bin 目录的绝对路径
ffmpeg_bin_path = os.path.join(base_path, 'ffmpeg_bin')
# 将其添加到 PATH 环境变量的末尾。
# 这样系统会优先使用已安装的 ffmpeg，仅在找不到时才使用我们内置的版本。
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
    # 对于使用多进程的打包程序 (您的项目用了 ProcessPoolExecutor)，
    # 在 Windows 上必须调用此函数。
    multiprocessing.freeze_support()

    # 创建一个计时器，在 1.5 秒后执行 open_browser 函数。
    # 这个延迟是为了给 Uvicorn 服务器足够的时间来完成启动。
    Timer(1.5, open_browser).start()

    # 启动 Uvicorn 服务器
    # 这会阻塞主线程，使脚本保持运行，直到服务器关闭。
    uvicorn.run(
        "webui.app:app",
        host="0.0.0.0",
        port=5000,
        reload=False  # 对于打包和稳定运行，reload 应为 False
    )
