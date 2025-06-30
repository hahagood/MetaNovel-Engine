import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class ProjectInfo:
    """项目信息数据类"""
    name: str
    display_name: str
    path: Path
    created_at: str
    last_accessed: str
    description: str = ""

class ProjectManager:
    """多项目管理器"""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        初始化项目管理器
        
        Args:
            base_dir: 项目存储的基础目录，默认为 ~/.metanovel
        """
        if base_dir is None:
            self.base_dir = Path.home() / ".metanovel"
        else:
            self.base_dir = Path(base_dir)
        
        self.projects_dir = self.base_dir / "projects"
        self.config_file = self.base_dir / "config.json"
        
        # 确保目录存在
        self._ensure_directories()
        
        # 初始化配置
        self._init_config()
    
    def _ensure_directories(self):
        """确保必要的目录存在"""
        self.base_dir.mkdir(exist_ok=True)
        self.projects_dir.mkdir(exist_ok=True)
    
    def _init_config(self):
        """初始化全局配置文件"""
        if not self.config_file.exists():
            default_config = {
                "version": "1.0",
                "active_project": None,
                "projects": {},
                "created_at": datetime.now().isoformat()
            }
            self._save_config(default_config)
    
    def _load_config(self) -> Dict[str, Any]:
        """加载全局配置"""
        try:
            with self.config_file.open('r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"加载配置文件时出错: {e}")
            return {}
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """保存全局配置"""
        try:
            with self.config_file.open('w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            return True
        except IOError as e:
            print(f"保存配置文件时出错: {e}")
            return False
    
    def create_project(self, name: str, display_name: str = "", description: str = "") -> bool:
        """
        创建新项目
        
        Args:
            name: 项目名称（用作目录名）
            display_name: 显示名称
            description: 项目描述
            
        Returns:
            bool: 创建成功返回True
        """
        # 验证项目名称
        if not name or not name.strip():
            print("项目名称不能为空")
            return False
        
        # 清理项目名称，去除非法字符
        clean_name = self._clean_project_name(name.strip())
        if not clean_name:
            print("项目名称包含非法字符")
            return False
        
        # 检查项目是否已存在
        if self.project_exists(clean_name):
            print(f"项目 '{clean_name}' 已存在")
            return False
        
        # 创建项目目录
        project_path = self.projects_dir / clean_name
        try:
            project_path.mkdir(exist_ok=False)
            
            # 创建项目的子目录
            (project_path / "meta").mkdir()
            (project_path / "meta_backup").mkdir()
            
            # 创建项目信息文件
            project_info = {
                "name": clean_name,
                "display_name": display_name or clean_name,
                "description": description,
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat()
            }
            
            info_file = project_path / "project_info.json"
            with info_file.open('w', encoding='utf-8') as f:
                json.dump(project_info, f, ensure_ascii=False, indent=4)
            
            # 更新全局配置
            config = self._load_config()
            config["projects"][clean_name] = project_info
            
            # 如果这是第一个项目，设为活动项目
            if not config.get("active_project"):
                config["active_project"] = clean_name
            
            self._save_config(config)
            
            print(f"✅ 项目 '{display_name or clean_name}' 创建成功")
            return True
            
        except OSError as e:
            print(f"创建项目目录时出错: {e}")
            return False
    
    def _clean_project_name(self, name: str) -> str:
        """清理项目名称，移除非法字符"""
        import re
        # 移除非法字符，保留中文、英文、数字、下划线、连字符
        cleaned = re.sub(r'[<>:"/\\|?*]', '', name)
        # 移除首尾空格
        cleaned = cleaned.strip()
        return cleaned
    
    def project_exists(self, name: str) -> bool:
        """检查项目是否存在"""
        project_path = self.projects_dir / name
        return project_path.exists() and project_path.is_dir()
    
    def list_projects(self) -> List[ProjectInfo]:
        """列出所有项目"""
        config = self._load_config()
        projects = []
        
        for name, info in config.get("projects", {}).items():
            if self.project_exists(name):
                projects.append(ProjectInfo(
                    name=info["name"],
                    display_name=info.get("display_name", name),
                    path=self.projects_dir / name,
                    created_at=info.get("created_at", ""),
                    last_accessed=info.get("last_accessed", ""),
                    description=info.get("description", "")
                ))
        
        return sorted(projects, key=lambda x: x.last_accessed, reverse=True)
    
    def get_active_project(self) -> Optional[str]:
        """获取当前活动项目"""
        config = self._load_config()
        return config.get("active_project")
    
    def set_active_project(self, name: str) -> bool:
        """设置活动项目"""
        if not self.project_exists(name):
            print(f"项目 '{name}' 不存在")
            return False
        
        config = self._load_config()
        config["active_project"] = name
        
        # 更新最后访问时间
        if name in config["projects"]:
            config["projects"][name]["last_accessed"] = datetime.now().isoformat()
        
        return self._save_config(config)
    
    def delete_project(self, name: str) -> bool:
        """删除项目"""
        if not self.project_exists(name):
            print(f"项目 '{name}' 不存在")
            return False
        
        import shutil
        try:
            # 删除项目目录
            project_path = self.projects_dir / name
            shutil.rmtree(project_path)
            
            # 更新全局配置
            config = self._load_config()
            if name in config["projects"]:
                del config["projects"][name]
            
            # 如果删除的是活动项目，清除活动项目
            if config.get("active_project") == name:
                # 如果还有其他项目，选择第一个作为活动项目
                remaining_projects = list(config["projects"].keys())
                config["active_project"] = remaining_projects[0] if remaining_projects else None
            
            self._save_config(config)
            
            print(f"✅ 项目 '{name}' 已删除")
            return True
            
        except OSError as e:
            print(f"删除项目时出错: {e}")
            return False
    
    def get_project_path(self, name: str) -> Optional[Path]:
        """获取项目路径"""
        if self.project_exists(name):
            return self.projects_dir / name
        return None
    
    def get_active_project_path(self) -> Optional[Path]:
        """获取活动项目路径"""
        active_project = self.get_active_project()
        if active_project:
            return self.get_project_path(active_project)
        return None
    
    def get_project_info(self, name: str) -> Optional[ProjectInfo]:
        """获取项目信息"""
        config = self._load_config()
        if name in config.get("projects", {}):
            info = config["projects"][name]
            return ProjectInfo(
                name=info["name"],
                display_name=info.get("display_name", name),
                path=self.projects_dir / name,
                created_at=info.get("created_at", ""),
                last_accessed=info.get("last_accessed", ""),
                description=info.get("description", "")
            )
        return None

# 全局项目管理器实例
project_manager = ProjectManager() 