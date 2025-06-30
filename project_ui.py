import questionary
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from datetime import datetime
from project_manager import project_manager
from project_data_manager import project_data_manager
from ui_utils import console

def handle_project_management():
    """处理项目管理主菜单"""
    while True:
        # 获取当前项目信息
        current_project = project_manager.get_active_project()
        current_display_name = project_data_manager.get_current_project_display_name()
        
        # 显示当前状态
        if current_project:
            status_text = f"[green]当前项目: {current_display_name}[/green]"
        else:
            status_text = "[yellow]当前无活动项目[/yellow]"
        
        console.print(Panel(status_text, title="📁 项目管理", border_style="blue"))
        
        # 菜单选项
        choices = [
            "1. 📋 查看所有项目",
            "2. ➕ 创建新项目", 
            "3. 🎯 选择项目开始创作",
            "4. 📝 编辑项目信息",
            "5. ❌ 删除项目",
            "6. 📊 项目详情",
            "7. 🔙 返回主菜单"
        ]
        
        action = questionary.select(
            "请选择要进行的操作：",
            choices=choices,
            use_indicator=True
        ).ask()
        
        if action is None or action.startswith("7."):
            break
        elif action.startswith("1."):
            list_all_projects()
        elif action.startswith("2."):
            create_new_project()
        elif action.startswith("3."):
            switch_project()
        elif action.startswith("4."):
            edit_project()
        elif action.startswith("5."):
            delete_project()
        elif action.startswith("6."):
            show_project_details()

def list_all_projects():
    """列出所有项目"""
    projects = project_manager.list_projects()
    
    if not projects:
        console.print("[yellow]暂无项目。请先创建一个项目。[/yellow]")
        return
    
    # 创建表格
    table = Table(title="📚 所有项目")
    table.add_column("项目名称", style="cyan", no_wrap=True)
    table.add_column("显示名称", style="green")
    table.add_column("描述", style="white")
    table.add_column("创建时间", style="yellow")
    table.add_column("最后访问", style="magenta")
    table.add_column("状态", style="red")
    
    current_project = project_manager.get_active_project()
    
    for project in projects:
        # 格式化时间
        try:
            created_time = datetime.fromisoformat(project.created_at).strftime("%Y-%m-%d %H:%M")
        except:
            created_time = "未知"
        
        try:
            access_time = datetime.fromisoformat(project.last_accessed).strftime("%Y-%m-%d %H:%M")
        except:
            access_time = "未知"
        
        # 状态标识
        status = "🔸 活动" if project.name == current_project else "⚪ 非活动"
        
        table.add_row(
            project.name,
            project.display_name,
            project.description or "无描述",
            created_time,
            access_time,
            status
        )
    
    console.print(table)

def create_new_project():
    """创建新项目"""
    console.print(Panel("📝 创建新项目", border_style="green"))
    
    # 输入项目名称
    project_name = questionary.text(
        "请输入项目名称（用作目录名）:",
        validate=lambda x: len(x.strip()) > 0 if x else False
    ).ask()
    
    if not project_name:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 输入显示名称
    display_name = questionary.text(
        "请输入显示名称（可选，留空则使用项目名称）:",
        default=project_name
    ).ask()
    
    if display_name is None:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 输入项目描述
    description = questionary.text(
        "请输入项目描述（可选）:"
    ).ask()
    
    if description is None:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 创建项目
    if project_manager.create_project(project_name.strip(), display_name.strip(), description.strip()):
        console.print(f"[green]✅ 项目 '{display_name or project_name}' 创建成功！[/green]")
        
        # 询问是否切换到新项目
        if questionary.confirm("是否切换到新创建的项目？", default=True).ask():
            project_data_manager.switch_project(project_name.strip())
            console.print(f"[green]已切换到项目 '{display_name or project_name}'[/green]")
    else:
        console.print("[red]❌ 项目创建失败[/red]")

