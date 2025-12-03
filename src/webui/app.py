
import os
import uuid
from flask import Flask, render_template, request, jsonify, make_response
from werkzeug.utils import secure_filename
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from waitress import serve
from a2wsgi import WSGIMiddleware

# --- 路径修复 ---
# 确保我们能从 webui 包内部正确导入
# (这个相对导入现在由 Python 的包机制处理，但保留路径计算以供其他用途)
current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent.parent.parent # E:\语音转文字

# 相对导入，这是正确的包内导入方式
from .speech_to_text_core import process_audio_file

# --- 初始化 Flask 应用 ---
# 明确指定 templates 文件夹的路径
# 将原始 Flask 应用命名为 flask_app 以便区分
flask_app = Flask(
    __name__,
    template_folder=project_root / "templates"
)

# --- 全局变量和配置 ---
executor = ProcessPoolExecutor(max_workers=2)
tasks = {}

UPLOAD_FOLDER = project_root / 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac'}
ALLOWED_MODELS = {'tiny', 'base', 'small', 'medium', 'large-v1', 'large-v2', 'large-v3'}

flask_app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- 路由和接口 (使用 flask_app) ---

@flask_app.route('/')
def index():
    return render_template('index.html')

@flask_app.route('/upload', methods=['POST'])
def upload_file():
    if 'audioFile' not in request.files:
        return jsonify({'error': '请求中没有文件部分'}), 400
    
    file = request.files['audioFile']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'error': '没有选择文件或文件类型不被允许'}), 400

    model_name = request.form.get('model', 'medium')
    if model_name not in ALLOWED_MODELS: model_name = 'medium'
    
    language = request.form.get('language')
    if language == "": language = None

    use_vad = request.form.get('vad', 'true').lower() == 'true'
    use_demucs = request.form.get('demucs', 'false').lower() == 'true'
    use_gpu = request.form.get('gpu', 'false').lower() == 'true'
    
    try:
        nst = float(request.form.get('no_speech_threshold', '0.6'))
        if not (0.0 <= nst <= 1.0): nst = 0.6
    except (ValueError, TypeError):
        nst = 0.6

    filename = secure_filename(file.filename)
    filepath = os.path.join(flask_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    print(f"文件已上传: {filepath}")

    task_id = str(uuid.uuid4())
    print(f"创建新任务，ID: {task_id}")

    future = executor.submit(
        process_audio_file,
        filepath, model_name, language, use_vad, use_demucs, nst, use_gpu
    )

    tasks[task_id] = {'future': future, 'status': 'RUNNING', 'result': None}
    
    return jsonify({'success': True, 'task_id': task_id})

@flask_app.route('/tasks/<task_id>/status')
def get_task_status(task_id):
    task_info = tasks.get(task_id)
    if not task_info:
        return jsonify({'state': 'NOT_FOUND'}), 404

    future = task_info['future']
    
    if future.done():
        if task_info['status'] not in ['SUCCESS', 'FAILURE']:
            try:
                result_data = future.result()
                if isinstance(result_data, dict) and 'error' in result_data:
                    task_info['status'] = 'FAILURE'
                    task_info['result'] = result_data['error']
                else:
                    task_info['status'] = 'SUCCESS'
                    task_info['result'] = result_data
            except Exception as e:
                task_info['status'] = 'FAILURE'
                task_info['result'] = str(e)
        
        response_data = {'state': task_info['status']}
        if task_info['status'] == 'FAILURE':
            response_data['error'] = task_info['result']
    else:
        response_data = {'state': 'RUNNING'}

    return jsonify(response_data)

@flask_app.route('/tasks/<task_id>/result/<file_type>')
def get_task_result(task_id, file_type):
    task_info = tasks.get(task_id)
    if not task_info or task_info['status'] != 'SUCCESS':
        return jsonify({'error': '任务尚未成功完成'}), 404

    result_data = task_info['result']
    
    if file_type == 'txt':
        content = result_data.get('txt_content', '')
        filename = "result.txt"
    elif file_type == 'srt':
        content = result_data.get('srt_content', '')
        filename = "result.srt"
    elif file_type == 'vtt':
        content = result_data.get('vtt_content', '')
        filename = "result.vtt"
    else:
        return jsonify({'error': '无效的文件类型'}), 400

    response = make_response(content)
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    
    return response

# --- ASGI 兼容性 ---
# 使用 WSGIMiddleware 包装 Flask 应用，使其与 ASGI 服务器 (如 Uvicorn) 兼容。
# Uvicorn 会寻找一个名为 `app` 的可调用对象。
app = WSGIMiddleware(flask_app)

if __name__ == '__main__':
    # --- 基于 waitress 的启动方式 ---
    # 这使得我们可以直接通过 `python -m webui.app` 来启动一个生产级的 WSGI 服务器。
    # 注意这里我们传递的是原始的 `flask_app`。
    print("="*50)
    print("启动 Waitress 生产级 WSGI 服务器...")
    print("请在浏览器中打开 http://0.0.0.0:5000")
    print("="*50)
    serve(flask_app, host='0.0.0.0', port=5000)
