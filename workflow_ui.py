import asyncio
import re
import json
from llm_service import llm_service
from project_data_manager import project_data_manager
from progress_utils import AsyncProgressManager, run_with_progress
from retry_utils import batch_retry_manager
from entity_manager import handle_characters, handle_locations, handle_items
from ui_utils import ui, console
from rich.panel import Panel
from rich.text import Text

def _sanitize_chapters(chapters):
    """Ensures every chapter has an 'order' key, adding one if missing."""
    for i, ch in enumerate(chapters):
        # 如果有chapter_number字段，使用它作为order
        if 'chapter_number' in ch and ch.get('chapter_number'):
            ch['order'] = ch['chapter_number']
        # 如果没有order字段或order为空，使用索引+1
        elif 'order' not in ch or not ch.get('order'):
            ch['order'] = i + 1
    return chapters

# This file now contains the main creative workflow, moved from meta_novel_cli.py

# --- Getters ---
def get_data_manager():
    return project_data_manager.get_data_manager()

def get_novel_name():
    data = get_data_manager().read_theme_one_line()
    return data.get("novel_name", "未命名小说") if isinstance(data, dict) else "未命名小说"

# --- Main Workflow ---
def handle_creative_workflow():
    """Handles the main creative workflow menu."""
    while True:
        console.clear()
        current_novel_name = get_novel_name()
        first_item = f"确立一句话主题 - 《{current_novel_name}》" if current_novel_name != "未命名小说" else "确立一句话主题"
        
        menu_options = [
            first_item, "扩展成一段话主题", "世界设定", "编辑故事大纲", 
            "编辑分章细纲", "编辑章节概要", "生成小说正文", "返回项目工作台"
        ]
        choice = ui.display_menu("创作流程", menu_options)

        actions = {'1': handle_theme_one_line, '2': handle_theme_paragraph, '3': handle_world_setting, 
                   '4': handle_story_outline, '5': handle_chapter_outline, '6': handle_chapter_summary, '7': handle_novel_generation}
        
        if choice in actions:
            actions[choice]()
        elif choice == '0':
            break

# --- Step 1: One-Line Theme ---
def handle_theme_one_line():
    """Handles creating or updating the one-sentence theme and novel name."""
    current_data = get_data_manager().read_theme_one_line()
    current_novel_name = get_novel_name()
    current_theme = current_data.get("theme", "") if isinstance(current_data, dict) else (current_data or "")

    ui.print_info(f"\n--- 当前状态 ---\n小说名称: {current_novel_name}\n一句话主题: {current_theme or '(尚未设置)'}\n------------------\n")
    
    action = ui.display_menu("请选择操作：", ["设置小说名称", "设置一句话主题", "同时设置", "返回"])
    
    if action == "1":
        set_novel_name()
        ui.pause()
    elif action == "2":
        new_theme = ui.prompt("请输入您的一句话主题:", default=current_theme)
        if new_theme and new_theme.strip():
            get_data_manager().write_theme_one_line({"novel_name": current_novel_name, "theme": new_theme.strip()})
            ui.print_success("主题已更新")
        ui.pause()
    elif action == "3":
        new_name = ui.prompt("请输入小说名称:", default=current_novel_name)
        if new_name and new_name.strip():
            new_theme = ui.prompt("请输入您的一句话主题:", default=current_theme)
            if new_theme and new_theme.strip():
                get_data_manager().write_theme_one_line({"novel_name": new_name.strip(), "theme": new_theme.strip()})
                ui.print_success("名称和主题已更新")
        ui.pause()
    elif action == "0":
        # 选择返回时直接返回，不需要暂停
        return

def set_novel_name():
    current_name = get_novel_name()
    new_name = ui.prompt("请输入新的小说名称:", default=current_name)
    if new_name and new_name.strip() and new_name != current_name:
        current_data = get_data_manager().read_theme_one_line()
        current_theme = current_data.get("theme", "") if isinstance(current_data, dict) else (current_data or "")
        get_data_manager().write_theme_one_line({"novel_name": new_name.strip(), "theme": current_theme})
        ui.print_success(f"小说名称已更新为: {new_name}")

