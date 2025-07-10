import sys
from ui_utils import ui, console
from project_ui import handle_project_management
from project_data_manager import project_data_manager
from rich.panel import Panel
from rich.text import Text
from signal_handler import setup_graceful_exit, cleanup_graceful_exit

def main():
    """主函数，程序的入口点。"""
    # 设置优雅退出处理
    setup_graceful_exit()
    
    try:
        while True:
            console.clear()
            
            # 快速显示基本界面
            active_project_name = project_data_manager.get_current_project_display_name()
            status_text = Text(f"当前项目: 《{active_project_name}》", justify="center")
            console.print(Panel(status_text, title="🚀 MetaNovel Engine", border_style="magenta"))
            
            # 显示项目进度（使用缓存优化）
            dm = project_data_manager.get_data_manager()
            if dm:
                status_details = dm.get_project_status_details()
                ui.print_project_status(status_details)
            
            # 主菜单
            menu_options = [
                "项目管理",
                "系统设置", # This will be wired up later
                "退出"
            ]
            
            # 显示菜单
            choice = ui.display_menu("🚀 MetaNovel Engine - 主菜单", menu_options)

            if choice == '1':
                handle_project_management()
            elif choice == '2':
                # This will be replaced by a call to settings_ui.py
                from settings_ui import handle_system_settings
                handle_system_settings()
            elif choice == '0':
                console.clear()
                ui.print_goodbye()
                break
    
    except KeyboardInterrupt:
        # 在这里不需要做任何事，因为信号处理器已经处理了
        pass
    finally:
        # 清理信号处理器
        cleanup_graceful_exit()


if __name__ == "__main__":
    main()