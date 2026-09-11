# GenSpec

GenSpec 是一个基于 Chainlit + LangGraph 的智能文档生成工具，可以根据用户上传的源文档，自动生成项目特定的标准化文档。

## ✨ 功能特性

- **智能文档解析**：自动解析 Markdown 格式的源文档
- **多文档类型支持**：支持生成 SRS、BRD、TRS、TDD 等多种文档类型
- **LangGraph 工作流**：基于 LangGraph 编排文档生成流程
- **交互式对话**：通过 Chainlit 提供友好的交互界面
- **智能信息提取**：自动从源文档中提取关键信息
- **文档审查优化**：自动生成并优化生成的文档
- **一键下载**：支持下载生成的 Markdown 文档

## 📋 支持的文档类型

| 类型 | 名称 | 描述 |
|------|------|------|
| SRS | 软件需求规格说明书 | 详细描述软件系统的功能和非功能需求 |
| BRD | 业务需求文档 | 描述业务目标、范围和利益相关者需求 |
| TRS | 技术需求规格说明书 | 描述系统的技术需求和架构 |
| TDD | 技术设计文档 | 描述系统的技术设计和架构决策 |

## 🚀 快速开始

### 环境要求

- Python 3.12+
- 兼容 OpenAI API 的 LLM 服务

### 安装

1. 克隆项目
```bash
git clone <repository-url>
cd GenSpec
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置您的 LLM API：
```
API_KEY=your_api_key_here
BASE_URL=https://your-llm-api.com/v1
MODEL=your-model-name
```

### 运行

```bash
chainlit run app.py -w
```

## 📖 使用指南

### 基本流程

1. **启动聊天**：运行命令后，浏览器会自动打开聊天界面
2. **上传文档**：上传一个 Markdown 格式的源文档
3. **输入指令**：告诉系统您需要生成什么类型的文档
   - 例如："根据这个生成 SRS 文档"
   - 例如："请生成业务需求文档 BRD"
4. **等待生成**：系统会自动分析并生成文档
5. **下载结果**：查看生成的文档并下载

### 示例对话

```
用户: [上传文件: requirement.md]
用户: 根据这个生成 SRS 文档

系统: ✅ 文件上传成功！
系统: 🔄 正在开始文档生成流程...
系统: ✅ 文档生成完成！
[显示生成的文档预览]
[提供下载链接]
```

## 🏗️ 项目结构

```
GenSpec/
├── app.py                      # Chainlit 主入口
├── config.py                   # 配置管理
├── chainlit.md                 # 欢迎页
├── .env.example                # 环境变量模板
├── requirements.txt            # 依赖
├── pyproject.toml              # 项目配置
├── graph/
│   ├── __init__.py
│   ├── builder.py              # Graph 构建
│   ├── nodes.py                # 节点函数
│   └── states.py               # State 定义
├── processors/
│   ├── __init__.py
│   └── markdown_parser.py      # Markdown 解析
├── templates/
│   ├── __init__.py
│   └── doc_templates.py        # 文档模板定义
└── utils/
    ├── __init__.py
    └── llm.py                  # LLM 封装
```

## 🔧 工作流说明

GenSpec 使用 LangGraph 编排以下工作流程：

1. **验证输入**：检查项目信息是否完整
2. **解析文档**：解析上传的 Markdown 源文档
3. **提取关键点**：使用 LLM 提取源文档的关键信息
4. **生成文档**：根据模板和提取的信息生成目标文档
5. **审查优化**：审查并优化生成的文档
6. **返回结果**：展示结果并提供下载

## 📝 文档模板

每个文档类型都有预定义的模板，包含：
- System Prompt：指导 LLM 如何生成文档
- Structure：文档结构和章节大纲

模板定义在 `templates/doc_templates.py` 中。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License