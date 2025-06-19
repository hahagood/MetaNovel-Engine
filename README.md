# MetaNovel-Engine

![Version](https://img.shields.io/badge/version-v0.0.1-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

AI辅助小说创作引擎 - 结构化、分阶段的长篇小说创作工具链

## 🎯 项目简介

**当前版本：v0.0.1（原型版本）**

本项目提供一套完整的AI辅助小说创作工具链，通过结构化的7步流程，帮助作家从一个简单的想法逐步扩展为完整的小说作品。采用JSON格式存储各阶段数据，有效节省上下文tokens、降低AI幻觉率，以工程化方式打磨故事。

## ✨ 核心特性

- **🎯 渐进式创作流程**：7个步骤层层递进，从主题构思到完整小说
- **🌍 完整世界设定**：角色、场景、道具三位一体的世界构建系统
- **📊 结构化数据管理**：所有创作元素以JSON格式存储，便于管理和复用
- **🤖 AI智能辅助**：集成OpenRouter API，支持多种大语言模型
- **🔗 上下文压缩**：通过结构化数据有效压缩上下文，避免长文本生成中的遗忘问题
- **⚡ 一键生成**：整合所有元数据，快速输出连贯的小说正文
- **🎮 交互式CLI**：友好的命令行界面，支持完整的CRUD操作

## 🚀 创作流程

### 第1步：确立一句话主题
- 定义小说的核心理念
- 为整个故事奠定基调

### 第2步：扩展成一段话主题  
- 将核心理念扩展为详细的主题描述
- 明确故事的主要方向和价值观

### 第3步：世界设定
- **角色管理**：创建和管理小说中的重要人物
- **场景管理**：设计故事发生的重要地点和环境
- **道具管理**：定义关键物品、武器、神器等元素

### 第4步：编辑故事大纲
- 基于主题和世界设定创建500-800字的详细故事框架
- 包含背景设定、主要情节线索、关键转折点等

### 第5步：编辑分章细纲
- 将故事分解为5-10个章节
- 每个章节包含标题和150-200字的详细大纲

### 第6步：编辑章节概要
- 为每个章节生成300-500字的详细概要
- 包含场景设定、角色行动、情节发展、对话要点等

### 第7步：生成小说正文
- 基于所有前期准备生成2000-4000字的完整章节正文
- 支持单章节或批量生成
- 提供完整的编辑和导出功能

## 📁 项目结构

```
MetaNovel-Engine/
├── meta/                      # 创作数据存储目录
│   ├── theme_one_line.json    # 一句话主题
│   ├── theme_paragraph.json   # 段落主题
│   ├── characters.json        # 角色信息
│   ├── locations.json         # 场景信息
│   ├── items.json             # 道具信息
│   ├── story_outline.json     # 故事大纲
│   ├── chapter_outline.json   # 分章细纲
│   ├── chapter_summary.json   # 章节概要
│   └── novel_text.json        # 小说正文
├── meta_novel_cli.py          # 主程序CLI脚本
├── requirements.txt           # Python依赖
├── README.md                  # 项目说明
└── LICENSE                    # 开源协议
```

## 🛠️ 安装与使用

### 环境要求
- Python 3.8+
- OpenRouter API密钥

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/MetaNovel-Engine.git
   cd MetaNovel-Engine
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置API密钥**
   ```bash
   export OPENROUTER_API_KEY="your-api-key-here"
   ```

4. **运行程序**
   ```bash
   python meta_novel_cli.py
   ```

### 使用说明

程序启动后会显示交互式菜单，按照1-7的步骤顺序进行创作：

```
请选择您要进行的操作:
  1. 确立一句话主题
  2. 扩展成一段话主题  
  3. 世界设定
  4. 编辑故事大纲
  5. 编辑分章细纲
  6. 编辑章节概要
  7. 生成小说正文
  8. 退出
```

每个步骤都有完整的管理功能，支持查看、编辑、删除等操作。程序会自动检查前置条件，确保创作流程的完整性。

## 🎨 功能特色

### 智能依赖检查
- 每个步骤都会检查前置条件
- 确保创作流程的逻辑完整性
- 避免跳步造成的信息缺失

### 上下文信息整合
- AI生成时自动整合所有相关信息
- 包含主题、角色、场景、道具、大纲等完整上下文
- 确保生成内容的一致性和连贯性

### 灵活的编辑功能
- 支持对所有生成内容的查看、编辑、删除
- 提供用户自定义提示词功能
- 支持重新生成和批量操作

### 完善的导出功能
- 智能文件命名（小说名_章节范围_时间戳）
- 完整的元数据信息
- 支持单章节或全本导出

## 🔧 配置说明

### API配置
程序支持OpenRouter平台的多种模型，默认使用`google/gemini-2.5-pro-preview-06-05`。

### 数据存储
所有创作数据存储在`meta/`目录下的JSON文件中，便于备份和版本管理。

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

## 📄 许可证

本项目采用MIT License，详见[LICENSE](LICENSE)文件。

## 📝 版本历史

### v0.0.1 (2024-12-19)
- 🎉 首个原型版本发布
- ✨ 实现完整的7步创作流程
- 🌍 支持世界设定管理（角色、场景、道具）
- 🔗 智能依赖检查和上下文整合
- 📊 结构化数据存储和管理
- 🤖 OpenRouter API集成
- 🎮 交互式CLI界面

## 🙏 致谢

感谢所有为这个项目贡献想法和代码的开发者们！

---

**开始您的AI辅助小说创作之旅吧！** 🚀
