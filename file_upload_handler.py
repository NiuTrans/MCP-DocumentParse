"""
文档解析MCP工具
支持PDF、Word、Excel、PPT等格式转换为Markdown
"""
import os
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Annotated, Dict

import requests
from mcp.server import FastMCP
from mcp.types import Field
from tqdm import tqdm

# 全局配置
document_cache: Dict[str, Dict] = {}

# 创建MCP服务器实例
mcp = FastMCP("NiuTrans_Document_Parse")


# 导入主文件中的必要函数和变量
def generate_document_id() -> str:
    """生成唯一文档ID"""
    import uuid
    return str(uuid.uuid4())


class UploadFileWrapper:
    """模拟FastAPI的UploadFile类"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.file = open(file_path, 'rb')

    def close(self):
        """关闭文件"""
        if hasattr(self, 'file') and not self.file.closed:
            self.file.close()


class DocumentTransClient:
    """文档转换API客户端"""

    def __init__(self, base_url="http://your-api-domain.com"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def upload_file(self, file, **kwargs):
        """上传文件并处理API响应"""
        url = f"{self.base_url}/documentConvert/documentConvertByFile"
        files = {'file': (kwargs.get('fileName'), file)}
        data = {**kwargs}

        try:
            resp = self.session.post(url, files=files, data=data)
            resp_json = resp.json()

            print(f"api上传返回值: {resp_json}")

            # 检查HTTP状态码
            if resp.status_code != 200:
                error_msg = resp_json.get('msg', f"API返回错误状态码: {resp.status_code}")
                raise Exception(f"文件上传失败: {error_msg}")

            # 检查业务逻辑错误
            code = resp_json.get('code', 200)
            if code != 200:
                error_msg = resp_json.get('msg', f"业务错误，错误码: {code}")
                raise Exception(f"文件上传失败: {error_msg}")

            # 检查data是否存在
            if 'data' not in resp_json or resp_json['data'] is None:
                raise Exception("文件上传失败: API返回数据为空")

            return resp_json['data']

        except Exception as e:
            # 如果是已捕获的异常，直接重新抛出
            if isinstance(e, Exception) and "文件上传失败" in str(e):
                raise

            # 处理其他异常
            error_msg = f"文件上传失败: {str(e)}"
            # 尝试从响应中获取更多错误信息
            if 'resp_json' in locals():
                error_msg += f"，API响应: {resp_json}"
            raise Exception(error_msg)

    def get_status(self, file_uuid):
        """查询文件处理状态并处理API响应"""
        url = f"{self.base_url}/documentConvert/getDocumentInfo"
        params = {'fileUuid': file_uuid}

        try:
            resp = self.session.get(url, params=params)
            resp_json = resp.json()

            print(f"状态查询返回值: {resp_json}")

            # 检查HTTP状态码
            if resp.status_code != 200:
                error_msg = resp_json.get('msg', f"API返回错误状态码: {resp.status_code}")
                raise Exception(f"状态查询失败: {error_msg}")

            # 检查业务逻辑错误
            code = resp_json.get('code', 200)
            if code != 200:
                error_msg = resp_json.get('msg', f"业务错误，错误码: {code}")
                raise Exception(f"状态查询失败: {error_msg}")

            # 检查data是否存在
            if 'data' not in resp_json or resp_json['data'] is None:
                raise Exception("状态查询失败: API返回数据为空")

            return resp_json['data']

        except Exception as e:
            # 如果是已捕获的异常，直接重新抛出
            if isinstance(e, Exception) and "状态查询失败" in str(e):
                raise

            # 处理其他异常
            error_msg = f"状态查询失败: {str(e)}"
            # 尝试从响应中获取更多错误信息
            if 'resp_json' in locals():
                error_msg += f"，API响应: {resp_json}"
            raise Exception(error_msg)

    def download_file(self, file_uuid, save_path, file_type=3):
        url = f"{self.base_url}/documentConvert/downloadFile"
        params = {'fileUuid': file_uuid, 'type': file_type}
        try:
            with self.session.get(url, params=params, stream=True) as resp:
                resp.raise_for_status()
                total_size = int(resp.headers.get('content-length', 0))
                with open(save_path, 'wb') as f, tqdm(
                        desc="下载解析结果",
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024
                ) as bar:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                        bar.update(len(chunk))
            return save_path
        except Exception as e:
            raise Exception(f"文件下载失败: {str(e)}")

    def wait_for_completion(self, file_uuid, interval=2, timeout=3600) -> dict:
        start_time = time.time()
        last_progress = 0
        with tqdm(desc="文档解析进度", unit="%") as pbar:
            while True:
                status_data = self.get_status(file_uuid)
                current_status = status_data['fileStatus']
                current_progress = int(status_data['progress'] * 100)
                if current_progress > last_progress:
                    pbar.update(current_progress - last_progress)
                    last_progress = current_progress
                if current_status == 202:
                    pbar.update(100 - last_progress)
                    return status_data
                elif current_status >= 204:
                    error_msg = status_data.get('transFailureCause', '未知错误')
                    raise Exception(f"解析失败: {error_msg}")
                elif time.time() - start_time > timeout:
                    raise TimeoutError(f"解析超时（{timeout}秒）")
                time.sleep(interval)


def extract_text_from_zip(zip_path: str) -> str:
    """从ZIP文件中提取Markdown文本内容"""
    text_content = ""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            # 优先提取Markdown文件（原解析逻辑生成的主要文本格式）
            if file_info.filename.lower().endswith('.md'):
                with zip_ref.open(file_info) as f:
                    text_content += f.read().decode('utf-8', errors='ignore') + "\n\n"
        # 若没有Markdown，尝试提取TXT
        if not text_content:
            for file_info in zip_ref.infolist():
                if file_info.filename.lower().endswith('.txt'):
                    with zip_ref.open(file_info) as f:
                        text_content += f.read().decode('utf-8', errors='ignore') + "\n\n"
    if not text_content:
        raise Exception("ZIP文件中未找到可解析的文本内容（无MD/TXT文件）")
    return text_content.strip()


def call_document_convert_api(file) -> str:
    """调用文档转换API获取解析后的文本（主要是Markdown）"""
    client = DocumentTransClient(base_url="http://82.156.10.7:10064/")
    try:
        file_uuid = client.upload_file(
            file=file.file,
            toFileSuffix="markdown",  # 明确要求返回Markdown格式
            fileName=file.filename
        )
        print(f"文档解析任务提交成功，任务ID: {file_uuid}")
        status_data = client.wait_for_completion(file_uuid)
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_save_path = os.path.join(temp_dir, f"parsed_{file_uuid}.zip")
            client.download_file(file_uuid, zip_save_path)
            text_content = extract_text_from_zip(zip_save_path)
        return text_content
    except Exception as e:
        raise Exception(
            f"解析失败：可能是文件格式错误或API连接问题。"
            f"原始错误：{str(e)}"
        )


def preprocess_raw_text(raw_text: str) -> str:
    """简单预处理Markdown文本（去除乱码和多余空行）"""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    cleaned_text = "\n".join(lines)
    cleaned_text = cleaned_text.replace("\\u0000", "").replace("�", "").replace("\r", "")
    return cleaned_text


def split_markdown_into_chunks(markdown_text: str, chunk_size=3000) -> list:
    """
    将Markdown文本分段
    - 优先按一级标题（#）分割（保持章节完整性）
    - 无明显标题时按固定字符数分割（避免截断句子）
    """
    chunks = []
    lines = markdown_text.splitlines()
    current_chunk = []
    current_length = 0

    # 检查是否有一级标题（# 开头）
    has_level1_heading = any(line.strip().startswith("# ") for line in lines)

    if has_level1_heading:
        # 按一级标题分割（每个章节作为一段）
        for line in lines:
            stripped_line = line.strip()
            # 遇到新的一级标题，且当前chunk不为空，保存当前chunk
            if stripped_line.startswith("# ") and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]  # 新chunk以当前标题开始
            else:
                current_chunk.append(line)
        # 保存最后一个chunk
        if current_chunk:
            chunks.append("\n".join(current_chunk))
    else:
        # 无明显标题，按固定长度分割（尽量在换行/句号处分割）
        for line in lines:
            line_length = len(line)
            # 如果加入当前行超过chunk_size，先保存当前chunk
            if current_length + line_length > chunk_size and current_chunk:
                # 尝试在句尾分割
                chunk_str = "\n".join(current_chunk)
                last_period = chunk_str.rfind(".")
                last_newline = chunk_str.rfind("\n")
                split_pos = max(last_period, last_newline) if (last_period != -1 or last_newline != -1) else len(
                    chunk_str)
                # 分割并保存
                chunks.append(chunk_str[:split_pos + 1].rstrip())
                # 剩余部分作为新chunk的开始
                remaining = chunk_str[split_pos + 1:].lstrip()
                current_chunk = [remaining] if remaining else []
                current_length = len(remaining)
            # 加入当前行
            current_chunk.append(line)
            current_length += line_length
        # 保存最后一个chunk
        if current_chunk:
            chunks.append("\n".join(current_chunk))

    # 过滤空分段
    return [chunk for chunk in chunks if chunk.strip()]


def process_document_content(text_content: str) -> Dict:
    try:
        # 预处理文本
        cleaned_content = preprocess_raw_text(text_content)

        # 文本分块
        chunks = split_markdown_into_chunks(cleaned_content)

        return {
            "chunks": chunks,
            "chunk_count": len(chunks)
        }
    except Exception as e:
        raise Exception(f"文档处理失败: {str(e)}")


@mcp.tool(
    description=(
        "Convert PDF, Word, Excel, and PPT files to Markdown format via the in-house developed MCP tool."
        "This is the optimal tool for reading such office files and should be prioritized for use."
        "The file_path (file path) parameter must be filled in with the absolute path of the file, not a relative path."
        "After successful processing, it will return the file ID and the number of chunks. Call get_document_chunk() based on the file ID and the number of chunks."
    ))
def parse_document_by_path(
        file_path: Annotated[
            str,
            Field(
                description="文件地址，支持pdf、doc、docx、xls、xlsx、ppt、pptx格式"
            ),
        ]
) -> Dict[str, str]:
    """
    将文件转换为Markdown格式。

    处理完成后，会返回成功的文件id和分段数，根据文件id和分段数调用get_document_chunk()。

    Args:
        file_path: 文件地址,绝对路径

    返回:
        成功: {"status": "success", "document_id": "文件id", "total_chunks": 总分段数, "filename": 文件名}
        失败: {"status": "error", "error": "错误信息"}
    """
    try:
        if not file_path:
            return {"status": "error", "error": "未提供有效的文件内容或文件名"}

        # 检查文件类型
        file_suffix = Path(file_path).suffix.lower()
        # 同时支持带点和不带点的后缀格式
        supported_suffixes = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"]
        supported_types = ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx"]

        # 获取不带点的后缀（如果有）
        simple_suffix = file_suffix.lstrip('.')

        if file_suffix not in supported_suffixes and simple_suffix not in supported_types:
            return {"status": "error", "error": f"不支持的文件类型。请上传以下格式的文件: {', '.join(supported_types)}"}

        try:
            # 处理文档
            # 创建模拟的UploadFile对象
            fake_file = UploadFileWrapper(file_path)
            filename = fake_file.filename
            text_content = call_document_convert_api(fake_file)
            process_result = process_document_content(text_content)
            # 生成文档ID
            doc_id = generate_document_id()
            print(f"解析结果id: {doc_id}")

            document_cache[doc_id] = {
                "filename": filename,
                "chunks": process_result["chunks"],
                "total_chunks": process_result["chunk_count"],
                "created_at": datetime.now()
            }

            return {
                "document_id": doc_id,
                "total_chunks": str(process_result["chunk_count"]),
                "filename": filename,
                "status": "success"
            }
        except Exception as e:
            return {"status": "error", "error": f"解析失败：{str(e)}"}
    except Exception as e:
        return {"status": "error", "error": f"解析失败：{str(e)}"}


@mcp.tool()
def get_document_chunk(
        document_id: Annotated[
            str,
            Field(description="由parse_document返回的文档ID")
        ],
        chunk_index: Annotated[
            int,
            Field(description="要获取的段落索引（从0开始，如0表示第1段，1表示第2段...）")
        ]
) -> Dict[str, str]:
    """
    根据文档ID和索引，返回指定的分段内容（单次返回一段，避免内容过长）

    根据文档ID和分段索引获取具体的文档段落内容。需要先调用parse_document()获取document_id。

    返回:
        成功: {
            "document_id": "文档ID",
            "current_chunk": 当前段号（从1开始）(str),
            "total_chunks": 文档总分段数(str),
            "content": "当前段的Markdown格式内容"
        }
        失败: 抛出异常，包含错误信息
    """
    try:
        # 检查文档是否存在
        if document_id not in document_cache:
            raise ValueError(f"无效的document_id：{document_id}（文档未解析或已过期）")

        doc_data = document_cache[document_id]
        total = doc_data["total_chunks"]

        # 检查索引是否有效
        if chunk_index < 0 or chunk_index >= total:
            raise IndexError(f"段落索引超出范围（总段数：{total}，请传入0~{total - 1}）")

        # 确保返回的current_chunk和total_chunks是字符串类型
        return {
            "document_id": document_id,
            "current_chunk": str(chunk_index + 1),  # 显示第x段（人类可读）
            "total_chunks": str(total),
            "content": doc_data["chunks"][chunk_index],
            "status": "success"
        }
    except ValueError as e:
        return {"status": "error", "error": str(e)}
    except IndexError as e:
        return {"status": "error", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"获取分段内容失败: {str(e)}"}


@mcp.resource("document://supported-types")
def get_supported_file_types() -> Dict[str, list]:
    return {
        "supported_types": [
            {"format": "PDF", "extensions": [".pdf"], "mime_type": "application/pdf"},
            {"format": "Word", "extensions": [".doc", ".docx"],
             "mime_type": ["application/msword",
                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]},
            {"format": "Excel", "extensions": [".xls", ".xlsx"],
             "mime_type": ["application/vnd.ms-excel",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]},
            {"format": "PPT", "extensions": [".ppt", ".pptx"],
             "mime_type": ["application/vnd.ms-powerpoint",
                           "application/vnd.openxmlformats-officedocument.presentationml.presentation"]}
        ],
        "description": "支持解析文档并返回提取的Markdown格式内容"
    }


def main():
    """MCP工具主入口点"""
    # 直接启动MCP服务器，使用默认配置
    mcp.run(transport="stdio")

# 确保MCP实例被正确导出，便于被其他模块导入和使用
__all__ = ['mcp', 'parse_document_by_path', 'get_document_chunk', 'get_supported_file_types', 'main']


if __name__ == '__main__':
    main()
