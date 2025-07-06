from rich import print as rprint
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from datetime import datetime
from project_manager import project_manager
from project_data_manager import project_data_manager
from ui_utils import ui, console

def handle_project_management():
    """处理项目管理的UI和逻辑"""
    while True:
        console.clear()
        
        current_project = project_manager.get_active_project()
        current_display_name = "无"
        if current_project:
            info = project_manager.get_project_info(current_project)
            current_display_name = info.display_name if info else "未知"
        
        # 将标题作为参数传给display_menu，并移除单独的Panel打印
        title = f"📁 项目管理 (当前: {current_display_name})"
        
        menu_options = [
            "🚀  继续当前项目创作",
            "🔁  切换其他项目",
            "📋  查看所有项目",
            "➕  创建新项目",
            "✏️ 编辑项目信息",
            "🗑️ 删除项目",
            "📊  项目详情",
            "🔙  返回主菜单"
        ]
        
        choice = ui.display_menu(title, menu_options, default_choice="1" if current_project else "3")

        if choice is None:
            break

        def _handle_creative_workflow_wrapper():
            from meta_novel_cli import handle_creative_workflow
            handle_creative_workflow()

        action_map = {
            "1": _handle_creative_workflow_wrapper,
            "2": switch_project,
            "3": list_all_projects,
            "4": create_new_project,
            "5": edit_project,
            "6": delete_project,
            "7": show_project_details,
            "8": lambda: "break"  # 用于跳出循环的哨兵
        }

        # 如果没有当前项目，一些选项是无效的
        if not current_project and choice in ["1", "2", "7"]:
            ui.print_warning("此操作需要先选择一个活动项目。")
            ui.pause()
            continue

        action = action_map.get(choice)
        if action:
            if action() == "break":
                break
        else:
            ui.print_warning("无效的选择。")
            ui.pause()

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
    project_name = ui.prompt("请输入项目名称（用作目录名）")
    
    if not project_name:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 输入显示名称
    display_name = ui.prompt("请输入显示名称（可选，留空则使用项目名称）", default=project_name)
    
    if display_name is None:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 输入项目描述
    description = ui.prompt("请输入项目描述（可选）")
    
    if description is None:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 创建项目
    if project_manager.create_project(project_name.strip(), display_name.strip(), description.strip()):
        console.print(f"[green]✅ 项目 '{display_name or project_name}' 创建成功！[/green]")
        
        # 询问是否切换到新项目
        if ui.confirm("是否切换到新创建的项目？", default=True):
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
    
    choices.append("返回")
    
    choice_index_str = ui.display_menu("请选择要进入的项目：", choices)
    
    # 检查用户是否选择了返回
    if choice_index_str is None or int(choice_index_str) > len(choices) - 1:
        return

    choice_index = int(choice_index_str) - 1

    if choice_index < 0:
        return

    selected_display_name = choices[choice_index].replace(" (当前)", "")
    for project in projects:
        if project.display_name == selected_display_name:
            if project_data_manager.switch_project(project.name):
                console.print(f"[green]✅ 已切换到项目 '{project.display_name}'[/green]")
                
                # 导入并调用创作流程菜单
                from meta_novel_cli import handle_creative_workflow
                handle_creative_workflow()
                # After returning from the creative workflow, we should return to the main menu.
                return
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
    
    choice_index_str = ui.display_menu("请选择要删除的项目：", choices)
    
    if choice_index_str is None:
        console.print("[yellow]操作已取消[/yellow]")
        return
        
    choice_index = int(choice_index_str) - 1
    
    if choice_index < 0 or choice_index >= len(choices) - 1:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 找到对应的项目
    selected_display_name = choices[choice_index].replace(" (当前)", "")
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
    
    if ui.confirm(f"确定要删除项目 '{selected_project.display_name}' 吗？", default=False):
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
    
    # 获取项目对应的显示名称
    project_display_name = project_info.display_name or project_info.name

    # 创建详情面板
    details = f"""
[cyan]项目名称:[/cyan] {project_info.name}
[cyan]显示名称:[/cyan] {project_display_name}
[cyan]项目描述:[/cyan] {project_info.description or '无描述'}
[cyan]项目路径:[/cyan] {project_info.path}
[cyan]创建时间:[/cyan] {project_info.created_at}
[cyan]最后访问:[/cyan] {project_info.last_accessed}
    """.strip()
    
    console.print(Panel(details, title=f"📊 项目详情 - {project_display_name}", border_style="cyan"))

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
    
    choice_index_str = ui.display_menu("请选择要编辑的项目：", choices)
    
    if choice_index_str is None:
        console.print("[yellow]操作已取消[/yellow]")
        return
        
    choice_index = int(choice_index_str) - 1
    
    if choice_index < 0 or choice_index >= len(choices) - 1:
        console.print("[yellow]操作已取消[/yellow]")
        return
    
    # 找到对应的项目
    selected_display_name = choices[choice_index]
    selected_project = None
    for project in projects:
        if project.display_name == selected_display_name:
            selected_project = project
            break
    
    if not selected_project:
        console.print("[red]未找到选中的项目[/red]")
        return
    
    console.print(Panel(f"✏️ 正在编辑项目: {selected_project.display_name}", border_style="yellow"))
    
    # 编辑显示名称
    new_display_name = ui.prompt(
        "请输入新的显示名称",
        default=selected_project.display_name
    )
    
    if new_display_name is None:
        console.print("[yellow]操作已取消[/yellow]")
        return
        
    new_description = ui.prompt("输入新的描述 (留空不修改)", default=selected_project.description or "")
    if new_description is None:
        console.print("[yellow]操作已取消[/yellow]")
        return

    # 检查是否有更改
    display_name_changed = new_display_name.strip() != selected_project.display_name
    description_changed = new_description.strip() != (selected_project.description or "")
    
    if not display_name_changed and not description_changed:
        console.print("[yellow]没有任何更改[/yellow]")
        return

    update_display_name = new_display_name.strip() if display_name_changed else None
    update_description = new_description.strip() if description_changed else None

    # 更新项目
    if project_manager.update_project_info(
        selected_project.name, 
        display_name=update_display_name,
        description=update_description
    ):
        ui.print_success(f"✅ 项目 '{update_display_name or selected_project.name}' 信息已更新")
        # 刷新数据管理器以确保显示名称立即更新
        project_data_manager.refresh_data_manager()
    else:
        ui.print_error("❌ 更新项目信息失败")
    
    ui.pause() 