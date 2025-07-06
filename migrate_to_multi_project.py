#!/usr/bin/env python3
"""
数据迁移脚本：从单项目模式迁移到多项目模式
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime
from project_manager import project_manager
from ui_utils import ui

def check_legacy_data():
    """检查是否存在旧版本的数据"""
    legacy_meta_dir = Path("meta")
    legacy_backup_dir = Path("meta_backup")
    
    has_legacy_data = False
    legacy_files = []
    
    if legacy_meta_dir.exists() and legacy_meta_dir.is_dir():
        for file_path in legacy_meta_dir.glob("*.json"):
            if file_path.is_file() and file_path.stat().st_size > 0:
                has_legacy_data = True
                legacy_files.append(file_path)
    
    return has_legacy_data, legacy_files, legacy_meta_dir, legacy_backup_dir

def get_legacy_project_name():
    """从旧数据中获取项目名称"""
    theme_file = Path("meta/theme_one_line.json")
    
    if theme_file.exists():
        try:
            with theme_file.open('r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                # 尝试获取小说名称
                novel_name = data.get("novel_name")
                if novel_name and novel_name != "未命名小说":
                    return novel_name
                
                # 尝试从主题中提取
                theme = data.get("theme", "")
                if theme and "《" in theme and "》" in theme:
                    start = theme.find("《") + 1
                    end = theme.find("》")
                    if start > 0 and end > start:
                        return theme[start:end]
            
            elif isinstance(data, str) and data.strip():
                # 尝试从字符串主题中提取
                if "《" in data and "》" in data:
                    start = data.find("《") + 1
                    end = data.find("》")
                    if start > 0 and end > start:
                        return data[start:end]
        except:
            pass
    
    return "我的小说"

def migrate_legacy_data():
    """迁移旧版本数据到多项目模式"""
    ui.print_info("🔄 检查是否存在旧版本数据...")
    
    has_legacy, legacy_files, legacy_meta_dir, legacy_backup_dir = check_legacy_data()
    
    if not has_legacy:
        ui.print_success("✅ 未发现旧版本数据，无需迁移")
        return True
    
    ui.print_info(f"📁 发现旧版本数据文件 {len(legacy_files)} 个:")
    for file_path in legacy_files:
        ui.print_info(f"   - {file_path}")
    
    # 获取项目名称
    project_name = get_legacy_project_name()
    ui.print_info(f"📝 检测到的项目名称: {project_name}")
    
    # 询问用户是否进行迁移
    if not ui.confirm(
        f"是否将现有数据迁移到新项目 '{project_name}' 中？",
        default=True
    ):
        ui.print_warning("⏹️ 用户取消迁移")
        return False
    
    # 允许用户修改项目名称
    final_name = ui.prompt(
        "请确认项目名称（或修改）:",
        default=project_name
    )
    
    if not final_name or not final_name.strip():
        ui.print_error("❌ 项目名称不能为空")
        return False
    
    final_name = final_name.strip()
    
    # 创建新项目
    ui.print_info(f"🏗️ 创建新项目: {final_name}")
    if not project_manager.create_project(final_name, final_name, "从旧版本迁移的项目"):
        ui.print_error("❌ 创建项目失败")
        return False
    
    # 获取项目路径
    project_path = project_manager.get_project_path(final_name)
    if not project_path:
        ui.print_error("❌ 获取项目路径失败")
        return False
    
    target_meta_dir = project_path / "meta"
    target_backup_dir = project_path / "meta_backup"
    
    try:
        # 迁移数据文件
        ui.print_info("📂 迁移数据文件...")
        if legacy_meta_dir.exists():
            for item in legacy_meta_dir.iterdir():
                if item.is_file():
                    target_file = target_meta_dir / item.name
                    shutil.copy2(item, target_file)
                    ui.print_success(f"   ✅ 已迁移: {item.name}")
        
        # 迁移备份文件
        if legacy_backup_dir.exists() and legacy_backup_dir.is_dir():
            ui.print_info("📂 迁移备份文件...")
            for item in legacy_backup_dir.iterdir():
                if item.is_file():
                    target_file = target_backup_dir / item.name
                    shutil.copy2(item, target_file)
                    ui.print_success(f"   ✅ 已迁移备份: {item.name}")
        
        # 设置为活动项目
        project_manager.set_active_project(final_name)
        
        ui.print_success(f"✅ 数据迁移完成！项目 '{final_name}' 已设为活动项目")
        
        # 询问是否删除旧数据
        if ui.confirm(
            "是否删除原始的旧版本数据目录？（建议保留作为备份）",
            default=False
        ):
            ui.print_info("🗑️ 删除旧版本数据...")
            if legacy_meta_dir.exists():
                shutil.rmtree(legacy_meta_dir)
                ui.print_success("   ✅ 已删除旧版本 meta 目录")
            
            if legacy_backup_dir.exists():
                shutil.rmtree(legacy_backup_dir)
                ui.print_success("   ✅ 已删除旧版本 meta_backup 目录")
        else:
            ui.print_info("📁 旧版本数据已保留，您可以稍后手动删除")
        
        return True
        
    except Exception as e:
        ui.print_error(f"❌ 迁移过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    ui.print_info("🚀 MetaNovel-Engine 数据迁移工具")
    ui.print_info("=" * 50)
    
    try:
        if migrate_legacy_data():
            ui.print_success("\n🎉 迁移成功完成！")
            ui.print_info("现在您可以使用 python meta_novel_cli.py 启动程序")
            ui.print_info("程序将自动运行在多项目模式下")
        else:
            ui.print_warning("\n⚠️ 迁移未完成")
    
    except KeyboardInterrupt:
        ui.print_warning("\n\n⏹️ 用户中断操作")
    except Exception as e:
        ui.print_error(f"\n💥 迁移过程中出现异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 