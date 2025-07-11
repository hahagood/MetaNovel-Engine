#!/usr/bin/env python3
"""
同步prompts.json到所有用户项目
将更新后的prompts.json分发到~/.metanovel/projects/下的所有项目
"""

import shutil
from pathlib import Path
from ui_utils import ui, console
from rich.panel import Panel
from config import get_app_data_dir

def get_projects_dir():
    """获取项目目录"""
    return get_app_data_dir() / "projects"

def get_all_projects():
    """获取所有项目目录"""
    projects_dir = get_projects_dir()
    if not projects_dir.exists():
        return []
    
    # 返回所有子目录
    return [p for p in projects_dir.iterdir() if p.is_dir()]

def sync_prompts_to_projects():
    """同步prompts.json到所有项目"""
    source_prompts = Path('prompts.json')
    
    if not source_prompts.exists():
        ui.print_error("未找到源prompts.json文件")
        return False
    
    projects = get_all_projects()
    if not projects:
        ui.print_warning("未找到任何项目")
        return False
    
    ui.print_info(f"找到 {len(projects)} 个项目")
    
    success_count = 0
    error_count = 0
    
    for project_path in projects:
        project_name = project_path.name
        target_prompts = project_path / 'prompts.json'
        
        try:
            # 备份现有的prompts.json（如果存在）
            if target_prompts.exists():
                backup_path = project_path / 'prompts.json.backup'
                shutil.copy2(target_prompts, backup_path)
                ui.print_info(f"已备份 {project_name} 的prompts.json")
            
            # 复制新的prompts.json
            shutil.copy2(source_prompts, target_prompts)
            ui.print_success(f"✅ 已同步到项目: {project_name}")
            success_count += 1
            
        except Exception as e:
            ui.print_error(f"❌ 同步到项目 {project_name} 失败: {e}")
            error_count += 1
    
    # 显示结果统计
    console.print(Panel(
        f"同步完成!\n成功: {success_count} 个项目\n失败: {error_count} 个项目",
        title="同步结果",
        border_style="green" if error_count == 0 else "yellow"
    ))
    
    return error_count == 0

def main():
    """主函数"""
    ui.print_info("开始同步prompts.json到所有项目...")
    
    if sync_prompts_to_projects():
        ui.print_success("所有项目同步完成！")
    else:
        ui.print_warning("部分项目同步失败，请检查错误信息")

if __name__ == "__main__":
    main()