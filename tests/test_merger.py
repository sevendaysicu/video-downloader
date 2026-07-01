"""切片合并模块单元测试"""
import os
import tempfile

from app.merger import merge_slices


def _create_test_slices(directory, count=5, content_size=64):
    """在指定目录创建测试用的 .bin 切片文件"""
    for i in range(1, count + 1):
        path = os.path.join(directory, f"CLS-{i:03d}.bin")
        with open(path, "wb") as f:
            # 每个切片写入可辨识的内容：索引号重复 content_size 次
            f.write(bytes([i]) * content_size)


class TestMergeSlices:
    """merge_slices 函数测试"""

    def test_merge_produces_correct_output(self, tmp_path):
        """合并后文件内容应为各切片按序拼接"""
        _create_test_slices(str(tmp_path), count=3, content_size=32)
        output_path, count = merge_slices(str(tmp_path))

        assert count == 3
        assert os.path.exists(output_path)
        assert output_path.endswith(".mp4")

        with open(output_path, "rb") as f:
            data = f.read()
        # 3 个切片 × 32 字节 = 96 字节
        assert len(data) == 96
        # 内容按切片顺序拼接
        assert data[:32] == bytes([1]) * 32
        assert data[32:64] == bytes([2]) * 32
        assert data[64:96] == bytes([3]) * 32

    def test_merge_sorts_by_filename(self, tmp_path):
        """切片应按文件名排序合并，不受创建顺序影响"""
        # 故意倒序创建
        for i in [3, 1, 2]:
            path = os.path.join(str(tmp_path), f"CLS-{i:03d}.bin")
            with open(path, "wb") as f:
                f.write(bytes([i]) * 8)

        output_path, count = merge_slices(str(tmp_path))

        with open(output_path, "rb") as f:
            data = f.read()
        # 即使创建顺序为 3,1,2，合并结果应为 1,2,3
        assert data == bytes([1]) * 8 + bytes([2]) * 8 + bytes([3]) * 8

    def test_merge_custom_output_path(self, tmp_path):
        """自定义输出路径应生效"""
        _create_test_slices(str(tmp_path), count=2, content_size=16)
        custom_path = os.path.join(str(tmp_path), "my_video.mp4")

        output_path, count = merge_slices(str(tmp_path), output_path=custom_path)

        assert output_path == custom_path
        assert os.path.exists(custom_path)
        assert count == 2

    def test_merge_empty_directory(self, tmp_path):
        """空目录应返回 0 个文件（生成空 MP4）"""
        output_path, count = merge_slices(str(tmp_path))
        assert count == 0
        # 空合并产生空文件
        assert os.path.getsize(output_path) == 0

    def test_merge_ignores_non_bin_files(self, tmp_path):
        """非 .bin 文件不应被合并"""
        _create_test_slices(str(tmp_path), count=2, content_size=16)
        # 创建干扰文件
        with open(os.path.join(str(tmp_path), "readme.txt"), "w") as f:
            f.write("should be ignored")
        with open(os.path.join(str(tmp_path), "data.json"), "w") as f:
            f.write("{}")

        _, count = merge_slices(str(tmp_path))
        assert count == 2  # 只计入 .bin 文件

    def test_merge_auto_generates_output_name(self, tmp_path):
        """自动生成的输出路径应基于目录名"""
        slice_dir = os.path.join(str(tmp_path), "slices_abc123")
        os.makedirs(slice_dir)
        _create_test_slices(slice_dir, count=1, content_size=8)

        output_path, _ = merge_slices(slice_dir)

        # slices_abc123 → video_abc123.mp4
        assert os.path.basename(output_path) == "video_abc123.mp4"

    def test_merge_progress_callback(self, tmp_path):
        """on_progress 回调应对每个切片调用一次"""
        _create_test_slices(str(tmp_path), count=4, content_size=16)
        progress_calls = []

        merge_slices(
            str(tmp_path),
            on_progress=lambda cur, tot: progress_calls.append((cur, tot)),
        )

        assert len(progress_calls) == 4
        assert progress_calls[0] == (1, 4)
        assert progress_calls[-1] == (4, 4)
