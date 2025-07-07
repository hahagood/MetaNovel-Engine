from rich import print as rprint
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from datetime import datetime
from project_manager import project_manager
from project_data_manager import project_data_manager
from ui_utils import ui, console
from workbench_ui import show_workbench

def handle_project_management():
    """处理项目管理的UI和逻辑"""
    while True:
        console.clear()
        
        current_project = project_manager.get_active_project()
        current_display_name = "无"
        if current_project:
            info = project_manager.get_project_info(current_project)
            current_display_name = info.display_name if info else "未知"
        
        title = f"📁 项目管理 (当前: {current_display_name})"
        
        menu_options = [
            "✅ 选择并进入项目",
            "➕ 创建新项目",
            "🗂️  管理项目列表",
            "🔙  返回主菜单"
        ]
        
        choice = ui.display_menu(title, menu_options)

        if choice == '1':
            select_and_enter_project()
        elif choice == '2':
            create_new_project()
        elif choice == '3':
            manage_project_list()
        elif choice == '0':
            break

def select_and_enter_project():
    """选择一个项目并进入其工作台"""
    projects = project_manager.list_projects()
    if not projects:
        ui.print_warning("暂无项目。请先创建一个新项目。")
        ui.pause()
        return

    current_project = project_manager.get_active_project()
    
    choices = []
    for p in projects:
        status = " (当前)" if p.name == current_project else ""
        choices.append(f"{p.display_name}{status}")
    choices.append("返回")

    choice_str = ui.display_menu("请选择要进入的项目:", choices)
    
    if choice_str.isdigit() and choice_str != '0':
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(projects):
            selected_project = projects[choice_index]
            project_data_manager.switch_project(selected_project.name)
            ui.print_success(f"已进入项目: 《{selected_project.display_name}》")
            show_workbench() # 进入项目工作台
    
def manage_project_list():
    """提供编辑、删除、查看详情等项目管理功能"""
    while True:
        list_all_projects() # 先展示列表
        
        menu_options = [
            "📝 编辑项目信息",
            "❌ 删除项目",
            "📊 查看项目详情",
            "🔙 返回"
        ]
        choice = ui.display_menu("🗂️ 管理项目列表", menu_options)

        if choice == '1':
            edit_project()
        elif choice == '2':
            delete_project()
        elif choice == '3':
            show_project_details()
        elif choice == '0':
            break

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
    # This function is now obsolete and replaced by select_and_enter_project
    pass

def delete_project():
    """删除项目"""
    selected_project = None
    
    # Let user select which project to delete
    projects = project_manager.list_projects()
    if not projects:
        ui.print_warning("没有可删除的项目。")
        return

    choices = [p.display_name for p in projects]
    choices.append("取消")
    
    choice_str = ui.display_menu("请选择要删除的项目:", choices)

    if choice_str.isdigit() and choice_str != '0':
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(projects):
            selected_project = projects[choice_index]
        else:
            ui.print_warning("无效的选择。")
            return
    else: # User cancelled
        return
        
    if not selected_project:
        ui.print_error("未找到选中的项目。")
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
    ui.pause()

def show_project_details():
    """显示项目详情"""
    current_project = project_manager.get_active_project()
    
    if not current_project:
        ui.print_warning("请先选择一个活动项目。")
        ui.pause()
        return
    
    info = project_manager.get_project_info(current_project)
    dm = project_data_manager.get_data_manager(current_project)

    if not info or not dm:
        ui.print_error("无法获取项目详情。")
        ui.pause()
        return
    
    # 获取项目对应的显示名称
    project_display_name = info.display_name or info.name

    # 创建详情面板
    details = f"""
[cyan]项目名称:[/cyan] {info.name}
[cyan]显示名称:[/cyan] {project_display_name}
[cyan]项目描述:[/cyan] {info.description or '无描述'}
[cyan]项目路径:[/cyan] {info.path}
[cyan]创建时间:[/cyan] {info.created_at}
[cyan]最后访问:[/cyan] {info.last_accessed}
    """.strip()
    
    console.print(Panel(details, title=f"📊 项目详情 - {project_display_name}", border_style="cyan"))

def edit_project():
    """编辑项目信息"""
    selected_project = None
    
    # Let user select which project to edit
    projects = project_manager.list_projects()
    if not projects:
        ui.print_warning("没有可编辑的项目。")
        return

    choices = [p.display_name for p in projects]
    choices.append("取消")
    
    choice_str = ui.display_menu("请选择要编辑的项目:", choices)
    
    if choice_str.isdigit() and choice_str != '0':
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(projects):
            selected_project = projects[choice_index]
        else:
            ui.print_warning("无效的选择。")
            return
    else: # User cancelled
        return

    if not selected_project:
        ui.print_error("未找到选中的项目。")
        return
        
    console.print(Panel(f"📝 正在编辑项目: {selected_project.display_name}", border_style="yellow"))
    
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