def switch_project():
    """切换项目并进入创作流程"""
    projects = project_manager.list_projects()
    
    if not projects:
        console.print("[yellow]暂无项目可切换[/yellow]")
        return
    
    current_project = project_manager.get_active_project()
    
    # 准备选择列表
    choices = []
    for project in projects:
        status = " (当前)" if project.name == current_project else ""
        choices.append(f"{project.display_name}{status}")
    
    choices.append("🔙 返回")
    
    selected = questionary.select(
        "请选择要进入的项目：",
        choices=choices,
        use_indicator=True
    ).ask()
    
    if not selected or selected == "🔙 返回":
        return
    
    # 找到对应的项目
    selected_display_name = selected.replace(" (当前)", "")
    for project in projects:
        if project.display_name == selected_display_name:
            if project_data_manager.switch_project(project.name):
                console.print(f"[green]✅ 已切换到项目 '{project.display_name}'[/green]")
                
                # 导入并调用创作流程菜单
                from meta_novel_cli import handle_creative_workflow
                handle_creative_workflow()
            else:
                console.print("[red]❌ 切换项目失败[/red]")
            break

def delete_project():
    """删除项目"""
    projects = project_manager.list_projects()
    
    if not projects:
        console.print("[yellow]暂无项目可删除[/yellow]")
        return
    
    current_project = project_manager.get_active_project()
    
    # 准备选择列表
    choices = []
    for project in projects:
        status = " (当前)" if project.name == current_project else ""
        choices.append(f"{project.display_name}{status}")
    
    choices.append("取消")
    
    selected = questionary.select(
        "请选择要删除的项目：",
        choices=choices,
        use_indicator=True
    ).ask()
    
    if not selected or selected == "取消":
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 找到对应的项目
    selected_display_name = selected.replace(" (当前)", "")
    selected_project = None
    for project in projects:
        if project.display_name == selected_display_name:
            selected_project = project
            break
    
    if not selected_project:
        console.print("[red]未找到选中的项目[/red]")
        return
    
    # 确认删除
    console.print(f"[red]⚠️  警告：即将删除项目 '{selected_project.display_name}'[/red]")
    console.print("[red]此操作将永久删除该项目的所有数据，无法恢复！[/red]")
    
    if questionary.confirm(f"确定要删除项目 '{selected_project.display_name}' 吗？", default=False).ask():
        if project_manager.delete_project(selected_project.name):
            console.print(f"[green]✅ 项目 '{selected_project.display_name}' 已删除[/green]")
        else:
            console.print("[red]❌ 删除项目失败[/red]")
    else:
        console.print("[yellow]操作已取消[/yellow]")

def show_project_details():
    """显示项目详情"""
    current_project = project_manager.get_active_project()
    
    if not current_project:
        console.print("[yellow]当前无活动项目[/yellow]")
        return
    
    project_info = project_manager.get_project_info(current_project)
    if not project_info:
        console.print("[red]无法获取项目信息[/red]")
        return
    
    # 创建详情面板
    details = f"""
[cyan]项目名称:[/cyan] {project_info.name}
[cyan]显示名称:[/cyan] {project_info.display_name}
[cyan]项目描述:[/cyan] {project_info.description or '无描述'}
[cyan]项目路径:[/cyan] {project_info.path}
[cyan]创建时间:[/cyan] {project_info.created_at}
[cyan]最后访问:[/cyan] {project_info.last_accessed}
    """.strip()
    
    console.print(Panel(details, title=f"📊 项目详情 - {project_info.display_name}", border_style="cyan"))
    
    # 获取项目进度信息
    data_manager = project_data_manager.get_data_manager()
    
    # 检查各个阶段的完成情况
    progress_info = []
    
    # 检查主题
    theme_data = data_manager.read_theme_one_line()
    if theme_data:
        progress_info.append("✅ 小说名称与主题")
    else:
        progress_info.append("❌ 小说名称与主题")
    
    # 检查段落主题
    paragraph = data_manager.read_theme_paragraph()
    if paragraph:
        progress_info.append("✅ 段落主题")
    else:
        progress_info.append("❌ 段落主题")
    
    # 检查世界设定
    characters = data_manager.read_characters()
    locations = data_manager.read_locations()
    items = data_manager.read_items()
    if characters or locations or items:
        progress_info.append("✅ 世界设定")
    else:
        progress_info.append("❌ 世界设定")
    
    # 检查故事大纲
    outline = data_manager.read_story_outline()
    if outline:
        progress_info.append("✅ 故事大纲")
    else:
        progress_info.append("❌ 故事大纲")
    
    # 检查分章细纲
    chapters = data_manager.read_chapter_outline()
    if chapters:
        progress_info.append("✅ 分章细纲")
    else:
        progress_info.append("❌ 分章细纲")
    
    # 检查章节概要
    summaries = data_manager.read_chapter_summaries()
    if summaries:
        progress_info.append("✅ 章节概要")
    else:
        progress_info.append("❌ 章节概要")
    
    # 检查小说正文
    novel_chapters = data_manager.read_novel_chapters()
    if novel_chapters:
        progress_info.append("✅ 小说正文")
    else:
        progress_info.append("❌ 小说正文")
    
    # 显示进度信息
    progress_text = "\n".join(progress_info)
    console.print(Panel(progress_text, title="📈 创作进度", border_style="green"))

