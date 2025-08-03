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
        chapter_data = novel_chapters.get(chapter_key, {})
        content = chapter_data.get('content', '')
        title = chapter_data.get('title', selected_title)
        
        novel_name = get_novel_name()
        timestamp = datetime.datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        display_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # 使用已有的字数数据，如果没有则重新计算
        word_count = chapter_data.get('word_count', 0)
        if word_count == 0:
            word_count = len(content.replace(' ', '').replace('\n', '').replace('\t', ''))
        
        filename = f"{novel_name}_{title}_{timestamp_str}.txt"
        
        try:
            with open(os.path.join(export_dir, filename), 'w', encoding='utf-8') as f:
                # 写入元数据头部
                f.write(f"《{novel_name}》\n")
                f.write("=" * 30 + "\n")
                f.write(f"导出时间: {display_timestamp}\n")
                # 获取章节号码
                chapter_num = int(chapter_key.split('_')[1])
                f.write(f"导出章节: 第{chapter_num}章 {title}\n")
                f.write(f"字数: {word_count} 字\n")
                f.write("=" * 30 + "\n\n")
                
                # 写入章节标题
                f.write(f"第{chapter_num}章 {title}\n")
                f.write("=" * 30 + "\n\n")
                
                # 写入正文内容
                f.write(content)
                
                # 添加AI生成作品说明
                f.write("\n\n" + "=" * 30 + "\n")
                f.write("这是 AI 生成的作品\n")
                f.write("如有问题或建议\n")
                f.write("请访问GitHub页面：\n")
                f.write("https://github.com/hahagood/MetaNovel-Engine\n")
                
            ui.print_success(f"章节 '{title}' 已导出到: {os.path.join(export_dir, filename)}\n")
        except Exception as e:
            ui.print_error(f"导出失败: {e}")
        ui.pause()


