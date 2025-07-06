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
from typing import List, Dict, Any, Optional
import json

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
        
        console.print(table)
        
        # 显示总体完成度进度条
        completion_percentage = int((completed_count / total_count) * 100)
        
        # 创建进度条
        from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
        
        progress_text = f"总体完成度: {completed_count}/{total_count} ({completion_percentage}%)"
        
        if completion_percentage == 100:
            # 全部完成时的祝贺
            UIUtils.print_success("🎉 恭喜！您已完成所有创作步骤！")
        elif completion_percentage > 0:
            # 显示下一步建议
            next_step = None
            for key, step_name in steps.items():
                status_info = status_details.get(key, {"completed": False})
                if not status_info.get("completed", False):
                    next_step = step_name
                    break
            
            if next_step:
                UIUtils.print_info(f"💡 建议下一步: {next_step}")
        else:
            # 刚开始时的提示
            UIUtils.print_info("💡 建议从第一步开始您的创作之旅")
        
        # 显示简洁的进度条
        console.print(f"\n📈 {progress_text}", style=Colors.HIGHLIGHT)
    
    @staticmethod
    def display_menu(title: str, options: List[str], default_choice: str = "1") -> str:
        """
        显示一个标准化的菜单并返回用户的选择。

        Args:
            title (str): 菜单标题。
            options (List[str]): 菜单选项列表。
            default_choice (str): 默认选项。

        Returns:
            str: 用户选择的选项的索引（从1开始）。
        """
        menu_text = "\n".join([f"  [cyan]{i}.[/cyan] {option}" for i, option in enumerate(options, 1)])
        
        panel = Panel(
            menu_text,
            title=f"🎯 {title}",
            title_align="left",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(panel)
        
        choice = Prompt.ask(
            "请选择操作",
            choices=[str(i) for i in range(1, len(options) + 1)],
            default=default_choice
        )
        return choice

    @staticmethod
    def print_menu(title: str, options: List[str]):
        """【即将废弃】打印菜单，请改用 display_menu"""
        UIUtils.print_warning("此 print_menu 方法已过时，请改用 display_menu 以获得更好的交互体验。")
        UIUtils.print_panel(
            "\n".join([f"  {i}. {option}" for i, option in enumerate(options, 1)]),
            title=f"🎯 {title}",
            style="bold blue"
        )
    
    @staticmethod
    def print_separator(char: str = "─", length: int = 50):
        """打印分隔线"""
        console.print(char * length, style=Colors.MUTED)
    
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
    def prompt(message: str, default: str = "") -> str:
        """输入提示"""
        return Prompt.ask(message, default=default)
    
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