# --- Step 2: Paragraph Theme ---
def handle_theme_paragraph():
    """Handles creating, viewing, editing, and deleting the paragraph-length theme."""
    dm = get_data_manager()
    if not dm: return
    
    while True:
        theme_paragraph = dm.read_theme_paragraph()
        status = "已设置" if theme_paragraph else "未设置"
        
        ui.print_info(f"\n当前段落主题状态: {status}")
        
        options = ["查看当前主题", "生成新的主题（智能版）", "生成新的主题（简单版）", "编辑当前主题", "删除当前主题", "返回"]
        action = ui.display_menu("段落主题管理:", options)

        if action == "1":
            view_theme_paragraph(theme_paragraph)
        elif action == "2":
            generate_enhanced_theme_paragraph(dm)
        elif action == "3":
            generate_theme_paragraph(dm)
        elif action == "4":
            edit_theme_paragraph(dm, theme_paragraph)
        elif action == "5":
            delete_theme_paragraph(dm)
        elif action == "0":
            break

def generate_enhanced_theme_paragraph(dm):
    """使用增强版工作流生成主题段落"""
    theme_one_line_data = dm.read_theme_one_line()
    if not isinstance(theme_one_line_data, dict) or not theme_one_line_data.get("theme"):
        ui.print_warning("请先设置一句话主题。")
        ui.pause()
        return

    # 使用新的主题段落服务
    from theme_paragraph_service import theme_paragraph_service
    
    success = theme_paragraph_service.run_enhanced_theme_paragraph_workflow(theme_one_line_data)
    
    if success:
        ui.print_success("增强版主题段落生成完成！")
    else:
        ui.print_warning("增强版主题段落生成被取消或失败。")
    
    ui.pause()

def view_theme_paragraph(theme_paragraph):
    if theme_paragraph:
        ui.print_panel(theme_paragraph, title="当前段落主题")
    else:
        ui.print_warning("尚未设置段落主题。")
    ui.pause()

def generate_theme_paragraph(dm):
    theme_one_line_data = dm.read_theme_one_line()
    if not isinstance(theme_one_line_data, dict) or not theme_one_line_data.get("theme"):
        ui.print_warning("请先设置一句话主题。")
        ui.pause()
        return

    if not llm_service.is_available():
        ui.print_error("AI服务不可用，请检查配置。")
        ui.pause()
        return
        
    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）:")
    
    # 直接调用同步函数
    ui.print_info("正在生成段落主题...")
    new_theme = llm_service.generate_theme_paragraph(theme_one_line_data, user_prompt)

    if new_theme:
        dm.write_theme_paragraph(new_theme)
        ui.print_success("段落主题已生成并保存。")
        ui.print_panel(new_theme, title="新生成的段落主题")
    else:
        ui.print_error("生成段落主题失败。")
    ui.pause()

def edit_theme_paragraph(dm, current_theme):
    if not current_theme:
        ui.print_warning("没有可编辑的主题。")
        ui.pause()
        return
        
    edited_theme = ui.prompt("请编辑您的段落主题:", default=current_theme, multiline=True)
    if edited_theme and edited_theme.strip() != current_theme:
        dm.write_theme_paragraph(edited_theme.strip())
        ui.print_success("段落主题已更新。")
    else:
        ui.print_warning("未作修改或输入为空。")
    ui.pause()

def delete_theme_paragraph(dm):
    if not dm.read_theme_paragraph():
        ui.print_warning("没有可删除的主题。")
        ui.pause()
        return

    if ui.confirm("确定要删除当前的段落主题吗？"):
        dm.delete_theme_paragraph()
        ui.print_success("段落主题已删除。")
    else:
        ui.print_warning("操作已取消。")
    ui.pause()

# --- Step 3: World Setting ---
def handle_world_setting():
    """Handles world setting management."""
    while True:
        choice = ui.display_menu("请选择要管理的世界设定类型：", ["角色管理", "场景管理", "道具管理", "返回"])
        if choice == "1": handle_characters()
        elif choice == "2": handle_locations()
        elif choice == "3": handle_items()
        elif choice == "0": break

# --- Step 4: Story Outline ---
def handle_story_outline():
    """Handles creating, viewing, editing, and deleting the story outline."""
    dm = get_data_manager()
    if not dm: return

    while True:
        story_outline = dm.read_story_outline()
        status = "已设置" if story_outline else "未设置"
        ui.print_info(f"\n当前故事大纲状态: {status}")

        options = ["查看当前大纲", "生成新的大纲", "编辑当前大纲", "删除当前大纲", "返回"]
        action = ui.display_menu("故事情节大纲管理:", options)

        if action == "1":
            view_story_outline(story_outline)
        elif action == "2":
            generate_story_outline(dm)
        elif action == "3":
            edit_story_outline(dm, story_outline)
        elif action == "4":
            delete_story_outline(dm)
        elif action == "0":
            break

