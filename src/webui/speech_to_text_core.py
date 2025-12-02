
import time
import os
import stable_whisper
import torch

def format_srt_time(seconds):
    """ 将秒数转换为SRT字幕的时间格式 (HH:MM:SS,ms) """
    assert seconds >= 0, "non-negative timestamp expected"
    milliseconds = round(seconds * 1000.0)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def process_audio_file(
    audio_file_path,
    model_name="medium",
    language=None,
    use_vad=True,
    use_demucs=False,
    no_speech_threshold=0.6,
    use_gpu=False # 新增 use_gpu 参数
):
    """
    一个参数化的、可定制的核心识别函数，现已支持GPU加速选项。
    """
    # --- 动态设备和参数选择 ---
    device = "cpu"
    if use_gpu:
        if torch.cuda.is_available():
            print("检测到 CUDA，将使用 GPU 加速。")
            device = "cuda"
        else:
            print("警告: 请求使用 GPU，但未检测到 CUDA。将回退到 CPU。")
    
    fp16_mode = True if device == "cuda" else False

    print("="*50)
    print(f"核心模块接收到新任务: {os.path.basename(audio_file_path)}")
    lang_display = language if language else "自动检测"
    print(f"配置: 模型='{model_name}', 语言='{lang_display}', 设备='{device.upper()}'")
    print(f"      Silero-VAD={'启用' if use_vad else '禁用'}, Demucs={'启用' if use_demucs else '禁用'}, FP16={'启用' if fp16_mode else '禁用'}")
    if not use_vad:
        print(f"      Whisper原生VAD灵敏度阈值: {no_speech_threshold}")
    print("="*50)

    # 1. 加载指定大小的模型到指定设备
    try:
        print(f"正在加载 Whisper '{model_name}' 模型到 {device.upper()}...")
        model = stable_whisper.load_model(model_name, device=device)
    except Exception as e:
        return {'error': f"错误: 加载模型失败。详情: {e}"}

    print("模型加载完毕。开始进行语音识别...")

    # 2. 构建 transcribe 函数的参数字典
    transcribe_args = {
        'fp16': fp16_mode,
        'vad': use_vad,
        'demucs': use_demucs,
    }
    if language:
        transcribe_args['language'] = language
    if not use_vad:
        transcribe_args['no_speech_threshold'] = no_speech_threshold

    # 3. 进行识别
    start_time = time.time()
    try:
        print(f"正在使用以下参数进行识别: {transcribe_args}")
        result = model.transcribe(audio_file_path, **transcribe_args)
    except Exception as e:
        return {'error': f"错误: 识别过程中发生错误。详情: {e}"}
    end_time = time.time()
    
    print(f"识别完成，耗时: {end_time - start_time:.2f} 秒。")

    # 4. 使用 regroup() 优化断句
    print("正在智能地重新分割长句子以优化字幕...")
    result = result.regroup()

    # 5. 生成 SRT 和 TXT 内容
    txt_content = result.text
    srt_content_lines = []
    for i, segment in enumerate(result.segments):
        start_time_srt = format_srt_time(segment.start)
        end_time_srt = format_srt_time(segment.end)
        text = segment.text.strip()
        
        if not text: continue
        
        srt_content_lines.append(f"{i + 1}")
        srt_content_lines.append(f"{start_time_srt} --> {end_time_srt}")
        srt_content_lines.append(f"{text}\n")
    
    srt_content = "\n".join(srt_content_lines)

    print(f"核心模块处理完成: {os.path.basename(audio_file_path)}")
    
    # 6. 返回结果字典
    return {
        'txt_content': txt_content,
        'srt_content': srt_content
    }
