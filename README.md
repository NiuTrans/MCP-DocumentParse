# MCP Document Parse Tool

## 项目介绍

这是一个MCP（Model Communication Protocol）工具，用于帮助解析各种格式的文档（PDF、Word、Excel、PPT等）获取其内容。该工具提供了简单易用的接口，使您能够在各种应用中集成文档解析功能。

## 支持的文件格式

- PDF (.pdf) - 支持可编辑 PDF 和扫描件
- Word (.doc, .docx)
- Excel (.xls, .xlsx)
- PowerPoint (.ppt, .pptx)

## 安装方法

### 使用 uv 安装并启动发布版

```bash
uv tool install mcp-document-parse
```

## 环境变量

- `NIUTRANS_API_KEY`（必填）：小牛翻译开放平台提供文档API的 API Key,可免费使用, 请登录后获取:https://niutrans.com/cloud/api/list
- `NIUTRANS_DOCUMENT_APPID`（必填）：小牛翻译开放平台提供文档API的 APPID,可免费使用, 请登录后获取:https://niutrans.com/cloud/api/list

## 计费说明

本工具使用小牛翻译开放平台的文档解析 API，计费规则如下：

| 文件类型 | 计费标准 |
|---------|---------|
| PDF / Word / PPT | 1 页 = 2 积分 |
| Excel | 2000 字符 = 2 积分 |

> 💡 **免费额度**：平台每天赠送 **100 积分**，供大家免费使用！

## 环境要求

- Python >= 3.9
- 依赖项已在 `pyproject.toml` 中定义

## MCP 客户端配置示例

若通过 `uv tool install` 安装，可在 `mcp.json` 中配置：

```json
{
  "mcpServers": {
    "document_parse": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "tool",
        "run",
        "mcp-document-parse"
      ],
      "env": {
        "NIUTRANS_API_KEY": "${env.NIUTRANS_API_KEY}",
        "NIUTRANS_DOCUMENT_APPID": "${env.NIUTRANS_DOCUMENT_APPID}"
      }
    }
  }
}
```

启动支持MCP的应用后，执行 `ListTools` 即可看到 `parse_document_by_path` 工具，同时支持 `ListResources` 读取 `document://supported-types`。


## 工具说明

### parse_document_by_path

将指定路径的文件转换为Markdown格式。

**参数：**
- `file_path` (str): 文件的绝对路径，支持pdf、doc、docx、xls、xlsx、ppt、pptx格式

**返回：**
- 成功: `{"status": "success", "text_content": "文件内容", "filename": 文件名}`
- 失败: `{"status": "error", "error": "错误信息"}`


### document://supported-types

获取支持的文件类型信息。

**返回：**
- 包含支持的文件类型列表及其描述的JSON对象

## 许可证

MIT License

## 联系方式

如有问题或建议，请联系 tianfengning@niutrans.com
