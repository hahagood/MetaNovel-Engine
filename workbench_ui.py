from ui_utils import ui, console
from project_data_manager import project_data_manager
from workflow_ui import handle_creative_workflow
from export_ui import handle_novel_export
from project_manager import project_manager
from rich.panel import Panel

def show_workbench():
    """显示项目工作台菜单"""
    while True:
        console.clear()
        active_project_name = project_data_manager.get_current_project_display_name()
        title = f"工作台 (当前项目: 《{active_project_name}》)"

        # 显示项目状态
        dm = project_data_manager.get_data_manager()
        if dm:
            status_details = dm.get_project_status_details()
            ui.print_project_status(status_details)
            
        menu_options = [
            "开始 / 继续创作",
            "查看项目概览",
            "导出小说",
            "返回项目管理"
        ]
        
        choice = ui.display_menu(title, menu_options)

        if choice == '1':
            handle_creative_workflow() 
        elif choice == '2':
            show_project_overview()
        elif choice == '3':
            handle_novel_export()
        elif choice == '0':
            break

def show_project_overview():
    """显示当前项目的详细概览"""
    console.clear()
    active_project_name = project_data_manager.get_current_project_display_name()
    ui.print_title(f"项目概览 - 《{active_project_name}》")
    
    # 获取项目元数据
    info = project_manager.get_project_info(project_manager.get_active_project())
    if info:
        details = f"""
[cyan]项目名称:[/cyan] {info.name}
[cyan]显示名称:[/cyan] {info.display_name}
[cyan]项目描述:[/cyan] {info.description or '无描述'}
[cyan]项目路径:[/cyan] {info.path}
[cyan]创建时间:[/cyan] {info.created_at}
[cyan]最后访问:[/cyan] {info.last_accessed}
        """.strip()
        console.print(Panel(details, title="项目元数据", border_style="cyan"))
    else:
        ui.print_warning("无法获取项目元数据。")

    # 获取项目进度
    dm = project_data_manager.get_data_manager()
    if dm:
        status_details = dm.get_project_status_details()
        ui.print_project_status(status_details)
    else:
        ui.print_warning("无法获取项目进度。")
        
    ui.pause()
