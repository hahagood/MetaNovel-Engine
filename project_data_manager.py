from pathlib import Path
from typing import Optional
from data_manager import DataManager
from project_manager import project_manager

class ProjectDataManager:
    """项目感知的数据管理器工厂"""
    
    def __init__(self):
        self._current_data_manager: Optional[DataManager] = None
        self._current_project: Optional[str] = None
        self.refresh_data_manager()
    
    def refresh_data_manager(self):
        """刷新数据管理器实例"""
        active_project = project_manager.get_active_project()
        
        # 如果活动项目发生变化或者数据管理器尚未创建，重新创建数据管理器
        if active_project != self._current_project or self._current_data_manager is None:
            self._current_project = active_project
            
            if active_project:
                # 多项目模式：使用项目路径
                project_path = project_manager.get_project_path(active_project)
                self._current_data_manager = DataManager(project_path)
            else:
                # 单项目模式：使用默认路径
                self._current_data_manager = DataManager()
    
    def get_data_manager(self) -> DataManager:
        """获取当前的数据管理器实例"""
        self.refresh_data_manager()
        return self._current_data_manager
    
    def switch_project(self, project_name: str) -> bool:
        """切换项目"""
        if project_manager.set_active_project(project_name):
            self.refresh_data_manager()
            return True
        return False
    
    def get_current_project_name(self) -> Optional[str]:
        """获取当前项目名称"""
        return self._current_project
    
    def get_current_project_display_name(self) -> str:
        """获取当前项目的显示名称"""
        if self._current_project:
            project_info = project_manager.get_project_info(self._current_project)
            if project_info:
                return project_info.display_name
        return "未命名小说"

# 全局项目数据管理器实例
project_data_manager = ProjectDataManager() 