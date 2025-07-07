from ui_utils import ui, console
from project_data_manager import project_data_manager
from workflow_ui import handle_creative_workflow
from export_ui import handle_novel_export

def show_workbench():
    """显示项目工作台菜单"""
    while True:
        console.clear()
        active_project_name = project_data_manager.get_current_project_display_name()
        title = f"🛠️ 工作台 (当前项目: 《{active_project_name}》)"

        # 显示项目状态
        dm = project_data_manager.get_data_manager()
        if dm:
            status_details = dm.get_project_status_details()
            ui.print_project_status(status_details)
            
        menu_options = [
            "✍️ 开始 / 继续创作",
            "📊 查看项目概览 (功能待实现)",
            "📤 导出小说",
            "🔙 返回项目管理"
        ]
        
        choice = ui.display_menu(title, menu_options)

        if choice == '1':
            handle_creative_workflow() 
        elif choice == '2':
            ui.print_info("功能开发中：显示项目详细概览...")
            ui.pause()
        elif choice == '3':
            handle_novel_export()
        elif choice == '0':
            break