def view_story_outline(story_outline):
    if story_outline:
        ui.print_panel(story_outline, title="当前故事大纲")
    else:
        ui.print_warning("尚未设置故事大纲。")
    ui.pause()

def generate_story_outline(dm):
    # 检查前置条件
    theme_paragraph = dm.read_theme_paragraph()
    if not theme_paragraph:
        ui.print_warning("请先设置段落主题。")
        ui.pause()
        return

    if not llm_service.is_available():
        ui.print_error("AI服务不可用，请检查配置。")
        ui.pause()
        return
        
    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）:")
    
    # 获取必要信息
    one_line_theme = dm.read_theme_one_line()
    paragraph_theme = dm.read_theme_paragraph()
    characters_info = dm.get_characters_info_string()

    # 直接调用同步函数并显示进度消息
    ui.print_info("正在生成故事大纲...")
    
    new_outline = llm_service.generate_story_outline(
        one_line_theme, 
        paragraph_theme, 
        characters_info, 
        user_prompt or ""
    )

    if new_outline:
        dm.write_story_outline(new_outline)
        ui.print_success("故事大纲已生成并保存。")
        ui.print_panel(new_outline, title="新生成的故事大纲")
    else:
        ui.print_error("生成故事大纲失败。")
    ui.pause()

def edit_story_outline(dm, current_outline):
    if not current_outline:
        ui.print_warning("没有可编辑的大纲。")
        ui.pause()
        return
        
    edited_outline = ui.prompt("请编辑您的故事大纲:", default=current_outline, multiline=True)
    if edited_outline and edited_outline.strip() != current_outline:
        dm.write_story_outline(edited_outline.strip())
        ui.print_success("故事大纲已更新。")
    else:
        ui.print_warning("未作修改或输入为空。")
    ui.pause()

def delete_story_outline(dm):
    if not dm.read_story_outline():
        ui.print_warning("没有可删除的大纲。")
        ui.pause()
        return

    if ui.confirm("确定要删除当前的故事大纲吗？"):
        dm.delete_story_outline()
        ui.print_success("故事大纲已删除。")
    else:
        ui.print_warning("操作已取消。")
    ui.pause()

# --- Step 5: Chapter Outline ---
def handle_chapter_outline():
    """Handles the multi-chapter outline management."""
    dm = get_data_manager()
    if not dm: return

    while True:
        chapters = _sanitize_chapters(dm.read_chapter_outline())
        status = f"已有 {len(chapters)} 章" if chapters else "未设置"
        ui.print_info(f"\n当前分章细纲状态: {status}")

        options = ["查看所有章节细纲", "生成新的分章细纲", "编辑指定章节", "删除指定章节", "全部删除", "返回"]
        action = ui.display_menu("分章细纲管理:", options)

        if action == "1":
            view_chapter_outlines(chapters)
        elif action == "2":
            generate_chapter_outline(dm, chapters)
        elif action == "3":
            edit_chapter_outline(dm, chapters)
        elif action == "4":
            delete_single_chapter_outline(dm, chapters)
        elif action == "5":
            delete_all_chapter_outlines(dm)
        elif action == "0":
            break

def view_chapter_outlines(chapters):
    if not chapters:
        ui.print_warning("尚未生成分章细纲。")
        ui.pause()
        return
    
    console.print(Panel(Text("📚 完整章节大纲", justify="center"), border_style="bold magenta"))

    for chapter in chapters:
        order = chapter.get("order", "N/A")
        title = chapter.get("title", "无标题")
        outline = chapter.get("outline", "无大纲内容。")
        
        content = f"[bold]{title}[/bold]\n\n{outline}"
        ui.print_panel(content, title=f"第 {order} 章")

    ui.pause()

