"""
UI工具模块 - 使用Rich库美化命令行界面
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich.tree import Tree
from rich.columns import Columns
from rich.align import Align
from typing import List, Dict, Any, Optional
import json
import sys
import os
import subprocess
import tempfile
import shutil

# 创建全局console实例
console = Console()

# 颜色主题
class Colors:
    SUCCESS = "green"
    ERROR = "red"
    WARNING = "yellow"
    INFO = "blue"
    HIGHLIGHT = "magenta"
    MUTED = "dim"
    ACCENT = "cyan"


class UIUtils:
    """UI工具类"""
    
    @staticmethod
    def print_success(message: str):
        """打印成功消息"""
        console.print(f"✅ {message}", style=Colors.SUCCESS)
    
    @staticmethod
    def print_error(message: str):
        """打印错误消息"""
        console.print(f"❌ {message}", style=Colors.ERROR)
    
    @staticmethod
    def print_warning(message: str):
        """打印警告消息"""
        console.print(f"⚠️  {message}", style=Colors.WARNING)
    
    @staticmethod
    def print_info(message: str):
        """打印信息消息"""
        console.print(f"ℹ️  {message}", style=Colors.INFO)
    
    @staticmethod
    def print_highlight(message: str):
        """打印高亮消息"""
        console.print(message, style=Colors.HIGHLIGHT)
    
    @staticmethod
    def print_muted(message: str):
        """打印灰色消息"""
        console.print(message, style=Colors.MUTED)
    
    @staticmethod
    def print_panel(content: str, title: str = "", style: str = ""):
        """打印面板"""
        panel = Panel(content, title=title, style=style)
        console.print(panel)
    
    @staticmethod
    def print_markdown(content: str):
        """打印Markdown内容"""
        md = Markdown(content)
        console.print(md)
    
    @staticmethod
    def print_json(data: Dict[str, Any], title: str = ""):
        """美化打印JSON数据"""
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
        if title:
            UIUtils.print_panel(syntax, title=title)
        else:
            console.print(syntax)
    
    @staticmethod
    def create_table(title: str, columns: List[str]) -> Table:
        """创建表格"""
        table = Table(title=title, show_header=True, header_style="bold magenta")
        for column in columns:
            table.add_column(column, style="cyan", no_wrap=True)
        return table
    
    @staticmethod
    def print_characters_table(characters: Dict[str, Dict[str, Any]]):
        """打印角色表格"""
        if not characters:
            UIUtils.print_warning("暂无角色数据")
            return
        
        table = UIUtils.create_table("🎭 角色列表", ["序号", "角色名", "描述预览", "创建时间"])
        
        for i, (name, char_data) in enumerate(characters.items(), 1):
            description = char_data.get("description", "")
            # 截取描述的前50个字符
            desc_preview = (description[:50] + "...") if len(description) > 50 else description
            created_at = char_data.get("created_at", "未知")
            
            table.add_row(
                str(i),
                f"[bold]{name}[/bold]",
                desc_preview,
                created_at
            )
        
        console.print(table)
    
    @staticmethod
    def print_locations_table(locations: Dict[str, Dict[str, Any]]):
        """打印场景表格"""
        if not locations:
            UIUtils.print_warning("暂无场景数据")
            return
        
        table = UIUtils.create_table("🏞️ 场景列表", ["序号", "场景名", "描述预览", "创建时间"])
        
        for i, (name, loc_data) in enumerate(locations.items(), 1):
            description = loc_data.get("description", "")
            desc_preview = (description[:50] + "...") if len(description) > 50 else description
            created_at = loc_data.get("created_at", "未知")
            
            table.add_row(
                str(i),
                f"[bold]{name}[/bold]",
                desc_preview,
                created_at
            )
        
        console.print(table)
    
    @staticmethod
    def print_items_table(items: Dict[str, Dict[str, Any]]):
        """打印道具表格"""
        if not items:
            UIUtils.print_warning("暂无道具数据")
            return
        
        table = UIUtils.create_table("⚔️ 道具列表", ["序号", "道具名", "描述预览", "创建时间"])
        
        for i, (name, item_data) in enumerate(items.items(), 1):
            description = item_data.get("description", "")
            desc_preview = (description[:50] + "...") if len(description) > 50 else description
            created_at = item_data.get("created_at", "未知")
            
            table.add_row(
                str(i),
                f"[bold]{name}[/bold]",
                desc_preview,
                created_at
            )
        
        console.print(table)
    
    @staticmethod
    def print_chapters_table(chapters: List[Dict[str, Any]]):
        """打印章节表格"""
        if not chapters:
            UIUtils.print_warning("暂无章节数据")
            return
        
        table = UIUtils.create_table("📚 章节列表", ["章节", "标题", "大纲预览", "创建时间"])
        
        for chapter in chapters:
            title = chapter.get("title", "")
            outline = chapter.get("outline", "")
            outline_preview = (outline[:60] + "...") if len(outline) > 60 else outline
            created_at = chapter.get("created_at", "未知")
            order = chapter.get("order", 0)
            
            table.add_row(
                f"第{order}章",
                f"[bold]{title}[/bold]",
                outline_preview,
                created_at
            )
        
        console.print(table)
    
    @staticmethod
    def print_project_status(status_details: Dict[str, Dict]):
        """打印项目状态"""
        table = UIUtils.create_table("📊 项目进度", ["步骤", "状态", "详细信息"])
        
        steps = {
            "theme_one_line": "1. 确立一句话主题",
            "theme_paragraph": "2. 扩展成一段话主题",
            "world_settings": "3. 世界设定",
            "story_outline": "4. 编辑故事大纲",
            "chapter_outline": "5. 编辑分章细纲",
            "chapter_summaries": "6. 编辑章节概要",
            "novel_chapters": "7. 生成小说正文"
        }
        
        completed_count = 0
        total_count = len(steps)
        
        for key, step_name in steps.items():
            status_info = status_details.get(key, {"completed": False, "details": "状态未知"})
            is_complete = status_info.get("completed", False)
            details = status_info.get("details", "状态未知")
            
            if is_complete:
                completed_count += 1
                status_icon = "✅"
                status_style = Colors.SUCCESS
            else:
                status_icon = "⏳"
                status_style = Colors.WARNING
            
            table.add_row(
                step_name,
                f"[{status_style}]{status_icon}[/{status_style}]",
                details
            )
        
        console.print(Align.center(table))
    
    @staticmethod
    def display_menu(title: str, options: List[str], default_choice: str = "1") -> Optional[str]:
        """
        显示菜单并获取用户选择。
        特殊处理包含"退出"、"返回"等关键字的选项，将其序号设置为0。
        """
        if not options:
            UIUtils.print_warning("菜单选项为空")
            return None

        exit_option = None
        exit_option_original_index = -1
        regular_options = list(options)  # 创建一个副本以安全地修改

        # 查找并分离出退出/返回选项（通常是最后一个）
        if regular_options:
            last_option_lower = regular_options[-1].lower()
            exit_keywords = ["exit", "quit", "back", "return", "cancel", "退出", "返回", "取消"]
            if any(keyword in last_option_lower for keyword in exit_keywords):
                exit_option_original_index = len(regular_options) - 1
                exit_option = regular_options.pop(exit_option_original_index)

        # 构建显示的菜单项和有效的选择
        menu_items = []
        valid_choices = []

        # 1. 处理普通选项
        for i, option in enumerate(regular_options, 1):
            menu_items.append(f"   {i}. {option}")
            valid_choices.append(str(i))

        # 2. 处理退出选项
        if exit_option:
            menu_items.append(f"   0. {exit_option}")
            valid_choices.append("0")

        # 渲染菜单面板
        panel_content = "\n".join(menu_items)
        panel = Panel(panel_content, title=f"╭─ {title} ─╮", border_style="dim", expand=False)
        console.print(Align.center(panel))

        # 准备并显示用户输入提示，并与菜单左对齐
        # 首先，我们需要测量Panel的宽度
        panel_width = console.measure(panel).maximum
        
        # 获取终端宽度
        terminal_width = console.width
        
        # 计算左侧需要填充的空格数
        padding = (terminal_width - panel_width) // 2
        
        # 创建带缩进的提示
        prompt_text = " " * padding + f"请选择操作 [{'/'.join(valid_choices)}]"

        # 确保 default_choice 是有效的，否则不使用默认值
        final_default = default_choice if default_choice in valid_choices else None

        try:
            choice = Prompt.ask(
                prompt_text,
                choices=valid_choices,
                default=final_default
            )

            # 将 "0" 映射回原始的选项索引 (1-based)
            if exit_option and choice == "0":
                # 返回原始列表中的位置 (index + 1)
                return str(exit_option_original_index + 1)

            return choice

        except Exception as e:
            # 在交互失败时返回 None，以防程序卡死
            console.print(f"[red]菜单输入时发生错误: {e}[/red]")
            return None

    @staticmethod
    def pause(message: str = "按任意键继续..."):
        """暂停程序，等待用户输入"""
        console.input(f"[dim]{message}[/dim]")

    @staticmethod
    def print_separator(char: str = "─", length: int = 50):
        """打印分隔线"""
        console.print(f"[{Colors.MUTED}]{char * length}[/{Colors.MUTED}]")
    
    @staticmethod
    def print_title(title: str):
        """打印标题"""
        title_text = Text(title, style="bold magenta")
        title_text.stylize("underline")
        console.print(title_text, justify="center")
    
    @staticmethod
    def print_subtitle(subtitle: str):
        """打印副标题"""
        console.print(f"\n{subtitle}", style="bold cyan")
    
    @staticmethod
    def confirm(message: str, default: bool = True) -> bool:
        """确认对话框"""
        return Confirm.ask(message, default=default)
    
    @staticmethod
    def prompt(prompt_text: str, default: Optional[str] = None, choices: Optional[List[str]] = None, multiline: bool = False) -> Optional[str]:
        """获取用户输入，支持单行和多行模式。多行模式会打开系统默认编辑器。"""
        try:
            if multiline:
                # --- Multi-line editing using external editor ---
                if choices:
                    raise ValueError("多行模式不支持'choices'参数")

                # 查找一个可用的文本编辑器
                editor = None
                # 1. 检查环境变量
                env_editor = os.environ.get('VISUAL') or os.environ.get('EDITOR')
                if env_editor and shutil.which(env_editor):
                    editor = env_editor
                
                # 2. 如果环境变量中没有，或者编辑器不存在，则根据操作系统尝试预设列表
                if not editor:
                    if sys.platform == "win32":
                        common_editors = ['notepad']
                    else:
                        common_editors = ['nvim', 'nano', 'vim', 'vi']
                    
                    for e in common_editors:
                        if shutil.which(e):
                            editor = e
                            break
                
                # 3. 如果还是没有找到，就报错
                if not editor:
                    if sys.platform == "win32":
                        error_msg = "错误：未找到默认编辑器 (notepad)。请确保其在系统路径中。"
                    else:
                        error_msg = "错误：未找到任何可用的文本编辑器 (如 nvim, nano, vim, vi)。请安装其中一个，或设置您的 VISUAL/EDITOR 环境变量。"
                    console.print(f"\\n[red]{error_msg}[/red]")
                    return None

                # 创建一个临时文件用于编辑
                fd, path = tempfile.mkstemp(suffix=".txt", text=True)
                
                try:
                    # 将初始内容写入临时文件
                    with os.fdopen(fd, 'w', encoding='utf-8') as tmpfile:
                        if default:
                            tmpfile.write(default)
                    
                    # 打印操作指南
                    console.print(f"[bold cyan]{prompt_text}[/bold cyan]")
                    console.print(f"[dim]正在调用外部编辑器 ({editor})。请在编辑器中修改内容，保存并关闭以继续...[/dim]")
                    
                    # 打开编辑器，并等待其关闭
                    subprocess.run([editor, path], check=True)
                    
                    # 从文件中读回修改后的内容
                    with open(path, 'r', encoding='utf-8') as tmpfile:
                        edited_content = tmpfile.read()
                    
                    return edited_content
                
                finally:
                    # 确保临时文件总是被删除
                    os.remove(path)

            else:
                # --- 原始的单行输入逻辑 ---
                return Prompt.ask(prompt_text, choices=choices, default=default)

        except (KeyboardInterrupt, EOFError):
            console.print("\\n[yellow]操作已取消。[/yellow]")
            return None
        except FileNotFoundError:
            console.print(f"\\n[red]错误：编辑器 '{editor}' 未找到。[/red]")
            console.print("[red]请安装该编辑器，或设置您的 VISUAL/EDITOR 环境变量。[/red]")
            return None
        except Exception as e:
            console.print(f"\\n[red]输入处理时发生错误: {e}[/red]")
            return None
    
    @staticmethod
    def create_progress() -> Progress:
        """创建进度条"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        )
    
    @staticmethod
    def print_welcome():
        """打印欢迎信息"""
        welcome_text = """
# 🎨 MetaNovel Engine

欢迎使用MetaNovel Engine！这是一个强大的AI辅助小说创作工具，
帮助您从一句话主题开始，逐步完成完整的小说创作。
        """
        UIUtils.print_markdown(welcome_text)
    
    @staticmethod
    def print_goodbye():
        """打印再见信息"""
        goodbye_text = """
# 👋 感谢使用 MetaNovel Engine

期待您的下次使用！如果您有任何问题或建议，
请访问项目GitHub页面：https://github.com/hahagood/MetaNovel-Engine

祝您创作愉快！✨
        """
        UIUtils.print_markdown(goodbye_text)
    
    @staticmethod
    def print_error_details(error: Exception, context: str = ""):
        """打印详细错误信息"""
        error_panel = Panel(
            f"[red]错误类型:[/red] {type(error).__name__}\n"
            f"[red]错误信息:[/red] {str(error)}\n"
            f"[red]上下文:[/red] {context}" if context else f"[red]错误信息:[/red] {str(error)}",
            title="❌ 错误详情",
            style="red"
        )
        console.print(error_panel)


# 全局UI工具实例
ui = UIUtils() 