import os
import datetime
from ui_utils import ui
from project_data_manager import project_data_manager
from config import get_export_base_dir
from project_manager import project_manager

def get_novel_name():
    """Helper to get the current novel's name."""
    dm = project_data_manager.get_data_manager()
    if not dm: return "未命名小说"
    data = dm.read_theme_one_line()
    return data.get("novel_name", "未命名小说") if isinstance(data, dict) else "未命名小说"

def get_export_dir():
    """Gets the export directory for the current project."""
    try:
        export_base_dir = get_export_base_dir()
        active_project = project_manager.get_active_project()
        export_dir = export_base_dir / active_project if active_project else export_base_dir / "Default"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir
    except Exception as e:
        ui.print_warning(f"⚠️ 获取导出目录时出错，使用默认导出文件夹: {e}")
        export_dir = "exports"
        os.makedirs(export_dir, exist_ok=True)
        return export_dir

def handle_novel_export():
    """Main UI handler for exporting the novel."""
    dm = project_data_manager.get_data_manager()
    if not dm:
        ui.print_warning("无活动项目，无法导出。")
        ui.pause()
        return

    chapters = dm.read_chapter_outline()
    novel_chapters = dm.read_novel_chapters()

    if not novel_chapters:
        ui.print_warning("\n当前没有小说正文可导出。")
        ui.pause()
        return
    
    while True:
        action = ui.display_menu("请选择导出操作：", ["导出完整小说", "导出单个章节", "导出章节范围", "返回"])
        
        if action == '1':
            export_complete_novel(chapters, novel_chapters)
        elif action == '2':
            export_single_chapter(chapters, novel_chapters)
        elif action == '3':
            export_chapter_range(chapters, novel_chapters)
        elif action == '0':
            break

def export_single_chapter(chapters, novel_chapters):
    """Exports a single chapter."""
    chapter_map = {f"chapter_{i+1}": ch.get('title', f'第{i+1}章') for i, ch in enumerate(chapters)}
    available_chapters = [title for key, title in chapter_map.items() if key in novel_chapters]
    
    choice_str = ui.display_menu("请选择要导出的章节：", available_chapters + ["返回"])
    
    # 优先处理返回选项
    if choice_str == '0':
        return

    if choice_str.isdigit() and int(choice_str) <= len(available_chapters):
        choice_index = int(choice_str) - 1
        # Find the correct chapter key
        selected_title = available_chapters[choice_index]
        chapter_key = next(key for key, title in chapter_map.items() if title == selected_title)
        
        export_dir = get_export_dir()
        content = novel_chapters.get(chapter_key, {}).get('content', '')
        title = novel_chapters.get(chapter_key, {}).get('title', selected_title)
        
        novel_name = get_novel_name()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{novel_name}_{title}_{timestamp}.txt"
        
        try:
            with open(os.path.join(export_dir, filename), 'w', encoding='utf-8') as f:
                f.write(content)
            ui.print_success(f"章节 '{title}' 已导出到: {os.path.join(export_dir, filename)}\n")
        except Exception as e:
            ui.print_error(f"导出失败: {e}")
        ui.pause()


def export_chapter_range(chapters, novel_chapters):
    """Exports a range of chapters."""
    # This implementation can be complex, for now, we'll keep it simple
    ui.print_info("导出章节范围功能正在施工中...")
    ui.pause()

def export_complete_novel(chapters, novel_chapters):
    """Exports the complete novel to a single file."""
    export_dir = get_export_dir()
    novel_name = get_novel_name()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{novel_name}_完整小说_{timestamp}.txt"
    filepath = os.path.join(export_dir, filename)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# {novel_name}\n\n")
            # Sort chapters by number
            sorted_keys = sorted(novel_chapters.keys(), key=lambda k: int(k.split('_')[1]))
            for key in sorted_keys:
                chapter_data = novel_chapters[key]
                f.write(f"## {chapter_data.get('title', '无标题')}\n\n")
                f.write(chapter_data.get('content', ''))
                f.write("\n\n---\n\n")
        ui.print_success(f"完整小说已导出到: {filepath}\n")
    except Exception as e:
        ui.print_error(f"导出失败: {e}")
    ui.pause()