def generate_chapter_outline(dm, current_chapters):
    if current_chapters:
        if not ui.confirm("已存在分章细纲，重新生成将覆盖所有内容，确定吗？"):
            ui.print_warning("操作已取消。")
            ui.pause()
            return
            
    # 检查前置条件
    story_outline = dm.read_story_outline()
    if not story_outline:
        ui.print_warning("请先设置故事大纲。")
        ui.pause()
        return

    if not llm_service.is_available():
        ui.print_error("AI服务不可用，请检查配置。")
        ui.pause()
        return
        
    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）:")
    
    # 获取必要信息
    one_line_theme = dm.read_theme_one_line()
    characters_info = dm.get_characters_info_string()
    
    # 直接调用同步函数并显示进度消息
    ui.print_info("正在生成分章细纲...")
    
    new_chapters_result = llm_service.generate_chapter_outline(
        one_line_theme, 
        story_outline, 
        characters_info, 
        user_prompt or ""
    )

    if new_chapters_result:
        try:
            # 处理返回结果，可能是JSON字典或字符串
            if isinstance(new_chapters_result, dict) and 'chapters' in new_chapters_result:
                # 如果直接返回字典格式
                new_chapters = new_chapters_result['chapters']
            elif isinstance(new_chapters_result, str):
                # 如果返回字符串，尝试解析JSON
                parsed_result = json.loads(new_chapters_result)
                if isinstance(parsed_result, dict) and 'chapters' in parsed_result:
                    new_chapters = parsed_result['chapters']
                elif isinstance(parsed_result, list):
                    new_chapters = parsed_result
                else:
                    raise ValueError("JSON格式不正确")
            else:
                raise ValueError("返回格式不被支持")
            
            if isinstance(new_chapters, list) and new_chapters:
                # 确保章节数据格式正确
                new_chapters = _sanitize_chapters(new_chapters)
                dm.write_chapter_outline(new_chapters)
                ui.print_success(f"已成功生成并保存 {len(new_chapters)} 章细纲。")
                view_chapter_outlines(new_chapters)
            else:
                raise ValueError("生成的章节列表为空或格式错误")
        except (json.JSONDecodeError, ValueError) as e:
            ui.print_error(f"AI返回的格式无效，无法解析分章细纲: {e}")
            ui.print_info("请尝试调整Prompt或模型，期望返回一个JSON格式的章节列表。")
            ui.print_info("原始返回内容：")
            ui.print(str(new_chapters_result))

    else:
        ui.print_error("生成分章细纲失败。")
    ui.pause()

def edit_chapter_outline(dm, chapters):
    if not chapters:
        ui.print_warning("没有可编辑的章节。")
        ui.pause()
        return

    chapter_titles = [ch.get('title', '无标题') for ch in chapters]
    choice_str = ui.display_menu("请选择要编辑的章节:", chapter_titles + ["返回"])
    
    if choice_str == '0':
        return
    
    if choice_str and choice_str.isdigit():
        choice_idx = int(choice_str) - 1
        if 0 <= choice_idx < len(chapters):
            chapter_to_edit = chapters[choice_idx]
            
            ui.print_panel(f"标题: {chapter_to_edit.get('title')}\n\n大纲: {chapter_to_edit.get('outline')}", title=f"编辑 第{chapter_to_edit['order']}章")
            
            new_title = ui.prompt("请输入新标题:", default=chapter_to_edit.get('title', ''))
            new_outline = ui.prompt("请输入新大纲:", default=chapter_to_edit.get('outline', ''), multiline=True)
            
            if new_title and new_outline:
                chapters[choice_idx]['title'] = new_title
                chapters[choice_idx]['outline'] = new_outline
                dm.write_chapter_outline(chapters)
                ui.print_success("章节已更新。")
            else:
                ui.print_warning("标题或大纲不能为空，未作修改。")
        else:
            ui.print_warning("无效的选择。")
    ui.pause()

def delete_single_chapter_outline(dm, chapters):
    if not chapters:
        ui.print_warning("没有可删除的章节。")
        ui.pause()
        return

    chapter_titles = [ch.get('title', '无标题') for ch in chapters]
    choice_str = ui.display_menu("请选择要删除的章节:", chapter_titles + ["返回"])
    
    if choice_str == '0':
        return
    
    if choice_str and choice_str.isdigit():
        choice_idx = int(choice_str) - 1
        if 0 <= choice_idx < len(chapters):
            if ui.confirm(f"确定要删除 '{chapters[choice_idx].get('title')}' 吗？"):
                chapters.pop(choice_idx)
                # Re-order remaining chapters
                for i, ch in enumerate(chapters):
                    ch['order'] = i + 1
                dm.write_chapter_outline(chapters)
                ui.print_success("章节已删除。")
            else:
                ui.print_warning("操作已取消。")
        else:
            ui.print_warning("无效的选择。")
    ui.pause()