def edit_project():
    """编辑项目信息"""
    projects = project_manager.list_projects()
    
    if not projects:
        console.print("[yellow]暂无项目可编辑[/yellow]")
        return
    
    # 准备选择列表
    choices = []
    for project in projects:
        choices.append(f"{project.display_name}")
    
    choices.append("取消")
    
    selected = questionary.select(
        "请选择要编辑的项目：",
        choices=choices,
        use_indicator=True
    ).ask()
    
    if not selected or selected == "取消":
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 找到对应的项目
    selected_project = None
    for project in projects:
        if project.display_name == selected:
            selected_project = project
            break
    
    if not selected_project:
        console.print("[red]未找到选中的项目[/red]")
        return
    
    console.print(Panel(f"📝 编辑项目 - {selected_project.display_name}", border_style="yellow"))
    
    # 显示当前信息
    console.print(f"[cyan]当前项目名称:[/cyan] {selected_project.name}")
    console.print(f"[cyan]当前显示名称:[/cyan] {selected_project.display_name}")
    console.print(f"[cyan]当前描述:[/cyan] {selected_project.description or '无描述'}")
    console.print()
    
    # 编辑显示名称
    new_display_name = questionary.text(
        "请输入新的显示名称（留空保持不变）:",
        default=selected_project.display_name
    ).ask()
    
    if new_display_name is None:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 编辑描述
    new_description = questionary.text(
        "请输入新的项目描述（留空保持不变）:",
        default=selected_project.description or ""
    ).ask()
    
    if new_description is None:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 检查是否有更改
    display_name_changed = new_display_name.strip() != selected_project.display_name
    description_changed = new_description.strip() != (selected_project.description or "")
    
    if not display_name_changed and not description_changed:
        console.print("[yellow]没有任何更改[/yellow]")
        return
    
    # 确认更改
    changes = []
    if display_name_changed:
        changes.append(f"显示名称: {selected_project.display_name} → {new_display_name.strip()}")
    if description_changed:
        changes.append(f"描述: {selected_project.description or '无描述'} → {new_description.strip() or '无描述'}")
    
    console.print("[yellow]即将进行以下更改:[/yellow]")
    for change in changes:
        console.print(f"  • {change}")
    
    if questionary.confirm("确认保存这些更改吗？", default=True).ask():
        # 执行更新
        update_display_name = new_display_name.strip() if display_name_changed else None
        update_description = new_description.strip() if description_changed else None
        
        if project_manager.update_project_info(
            selected_project.name, 
            display_name=update_display_name,
            description=update_description
        ):
            console.print(f"[green]✅ 项目信息已更新成功[/green]")
        else:
            console.print("[red]❌ 更新项目信息失败[/red]")
    else:
        console.print("[yellow]操作已取消[/yellow]") 