def export_chapter_range(chapters, novel_chapters):
    """Exports a range of chapters."""
    chapter_map = {f"chapter_{i+1}": ch.get('title', f'第{i+1}章') for i, ch in enumerate(chapters)}
    available_chapters = [(key, title) for key, title in chapter_map.items() if key in novel_chapters]
    
    if len(available_chapters) < 2:
        ui.print_warning("需要至少2个章节才能使用范围导出功能。")
        ui.pause()
        return
    
    ui.print_info("可用章节:")
    for i, (key, title) in enumerate(available_chapters, 1):
        ui.print_info(f"{i}. {title}")
    
    try:
        # 改进用户交互：支持范围格式如 "1-3" 或分别输入
        range_input = ui.get_user_input(f"请输入章节范围 (如: 1-{len(available_chapters)} 或 1,3 表示第1到第{len(available_chapters)}章): ")
        
        # 解析范围输入
        start_idx = None
        end_idx = None
        
        # 支持 "1-3" 格式
        if '-' in range_input:
            try:
                parts = range_input.split('-')
                if len(parts) == 2:
                    start_idx = int(parts[0].strip()) - 1
                    end_idx = int(parts[1].strip()) - 1
            except ValueError:
                pass
        
        # 支持 "1,3" 或 "1 3" 格式
        elif ',' in range_input or ' ' in range_input:
            try:
                separator = ',' if ',' in range_input else ' '
                parts = [p.strip() for p in range_input.split(separator) if p.strip()]
                if len(parts) == 2:
                    start_idx = int(parts[0]) - 1
                    end_idx = int(parts[1]) - 1
            except ValueError:
                pass
        
        # 支持单个数字（视为单章节）
        elif range_input.isdigit():
            idx = int(range_input) - 1
            start_idx = end_idx = idx
        
        # 验证输入
        if (start_idx is None or end_idx is None or 
            start_idx < 0 or end_idx >= len(available_chapters) or start_idx > end_idx):
            ui.print_warning("无效的章节范围。请使用格式如 '1-3' 或 '1,3' 来指定范围。")
            ui.pause()
            return
        
        # 选择范围内的章节
        selected_chapters = available_chapters[start_idx:end_idx + 1]
        
        export_dir = get_export_dir()
        novel_name = get_novel_name()
        timestamp = datetime.datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        display_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # 使用已有的字数数据计算总字数和生成章节列表
        total_word_count = 0
        chapter_titles = []
        for key, title in selected_chapters:
            chapter_data = novel_chapters[key]
            # 使用已有的字数数据，如果没有则重新计算
            word_count = chapter_data.get('word_count', 0)
            if word_count == 0:
                content = chapter_data.get('content', '')
                word_count = len(content.replace(' ', '').replace('\n', '').replace('\t', ''))
            total_word_count += word_count
            chapter_titles.append(title)
        
        chapters_str = "、".join(chapter_titles)
        
        # 生成更清晰的文件名
        if start_idx == end_idx:
            filename = f"{novel_name}_{chapter_titles[0]}_{timestamp_str}.txt"
        else:
            filename = f"{novel_name}_第{start_idx+1}-{end_idx+1}章_{timestamp_str}.txt"
        
        filepath = os.path.join(export_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            # 写入元数据头部
            f.write(f"《{novel_name}》\n")
            f.write("=" * 30 + "\n")
            f.write(f"导出时间: {display_timestamp}\n")
            # 根据章节范围显示不同的导出信息
            if start_idx == end_idx:
                chapter_num = int(selected_chapters[0][0].split('_')[1])
                f.write(f"导出章节: 第{chapter_num}章 {selected_chapters[0][1]}\n")
            else:
                start_num = int(selected_chapters[0][0].split('_')[1])
                end_num = int(selected_chapters[-1][0].split('_')[1])
                f.write(f"导出章节: 第{start_num}章到第{end_num}章\n")
            f.write(f"字数: {total_word_count} 字\n")
            f.write("=" * 30 + "\n\n")
            
            # 直接写入章节内容，不重复作品名
            for key, title in selected_chapters:
                chapter_data = novel_chapters[key]
                chapter_num = int(key.split('_')[1])
                f.write(f"第{chapter_num}章 {title}\n")
                f.write("=" * 30 + "\n\n")
                f.write(chapter_data.get('content', ''))
                f.write("\n\n---\n\n")
            
            # 添加AI生成作品说明
            f.write("\n" + "=" * 30 + "\n")
            f.write("这是 AI 生成的作品\n")
            f.write("如有问题或建议\n")
            f.write("请访问GitHub页面：\n")
            f.write("https://github.com/hahagood/MetaNovel-Engine\n")
        
        if start_idx == end_idx:
            ui.print_success(f"章节 '{chapter_titles[0]}' 已导出到: {filepath}\n")
        else:
            ui.print_success(f"章节 {start_idx+1}-{end_idx+1} 已导出到: {filepath}\n")
        
    except Exception as e:
        ui.print_error(f"导出失败: {e}")
    ui.pause()

def export_complete_novel(chapters, novel_chapters):
    """Exports the complete novel to a single file."""
    export_dir = get_export_dir()
    novel_name = get_novel_name()
    timestamp = datetime.datetime.now()
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    display_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    filename = f"{novel_name}_全本_{timestamp_str}.txt"
    filepath = os.path.join(export_dir, filename)
    
    # 使用已有的字数数据计算总字数
    total_word_count = 0
    sorted_keys = sorted(novel_chapters.keys(), key=lambda k: int(k.split('_')[1]))
    chapter_titles = []
    for key in sorted_keys:
        chapter_data = novel_chapters[key]
        # 使用已有的字数数据，如果没有则重新计算
        word_count = chapter_data.get('word_count', 0)
        if word_count == 0:
            content = chapter_data.get('content', '')
            word_count = len(content.replace(' ', '').replace('\n', '').replace('\t', ''))
        total_word_count += word_count
        chapter_titles.append(chapter_data.get('title', '无标题'))
    
    # 生成章节列表字符串（包含章节号）
    chapters_with_numbers = []
    for key in sorted_keys:
        chapter_data = novel_chapters[key]
        chapter_num = int(key.split('_')[1])
        chapter_title = chapter_data.get('title', '无标题')
        chapters_with_numbers.append(f"第{chapter_num}章 {chapter_title}")
    
    chapters_str = "、".join(chapters_with_numbers)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            # 写入元数据头部
            f.write(f"《{novel_name}》\n")
            f.write("=" * 30 + "\n")
            f.write(f"导出时间: {display_timestamp}\n")
            f.write(f"导出章节: 全文导出\n")
            f.write(f"字数: {total_word_count} 字\n")
            f.write("=" * 30 + "\n\n")
            
            # 直接写入章节内容，不重复作品名
            for key in sorted_keys:
                chapter_data = novel_chapters[key]
                chapter_num = int(key.split('_')[1])
                chapter_title = chapter_data.get('title', '无标题')
                f.write(f"第{chapter_num}章 {chapter_title}\n")
                f.write("=" * 30 + "\n\n")
                f.write(chapter_data.get('content', ''))
                f.write("\n\n---\n\n")
            
            # 添加AI生成作品说明
            f.write("\n" + "=" * 30 + "\n")
            f.write("这是 AI 生成的作品\n")
            f.write("如有问题或建议\n")
            f.write("请访问GitHub页面：\n")
            f.write("https://github.com/hahagood/MetaNovel-Engine\n")
        ui.print_success(f"完整小说已导出到: {filepath}\n")
    except Exception as e:
        ui.print_error(f"导出失败: {e}")
    ui.pause()
