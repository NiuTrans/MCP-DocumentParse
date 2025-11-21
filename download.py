import os
import requests
from tqdm import tqdm
from pathlib import Path


def validate_url(url):
    """验证URL格式"""
    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL必须以http://或https://开头")
    return url


def create_directory(directory):
    """创建目录（如果不存在）"""
    try:
        Path(directory).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        print(f"创建目录失败: {e}")
        return False


def get_filename_from_url(url):
    """从URL中提取文件名"""
    try:
        # 移除URL参数
        clean_url = url.split('?')[0].split('#')[0]
        # 提取文件名
        filename = os.path.basename(clean_url)

        # 如果文件名不明确，使用默认名称
        if not filename or filename.count('.') == 0:
            filename = "downloaded_file"

        return filename
    except Exception:
        return "downloaded_file"


def download_file(url, save_directory, filename=None, chunk_size=1024 * 1024):
    """
    下载文件到指定目录并返回完整的文件保存路径

    Args:
        url (str): 文件URL
        save_directory (str): 保存目录
        filename (str): 可选，指定文件名
        chunk_size (int): 分块大小，默认为1MB

    Returns:
        str: 成功时返回完整的文件保存路径，失败时返回None
    """
    try:
        # 验证URL
        validate_url(url)

        # 创建保存目录
        if not create_directory(save_directory):
            return None

        # 确定文件名
        if not filename:
            filename = get_filename_from_url(url)

        # 完整保存路径
        save_path = os.path.abspath(os.path.join(save_directory, filename))

        # 检查文件是否已存在
        if os.path.exists(save_path):
            overwrite = input(f"文件 '{save_path}' 已存在，是否覆盖? (y/n): ").lower()
            if overwrite != 'y':
                print("下载已取消")
                return None

        print(f"开始下载: {url}")
        print(f"保存路径: {save_path}")

        # 发送请求
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()  # 检查HTTP错误

        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))

        # 创建进度条
        progress_bar = tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=filename
        )

        # 下载文件
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    file.write(chunk)
                    progress_bar.update(len(chunk))

        progress_bar.close()
        print(f"\n✅ 文件下载成功!")
        print(f"📁 保存位置: {save_path}")

        # 返回完整的文件保存路径
        return save_path

    except requests.exceptions.RequestException as e:
        print(f"\n❌ 下载失败: {e}")
        return None
    except ValueError as e:
        print(f"\n❌ 参数错误: {e}")
        return None
    except KeyboardInterrupt:
        print(f"\n❌ 下载被用户取消")
        # 清理不完整的文件
        if 'save_path' in locals() and os.path.exists(save_path):
            os.remove(save_path)
        return None
    except Exception as e:
        print(f"\n❌ 未知错误: {e}")
        return None


# 使用示例
if __name__ == "__main__":
    # 示例1：基本使用
    file_path = download_file(
        url="https://example.com/file.zip",
        save_directory="downloads"
    )
    if file_path:
        print(f"返回的文件地址: {file_path}")

    # 示例2：指定文件名
    file_path2 = download_file(
        url="https://example.com/data.csv",
        save_directory="data",
        filename="custom_data.csv"
    )
    if file_path2:
        print(f"返回的文件地址: {file_path2}")