def delete_all_chapter_outlines(dm):
    if not dm.read_chapter_outline():
        ui.print_warning("没有可删除的章节。")
        ui.pause()
        return

    if ui.confirm("警告：这将删除所有章节细纲，确定吗？"):
        dm.delete_chapter_outline()
        ui.print_success("所有章节细纲已删除。")
    else:
        ui.print_warning("操作已取消。")
    ui.pause()

# --- Step 6: Chapter Summary ---
def handle_chapter_summary():
    """Handles chapter summary generation and management."""
    dm = get_data_manager()
    if not dm: return

    # Ensure each chapter has an order/number for later use
    chapters = dm.read_chapter_outline()
    for i, chapter in enumerate(chapters):
        chapter['order'] = i + 1

    while True:
        # Re-read summaries inside the loop to get the latest state
        summaries = dm.read_chapter_summaries()
        
        if not chapters:
            ui.print_warning("请先完成分章细纲的编辑。")
            ui.pause()
            return

        completed_count = len(summaries)
        total_count = len(chapters)
        status = f"已完成 {completed_count}/{total_count} 章"
        ui.print_info(f"\n当前章节概要状态: {status}")

        options = ["查看章节概要", "批量生成所有未完成的概要", "生成或修改单个概要", "删除单个概要", "返回"]
        action = ui.display_menu("章节概要管理:", options)

        if action == "1":
            view_chapter_summaries(chapters, summaries)
        elif action == "2":
            generate_all_summaries(dm, chapters, summaries)
        elif action == "3":
            generate_single_summary(dm, chapters, summaries)
        elif action == "4":
            delete_single_summary(dm, summaries)
        elif action == "0":
            break

def view_chapter_summaries(chapters, summaries):
    if not chapters:
        ui.print_warning("尚未创建任何分章细纲，无法查看概要。")
        ui.pause()
        return

    ui.print_info("\n--- 所有章节概要 ---")
    for i, chapter_data in enumerate(chapters):
        order = chapter_data.get("order", i + 1)
        title = chapter_data.get("title", f"第{order}章")
        
        summary_key = f"chapter_{order}"
        summary_content = summaries.get(summary_key, {}).get("summary", "尚未生成")
        
        ui.print_panel(summary_content, title=title)

    if not summaries:
        ui.print_info("\n提示：目前还没有任何已生成的章节概要。")

    ui.pause()

def generate_all_summaries(dm, chapters, summaries):
    chapters_to_generate = []
    for i, ch in enumerate(chapters):
        order = ch.get("order", i + 1)
        if f"chapter_{order}" not in summaries:
            chapters_to_generate.append(ch)

    if not chapters_to_generate:
        ui.print_info("所有章节概要均已生成。")
        ui.pause()
        return

    if not llm_service.is_available():
        ui.print_error("AI服务不可用，请检查配置。")
        ui.pause()
        return

    if not ui.confirm(f"将为 {len(chapters_to_generate)} 个章节批量生成概要，确定吗？"):
        ui.print_warning("操作已取消。")
        ui.pause()
        return
    
    # 获取上下文信息
    context = dm.get_context_info()
    user_prompt = ""  # 批量生成暂时不支持用户自定义提示
    
    # 逐个生成章节概要（同步方式）
    ui.print_info(f"开始批量生成 {len(chapters_to_generate)} 个章节概要...")
    results = {}
    failed_chapters = []
    
    for i, chapter in enumerate(chapters_to_generate, 1):
        order = chapter.get("order", i)
        title = chapter.get("title", f"第{order}章")
        
        ui.print_info(f"正在生成第{order}章概要: {title}... ({i}/{len(chapters_to_generate)})")
        
        try:
            summary = llm_service.generate_chapter_summary(
                chapter, 
                order, 
                context, 
                user_prompt
            )
            
            if summary:
                results[f"chapter_{order}"] = {
                    "title": title,
                    "summary": summary
                }
                ui.print_success(f"第{order}章概要生成成功。")
            else:
                failed_chapters.append(order)
                ui.print_error(f"第{order}章概要生成失败。")
                
        except Exception as e:
            failed_chapters.append(order)
            ui.print_error(f"第{order}章概要生成异常: {e}")
        

    if results:
        new_summaries = {**summaries, **results}
        dm.write_chapter_summaries(new_summaries)
        ui.print_success(f"已成功生成 {len(results)} 个概要并保存。")
        if failed_chapters:
            ui.print_warning(f"失败的章节: {failed_chapters}")
    else:
        ui.print_error("批量生成概要失败。")
    ui.pause()

