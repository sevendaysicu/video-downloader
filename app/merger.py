"""切片文件合并模块"""
import os

# 8KB 分块读写，避免大切片一次性加载到内存
_CHUNK_SIZE = 8192


def merge_slices(save_dir, output_path=None, on_progress=None):
    """将 .bin 切片文件按文件名排序后流式合并为 MP4

    Args:
        save_dir: 切片所在目录
        output_path: 输出文件路径，None 时自动生成
        on_progress: 可选的进度回调 (current_file_index, total_files)

    Returns:
        (output_path, file_count) 二元组
    """
    files = sorted(f for f in os.listdir(save_dir) if f.endswith(".bin"))

    if output_path is None:
        parent_dir = os.path.dirname(save_dir)
        video_name = os.path.basename(save_dir).replace("slices_", "video_")
        output_path = os.path.join(parent_dir, f"{video_name}.mp4")

    total = len(files)
    with open(output_path, "wb") as out_f:
        for idx, fname in enumerate(files, 1):
            with open(os.path.join(save_dir, fname), "rb") as in_f:
                # 流式分块写入，不将整个切片加载到内存
                while True:
                    chunk = in_f.read(_CHUNK_SIZE)
                    if not chunk:
                        break
                    out_f.write(chunk)
            if on_progress:
                on_progress(idx, total)

    return output_path, total