def generate_single_summary(dm, chapters, summaries):
    """Handles the UI for generating or updating a summary for a single chapter."""
    chapter_titles = []
    for ch in chapters:
        order = ch.get('order')
        title = ch.get('title', '无标题')
        status = "已生成" if f"chapter_{order}" in summaries else "未生成"
        chapter_titles.append(f"({status}) {title}")

    choice_str = ui.display_menu("请选择要生成/修改概要的章节:", chapter_titles + ["返回"])

    # Handle returning to the previous menu
    if choice_str == '0':
        return

    # Handle a valid numeric choice
    if choice_str and choice_str.isdigit():
        choice_idx = int(choice_str) - 1
        if 0 <= choice_idx < len(chapters):
            chapter = chapters[choice_idx]
            chapter_key = f"chapter_{chapter['order']}"
            context = dm.get_context_info()

            # Confirm if overwriting an existing summary, or offer to edit.
            if chapter_key in summaries:
                if ui.confirm("该章节已有概要。是否重新生成？(选择 '否' 将进入编辑模式)"):
                    # User chose 'yes' to regenerate, so we let the function continue to the generation logic.
                    pass
                else:
                    # User chose 'no', so we start the editing process.
                    current_summary = summaries.get(chapter_key, {}).get("summary", "")
                    if not current_summary:
                        ui.print_error("错误：找不到要编辑的概要内容。")
                        ui.pause()
                        return

                    edited_summary = ui.prompt(
                        "请编辑您的章节概要:",
                        default=current_summary,
                        multiline=True
                    )

                    if edited_summary and edited_summary.strip() != current_summary:
                        summaries[chapter_key]['summary'] = edited_summary.strip()
                        dm.write_chapter_summaries(summaries)
                        ui.print_success("概要已更新。")
                    else:
                        ui.print_warning("未作修改或输入为空。")
                    
                    ui.pause()
                    return # Editing is done, so we exit the function.

            # Get user input and run generation (for new or regenerated summaries)
            user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）:")
            
            # 直接调用同步函数
            ui.print_info(f"正在为'{chapter.get('title')}'生成概要...")
            new_summary = llm_service.generate_chapter_summary(
                chapter,
                chapter['order'],
                context,
                user_prompt
            )

            # Process results
            if new_summary:
                summaries[chapter_key] = {"summary": new_summary, "title": chapter.get('title')}
                dm.write_chapter_summaries(summaries)
                ui.print_success("概要已生成并保存。")
                ui.print_panel(new_summary, title=f"新概要: {chapter.get('title')}")
            else:
                ui.print_error("生成概要失败。")
            
            ui.pause() # Pause after the action is complete
            return # Exit the function since we're done

    # If the input was not a valid choice, show an error
    ui.print_warning("无效的选择。")
    ui.pause()


def delete_single_summary(dm, summaries):
    if not summaries:
        ui.print_warning("没有可删除的概要。")
        ui.pause()
        return

    summary_titles = [f"第{k.split('_')[1]}章: {v.get('title', '无标题')}" for k, v in summaries.items()]
    choice_str = ui.display_menu("请选择要删除的概要:", summary_titles + ["返回"])

    if choice_str == '0':
        return

    if choice_str and choice_str.isdigit():
        choice_idx = int(choice_str) - 1
        # Note: This way of getting the key is fragile. A better way would be to pass a list of keys.
        # For now, this will work if the list order is preserved.
        if 0 <= choice_idx < len(summaries):
            key_to_delete = list(summaries.keys())[choice_idx]
            if ui.confirm(f"确定要删除 '{summaries[key_to_delete].get('title')}' 的概要吗？"):
                del summaries[key_to_delete]
                dm.write_chapter_summaries(summaries)
                ui.print_success("概要已删除。")
            else:
                ui.print_warning("操作已取消。")
        else:
            ui.print_warning("无效的选择。")
    ui.pause()

# --- Step 7: Novel Generation ---
def handle_novel_generation():
    """Handles novel chapter generation and management."""
    dm = get_data_manager()
    if not dm: return

    while True:
        chapters = _sanitize_chapters(dm.read_chapter_outline())
        summaries = dm.read_chapter_summaries()
        novel_chapters = dm.read_novel_chapters()

        if not chapters or not summaries:
            ui.print_warning("请先完成分章细纲和章节概要的编辑。")
            ui.pause()
            return

        completed_count = len(novel_chapters)
        total_count = len(chapters)
        status = f"已生成 {completed_count}/{total_count} 章"
        ui.print_info(f"\n当前小说正文状态: {status}")

        options = ["查看章节正文", "批量生成未完成章节", "生成/重新生成单个章节", "手动编辑章节正文", "删除单个章节", "返回"]
        action = ui.display_menu("小说正文生成管理:", options)

        if action == "1":
            view_novel_chapter(chapters, novel_chapters)
        elif action == "2":
            generate_all_novel_chapters(dm, chapters, summaries, novel_chapters)
        elif action == "3":
            generate_single_novel_chapter(dm, chapters, summaries, novel_chapters)
        elif action == "4":
            edit_novel_chapter(dm, chapters, novel_chapters)
        elif action == "5":
            delete_novel_chapter(dm, chapters, novel_chapters)
        elif action == "0":
            break

def view_novel_chapter(chapters, novel_chapters):
    if not novel_chapters:
        ui.print_warning("尚无任何章节正文。")
        ui.pause()
        return

    chapter_map = {int(k.split('_')[1]): v.get('title', f"第{k.split('_')[1]}章") for k, v in novel_chapters.items()}
    chapter_titles = [f"第{order}章: {title}" for order, title in sorted(chapter_map.items())]
    
    choice_str = ui.display_menu("请选择要查看的章节:", chapter_titles + ["返回"])
    
    if choice_str == '0':
        return
    
    if choice_str and choice_str.isdigit():
        choice_idx = int(choice_str) - 1
        sorted_orders = sorted(chapter_map.keys())
        if 0 <= choice_idx < len(sorted_orders):
            order = sorted_orders[choice_idx]
            chapter_data = novel_chapters.get(f"chapter_{order}")
            if chapter_data:
                ui.print_panel(chapter_data.get('content', '无内容'), title=chapter_data.get('title', ''))
        else:
            ui.print_warning("无效的选择。")
    ui.pause()

def generate_all_novel_chapters(dm, chapters, summaries, novel_chapters):
    # Implementation for batch generation, adapted from old cli
    context = dm.get_context_info()
    chapters_to_generate = [ch for ch in chapters if f"chapter_{ch['order']}" not in novel_chapters]
    
    if not chapters_to_generate:
        ui.print_info("所有章节正文均已生成。")
        ui.pause()
        return

    if not ui.confirm(f"将为 {len(chapters_to_generate)} 个章节生成正文，确定吗？"):
        ui.print_warning("操作已取消。")
        return

    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）:")

    # 同步顺序生成所有章节
    ui.print_info(f"开始生成 {len(chapters_to_generate)} 个章节正文...")
    results = {}
    failed_chapters = []
    
    for i, chapter in enumerate(chapters_to_generate, 1):
        order = chapter['order']
        title = chapter.get('title', f'第{order}章')
        
        ui.print_info(f"正在生成第{order}章: {title}... ({i}/{len(chapters_to_generate)})")
        
        try:
            content = llm_service.generate_novel_chapter(
                chapter, 
                summaries.get(f"chapter_{order}"), 
                order, 
                context, 
                user_prompt
            )
            
            if content:
                results[f"chapter_{order}"] = {
                    "title": title, 
                    "content": content, 
                    "word_count": len(content)
                }
                ui.print_success(f"第{order}章生成成功。")
            else:
                failed_chapters.append(order)
                ui.print_error(f"第{order}章生成失败。")
                
        except Exception as e:
            failed_chapters.append(order)
            ui.print_error(f"第{order}章生成异常: {e}")
        

    if results:
        updated_chapters = {**novel_chapters, **results}
        dm.write_novel_chapters(updated_chapters)
        ui.print_success(f"成功生成 {len(results)} 个章节。")
        if failed_chapters:
            ui.print_warning(f"失败章节: {failed_chapters}")
    else:
        ui.print_error("所有章节生成均失败。")
    ui.pause()


def generate_single_novel_chapter(dm, chapters, summaries, novel_chapters):
    chapter_titles = []
    for i, chapter_data in enumerate(chapters):
        order = chapter_data.get('order', i + 1)
        key = f"chapter_{order}"
        status = "已生成" if key in novel_chapters else "未生成"
        title = chapter_data.get('title', '无标题')
        chapter_titles.append(f"({status}) {title}")

    choice_str = ui.display_menu("请选择要生成正文的章节:", chapter_titles + ["返回"])

    if choice_str == '0':
        return

    if choice_str and choice_str.isdigit():
        choice_idx = int(choice_str) - 1
        if 0 <= choice_idx < len(chapters):
            chapter = chapters[choice_idx]
            order = chapter.get('order', choice_idx + 1)
            chapter_key = f"chapter_{order}"

            if chapter_key in novel_chapters and not ui.confirm("该章节已有正文，是否覆盖？"):
                return

            user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）:")
            context = dm.get_context_info()

            # 直接调用同步函数
            ui.print_info(f"正在生成'{chapter.get('title', '无标题')}'...")
            content = llm_service.generate_novel_chapter(
                chapter, 
                summaries.get(chapter_key), 
                order, 
                context, 
                user_prompt
            )

            if content:
                novel_chapters[chapter_key] = {"title": chapter.get('title', '无标题'), "content": content, "word_count": len(content)}
                dm.write_novel_chapters(novel_chapters)
                ui.print_success("章节正文已生成并保存。")
            else:
                ui.print_error("章节生成失败。")
            ui.pause()
        else:
            ui.print_warning("无效的选择。")
            ui.pause()


def edit_novel_chapter(dm, chapters, novel_chapters):
    if not novel_chapters:
        ui.print_warning("没有可编辑的章节。")
        return

    chapter_map = {int(k.split('_')[1]): v.get('title', f"第{k.split('_')[1]}章") for k, v in novel_chapters.items()}
    chapter_titles = [f"第{order}章: {title}" for order, title in sorted(chapter_map.items())]

    choice_str = ui.display_menu("请选择要编辑的章节:", chapter_titles + ["返回"])

    if choice_str == '0':
        return

    if choice_str and choice_str.isdigit():
        choice_idx = int(choice_str) - 1
        sorted_orders = sorted(chapter_map.keys())
        if 0 <= choice_idx < len(sorted_orders):
            order = sorted_orders[choice_idx]
            chapter_key = f"chapter_{order}"
            current_content = novel_chapters[chapter_key].get('content', '')
            
            edited_content = ui.prompt("请编辑章节正文:", default=current_content, multiline=True)
            if edited_content and edited_content.strip() != current_content:
                novel_chapters[chapter_key]['content'] = edited_content
                novel_chapters[chapter_key]['word_count'] = len(edited_content)
                dm.write_novel_chapters(novel_chapters)
                ui.print_success("章节已更新。")
            else:
                ui.print_warning("内容未修改。")
        else:
            ui.print_warning("无效的选择。")
    ui.pause()


def delete_novel_chapter(dm, chapters, novel_chapters):
    if not novel_chapters:
        ui.print_warning("没有可删除的章节。")
        return

    chapter_map = {int(k.split('_')[1]): v.get('title', f"第{k.split('_')[1]}章") for k, v in novel_chapters.items()}
    chapter_titles = [f"第{order}章: {title}" for order, title in sorted(chapter_map.items())]

    choice_str = ui.display_menu("请选择要删除的章节:", chapter_titles + ["返回"])
    
    if choice_str == '0':
        return
    
    if choice_str and choice_str.isdigit():
        choice_idx = int(choice_str) - 1
        sorted_orders = sorted(chapter_map.keys())
        if 0 <= choice_idx < len(sorted_orders):
            order = sorted_orders[choice_idx]
            chapter_key = f"chapter_{order}"
            
            if ui.confirm(f"确定要删除 '{chapter_map[order]}' 的正文吗？"):
                del novel_chapters[chapter_key]
                dm.write_novel_chapters(novel_chapters)
                ui.print_success("章节正文已删除。")
            else:
                ui.print_warning("操作已取消。")
        else:
            ui.print_warning("无效的选择。")
    ui.pause()
