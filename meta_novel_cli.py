import sys
import os

# --- 导入配置模块并设置代理 ---
from config import setup_proxy
setup_proxy()  # 必须在导入网络库之前设置代理
# ----------------------------------------------------


import json
import re
import datetime
import asyncio
from llm_service import llm_service
from project_data_manager import project_data_manager
from progress_utils import AsyncProgressManager, run_with_progress
from retry_utils import batch_retry_manager
from config import RETRY_CONFIG, update_retry_config
from entity_manager import handle_characters, handle_locations, handle_items
from ui_utils import ui, console
from rich.panel import Panel
from rich.text import Text
from project_ui import handle_project_management

# 获取当前数据管理器的便捷函数
def get_data_manager():
    """获取当前项目的数据管理器"""
    return project_data_manager.get_data_manager()

# --- Helper Functions ---
def ensure_meta_dir():
    """Ensures the meta directory exists."""
    # 现在由data_manager自动处理
    pass


def handle_theme_one_line():
    """Handles creating or updating the one-sentence theme and novel name."""
    ensure_meta_dir()
    
    # 获取当前数据
    current_data = get_data_manager().read_theme_one_line()
    current_novel_name = get_novel_name()
    
    # 处理不同格式的主题数据
    if isinstance(current_data, dict):
        current_theme = current_data.get("theme", "")
    elif isinstance(current_data, str):
        current_theme = current_data
    else:
        current_theme = ""
    
    # 显示当前状态
    ui.print_info(f"\n--- 当前状态 ---")
    ui.print_info(f"小说名称: {current_novel_name}")
    if current_theme:
        ui.print_info(f"一句话主题: {current_theme}")
    else:
        ui.print_info("一句话主题: (尚未设置)")
    ui.print_info("------------------\n")
    
    # 提供操作选项
    menu_options = [
        "设置小说名称",
        "设置一句话主题",
        "同时设置名称和主题",
        "返回主菜单"
    ]
    action = ui.display_menu("请选择您要进行的操作：", menu_options)
    
    if action is None or action == "4":
        ui.print_info("返回主菜单。\n")
        return
    elif action == "1":
        # 只设置小说名称
        set_novel_name()
    elif action == "2":
        # 只设置一句话主题
        new_theme = ui.prompt("请输入您的一句话主题:", default=current_theme)
        
        if new_theme is not None and new_theme.strip():
            # 保存主题，保持现有的小说名称
            new_data = {
                "novel_name": current_novel_name,
                "theme": new_theme.strip()
            }
            if get_data_manager().write_theme_one_line(new_data):
                ui.print_success(f"✅ 主题已更新为: {new_theme}\n")
            else:
                ui.print_error("❌ 保存主题时出错。\n")
        elif new_theme is None:
            ui.print_warning("操作已取消。\n")
        else:
            ui.print_warning("主题不能为空。\n")
    elif action == "3":
        # 同时设置名称和主题
        new_novel_name = ui.prompt("请输入小说名称:", default=current_novel_name if current_novel_name != "未命名小说" else "")
        
        if new_novel_name is None:
            ui.print_warning("操作已取消。\n")
            return
        
        new_novel_name = new_novel_name.strip()
        if not new_novel_name:
            ui.print_warning("小说名称不能为空。\n")
            return
        
        new_theme = ui.prompt("请输入您的一句话主题:", default=current_theme)
        
        if new_theme is None:
            ui.print_warning("操作已取消。\n")
            return
        
        new_theme = new_theme.strip()
        if not new_theme:
            ui.print_warning("主题不能为空。\n")
            return
        
        # 保存名称和主题
        new_data = {
            "novel_name": new_novel_name,
            "theme": new_theme
        }
        if get_data_manager().write_theme_one_line(new_data):
            ui.print_success(f"✅ 小说名称已设置为: {new_novel_name}")
            ui.print_success(f"✅ 主题已设置为: {new_theme}\n")
        else:
            ui.print_error("❌ 保存时出错.\n")


def handle_theme_paragraph():
    """Handles creating or updating the paragraph-long theme using an LLM."""
    ensure_meta_dir()

    # 首先检查一句话主题是否存在
    one_line_data = get_data_manager().read_theme_one_line()
    if not one_line_data:
        ui.print_warning("\n请先使用选项 [1] 确立一句话主题。")
        return
    
    # 获取实际的主题内容
    if isinstance(one_line_data, dict):
        one_line_theme = one_line_data.get("theme", "")
    elif isinstance(one_line_data, str):
        one_line_theme = one_line_data
    else:
        one_line_theme = ""
    
    if not one_line_theme.strip():
        ui.print_warning("\n请先使用选项 [1] 确立一句话主题。")
        return

    # 检查是否已有段落主题
    existing_paragraph = get_data_manager().read_theme_paragraph()

    if existing_paragraph:
        # 如果已有段落主题，显示并提供操作选项
        ui.print_info("\n--- 当前段落主题 ---")
        ui.print_info(existing_paragraph)
        ui.print_info("------------------------\n")

        action = ui.display_menu("请选择您要进行的操作：", [
            "查看当前内容（已显示）",
            "修改当前内容",
            "重新生成内容",
            "返回主菜单"
        ])

        if action is None or action == "4":
            ui.print_info("返回主菜单。\n")
            return
        elif action == "1":
            ui.print_info("当前内容已在上方显示。\n")
            return
        elif action == "2":
            edited_paragraph = ui.prompt("请修改您的段落主题:", default=existing_paragraph)
            if edited_paragraph and edited_paragraph.strip() and edited_paragraph != existing_paragraph:
                if get_data_manager().write_theme_paragraph(edited_paragraph):
                    ui.print_success("段落主题已更新.\n")
                else:
                    ui.print_error("保存段落主题时出错.\n")
            elif edited_paragraph is None:
                ui.print_warning("操作已取消.\n")
            else:
                ui.print_warning("内容未更改.\n")
            return
        elif action == "3":
            # 继续执行重新生成逻辑
            ui.print_info("\n正在重新生成段落主题...")
        else:
            return

    # 生成新的段落主题（无论是首次生成还是重新生成）
    if not one_line_theme.strip():
        ui.print_warning("\n一句话主题为空，请先使用选项 [1] 确立主题。")
        return
            
    ui.print_info(f'\n基于主题 "{one_line_theme}" 进行扩展...')

    # 获取用户自定义提示词
    ui.print_info("您可以输入额外的要求或指导来影响AI生成的内容。")
    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）", default="")

    if user_prompt is None:
        ui.print_warning("操作已取消。\n")
        return
    
    # 如果用户不想继续，提供确认选项
    if not user_prompt.strip():
        confirm = ui.confirm("确定要继续生成段落主题吗？")
        if not confirm:
            ui.print_warning("操作已取消。\n")
            return

    if not llm_service.is_available():
        print("AI服务不可用，请检查配置。")
        return

    if user_prompt.strip():
        print(f"用户指导：{user_prompt.strip()}")
    
    ui.print_info("正在调用 AI 生成段落主题，请稍候...")
    generated_paragraph = llm_service.generate_theme_paragraph(one_line_theme, user_prompt)
    
    if not generated_paragraph:
        ui.print_error("AI生成失败，请稍后重试。")
        return

    ui.print_info("\n--- AI 生成的段落主题 ---")
    ui.print_info(generated_paragraph)
    ui.print_info("------------------------\n")
    
    # 提供更清晰的操作选项
    action = ui.display_menu("请选择您要进行的操作：", [
        "接受并保存",
        "修改后保存", 
        "放弃此次生成"
    ])

    if action is None or action == "3":
        print("已放弃此次生成。\n")
        return
    elif action == "1":
        # 直接保存
        if get_data_manager().write_theme_paragraph(generated_paragraph):
            ui.print_success("段落主题已保存。\n")
        else:
            ui.print_error("保存段落主题时出错。\n")
    elif action == "2":
        # 修改后保存
        edited_paragraph = ui.prompt("请修改您的段落主题:", default=generated_paragraph)

        if edited_paragraph and edited_paragraph.strip():
            if get_data_manager().write_theme_paragraph(edited_paragraph):
                ui.print_success("段落主题已保存.\n")
            else:
                ui.print_error("保存段落主题时出错.\n")
        else:
            ui.print_warning("操作已取消或内容为空，未保存.\n")


def handle_world_setting():
    """Handles world setting management including characters, locations, and items."""
    ensure_meta_dir()
    
    # 检查前置条件
    one_line_exists, paragraph_exists = get_data_manager().check_prerequisites_for_world_setting()
    
    if not one_line_exists or not paragraph_exists:
        ui.print_warning("\n请先完成前面的步骤：")
        if not one_line_exists:
            ui.print_warning("- 步骤1: 确立一句话主题")
        if not paragraph_exists:
            ui.print_warning("- 步骤2: 扩展成一段话主题")
        ui.print_warning("\n世界设定需要基于明确的主题来创建角色、场景和道具。\n")
        return
    
    while True:
        choice = ui.display_menu("请选择要管理的世界设定类型：", [
            "角色管理",
            "场景管理",
            "道具管理",
            "返回主菜单"
        ])
        
        if choice is None or choice == "4":
            break
        elif choice == "1":
            handle_characters()
        elif choice == "2":
            handle_locations()
        elif choice == "3":
            handle_items()


# handle_characters 现在由 entity_manager 模块提供


# handle_locations 现在由 entity_manager 模块提供


# handle_items 现在由 entity_manager 模块提供


# ===== 实体管理函数现已移至 entity_manager 模块 =====

# 所有实体CRUD函数现已统一移至 entity_manager 模块


def handle_story_outline():
    """Handles story outline management with full CRUD operations."""
    ensure_meta_dir()
    
    # 检查前置条件
    one_line_exists, paragraph_exists = get_data_manager().check_prerequisites_for_story_outline()
    
    if not one_line_exists or not paragraph_exists:
        ui.print_warning("\n请先完成前面的步骤：")
        if not one_line_exists:
            ui.print_warning("- 步骤1: 确立一句话主题")
        if not paragraph_exists:
            ui.print_warning("- 步骤2: 扩展成一段话主题")
        ui.print_warning()
        return
    
    while True:
        # 每次循环都重新读取大纲数据
        current_outline = get_data_manager().read_story_outline()
        
        # 显示当前大纲状态
        if current_outline:
            ui.print_info("\n--- 当前故事大纲 ---")
            # 显示前200字符作为预览
            preview = current_outline[:200] + "..." if len(current_outline) > 200 else current_outline
            ui.print_info(preview)
            ui.print_info("------------------------\n")
            
            action = ui.display_menu("请选择您要进行的操作：", [
                "查看完整大纲",
                "修改当前大纲",
                "重新生成大纲",
                "返回主菜单"
            ])
            
            if action is None or action == "4":
                break
            elif action == "1":
                ui.print_info("\n--- 完整故事大纲 ---")
                ui.print_info(current_outline)
                ui.print_info("------------------------\n")
                
                # 等待用户确认后继续循环
                ui.prompt("按任意键继续...")
                continue
            elif action == "2":
                edit_outline()
                continue
            elif action == "3":
                ui.print_info("\n正在重新生成故事大纲...")
                generate_story_outline()
                continue
            else:
                break
        else:
            ui.print_info("\n当前没有故事大纲，让我们来生成一个。\n")
            # 生成新的故事大纲
            generate_story_outline()
            break


def generate_story_outline():
    """Generate a new story outline based on existing themes and characters."""
    # 读取主题信息
    one_line_data = get_data_manager().read_theme_one_line()
    if isinstance(one_line_data, dict):
        one_line_theme = one_line_data.get("theme", "")
    elif isinstance(one_line_data, str):
        one_line_theme = one_line_data
    else:
        one_line_theme = ""
        
    paragraph_theme = get_data_manager().read_theme_paragraph()
    
    # 读取角色信息（如果有的话）
    characters_info = get_data_manager().get_characters_info_string()
    
    ui.print_info(f"基于主题和角色信息生成故事大纲...")
    
    # 获取用户自定义提示词
    ui.print_info("您可以输入额外的要求或指导来影响AI生成故事大纲。")
    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）", default="")

    if user_prompt is None:
        ui.print_warning("操作已取消。\n")
        return
    
    # 如果用户不想继续，提供确认选项
    if not user_prompt.strip():
        confirm = ui.confirm("确定要继续生成故事大纲吗？")
        if not confirm:
            ui.print_warning("操作已取消。\n")
            return

    if user_prompt.strip():
        ui.print_info(f"用户指导：{user_prompt.strip()}")
    
    ui.print_info("正在调用 AI 生成故事大纲，请稍候...")
    generated_outline = llm_service.generate_story_outline(one_line_theme, paragraph_theme, characters_info, user_prompt)
    
    if not generated_outline:
        ui.print_error("AI生成失败，请稍后重试。")
        return

    ui.print_info("\n--- AI 生成的故事大纲 ---")
    ui.print_info(generated_outline)
    ui.print_info("------------------------\n")
    
    # 提供操作选项
    action = ui.display_menu("请选择您要进行的操作：", [
        "接受并保存",
        "修改后保存", 
        "放弃此次生成"
    ])

    if action is None or action == "3":
        ui.print_warning("已放弃此次生成。\n")
        return
    elif action == "1":
        # 直接保存
        if get_data_manager().write_story_outline(generated_outline):
            ui.print_success("故事大纲已保存。\n")
        else:
            ui.print_error("保存故事大纲时出错。\n")
    elif action == "2":
        # 修改后保存
        edited_outline = ui.prompt("请修改故事大纲:", default=generated_outline)

        if edited_outline and edited_outline.strip():
            if get_data_manager().write_story_outline(edited_outline):
                ui.print_success("故事大纲已保存.\n")
            else:
                ui.print_error("保存故事大纲时出错.\n")
        else:
            ui.print_warning("操作已取消或内容为空，未保存.\n")


def edit_outline():
    """Edit existing story outline."""
    current_outline = get_data_manager().read_story_outline()
    ui.print_info("\n--- 当前故事大纲 ---")
    ui.print_info(current_outline)
    ui.print_info("------------------------\n")
    
    edited_outline = ui.prompt("请修改故事大纲:", default=current_outline)
    
    if edited_outline and edited_outline.strip() and edited_outline != current_outline:
        if get_data_manager().write_story_outline(edited_outline):
            ui.print_success("故事大纲已更新。\n")
        else:
            ui.print_error("更新故事大纲时出错。\n")
    elif edited_outline is None:
        ui.print_warning("操作已取消。\n")
    else:
        ui.print_warning("内容未更改。\n")


def handle_chapter_outline():
    """Handles chapter outline management with full CRUD operations."""
    ensure_meta_dir()
    
    # 检查前置条件
    story_outline_exists = get_data_manager().check_prerequisites_for_chapter_outline()
    
    if not story_outline_exists:
        ui.print_warning("\n请先完成步骤4: 编辑故事大纲\n")
        return
    
    while True:
        # 每次循环都重新读取数据
        chapters = get_data_manager().read_chapter_outline()
        
        # 显示当前章节列表
        if chapters:
            ui.print_info("\n--- 当前分章细纲 ---")
            for i, chapter in enumerate(chapters, 1):
                title = chapter.get('title', f'第{i}章')
                outline = chapter.get('outline', '无大纲')
                preview = outline[:50] + "..." if len(outline) > 50 else outline
                ui.print_info(f"{i}. {title}: {preview}")
            ui.print_info("------------------------\n")
        else:
            ui.print_info("\n当前没有分章细纲。\n")
        
        # 操作选项
        choices = {
            "1": "生成分章细纲",
            "2": "添加新章节",
            "3": "查看章节详情",
            "4": "修改章节信息", 
            "5": "删除章节",
            "6": "返回主菜单"
        }
        
        if not chapters:
            # 如果没有章节，只显示生成和返回选项
            choices = {
                "1": "生成分章细纲",
                "2": "返回主菜单"
            }
        
        action = ui.display_menu("请选择您要进行的操作：", list(choices.values()))
        
        if action is None:
            break

        action_key = action.split('.')[0]

        if not chapters:
            if action_key == '1':
                generate_chapter_outline()
            elif action_key == '2':
                break
        else:
            if action_key == '1':
                generate_chapter_outline()
            elif action_key == '2':
                add_chapter()
            elif action_key == '3':
                view_chapter()
            elif action_key == '4':
                edit_chapter()
            elif action_key == '5':
                delete_chapter()
            elif action_key == '6':
                break


def generate_chapter_outline():
    """Generate chapter outline based on story outline."""
    # 读取故事大纲和其他信息
    story_outline = get_data_manager().read_story_outline()
    one_line_data = get_data_manager().read_theme_one_line()
    if isinstance(one_line_data, dict):
        one_line_theme = one_line_data.get("theme", "")
    elif isinstance(one_line_data, str):
        one_line_theme = one_line_data
    else:
        one_line_theme = ""
        
    characters_info = get_data_manager().get_characters_info_string()
    
    ui.print_info("基于故事大纲生成分章细纲...")
    
    # 获取用户自定义提示词
    ui.print_info("您可以输入额外的要求或指导来影响AI生成分章细纲。")
    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）", default="")

    if user_prompt is None:
        ui.print_warning("操作已取消.\n")
        return
    
    # 如果用户不想继续，提供确认选项
    if not user_prompt.strip():
        confirm = ui.confirm("确定要继续生成分章细纲吗？")
        if not confirm:
            ui.print_warning("操作已取消。\n")
            return

    if user_prompt.strip():
        ui.print_info(f"用户指导：{user_prompt.strip()}")
    
    ui.print_info("正在调用 AI 生成分章细纲，请稍候...")
    chapter_outline_data = llm_service.generate_chapter_outline(one_line_theme, story_outline, characters_info, user_prompt)
    
    if not chapter_outline_data:
        ui.print_error("AI生成失败，请稍后重试。")
        return

    # 显示生成的章节
    ui.print_info("\n--- AI 生成的分章细纲 ---")
    
    # 处理不同的返回格式
    if isinstance(chapter_outline_data, dict):
        chapters = chapter_outline_data.get('chapters', [])
        if not chapters:
            # 如果没有chapters字段，可能是直接返回的章节列表或其他格式
            ui.print_info("JSON解析结果：")
            ui.print_info(chapter_outline_data)
        else:
            for i, chapter in enumerate(chapters, 1):
                ui.print_info(f"\n第{i}章: {chapter.get('title', '无标题')}")
                ui.print_info(f"大纲: {chapter.get('outline', '无大纲')}")
    else:
        # 如果不是字典格式，直接显示原始内容
        ui.print_info("AI返回的原始内容：")
        ui.print_info(chapter_outline_data)
    
    ui.print_info("------------------------\n")
    
    # 提供操作选项
    action = ui.display_menu("请选择您要进行的操作：", [
        "接受并保存",
        "修改后保存", 
        "放弃此次生成"
    ])

    if action is None or action == "3":
        ui.print_warning("已放弃此次生成.\n")
        return
    elif action == "1":
        # 直接保存
        if isinstance(chapter_outline_data, dict):
            chapters_list = chapter_outline_data.get('chapters', [])
            if chapters_list:
                if get_data_manager().write_chapter_outline(chapters_list):
                    ui.print_success("分章细纲已保存.\n")
                else:
                    ui.print_error("保存分章细纲时出错.\n")
            else:
                ui.print_warning("生成的数据格式不正确，无法保存。请检查AI返回的内容格式.\n")
        else:
            ui.print_warning("生成的数据不是预期的JSON格式，无法直接保存。请选择修改后保存。\n")
    elif action == "2":
        # 修改后保存
        if isinstance(chapter_outline_data, dict):
            chapters = chapter_outline_data.get('chapters', [])
            if not chapters:
                ui.print_warning("无有效的章节数据可以修改。\n")
                return
        else:
            ui.print_warning("由于数据格式问题，请手动输入章节信息：\n")
            chapters = []
            
        # 让用户逐个确认或修改章节
        ui.print_info("请逐个确认或修改每个章节：\n")
        modified_chapters = []
        
        if chapters:
            for i, chapter in enumerate(chapters, 1):
                ui.print_info(f"--- 第{i}章 ---")
                ui.print_info(f"当前标题: {chapter.get('title', '无标题')}")
                ui.print_info(f"当前大纲: {chapter.get('outline', '无大纲')}")
                
                keep_chapter = ui.confirm(f"保留第{i}章吗？")
                if keep_chapter:
                    # 可以选择修改标题和大纲
                    modify = ui.confirm("需要修改这一章吗？")
                    if modify:
                        new_title = ui.prompt("章节标题:", default=chapter.get('title', ''))
                        new_outline = ui.prompt("章节大纲:", default=chapter.get('outline', ''))
                        if new_title is not None and new_outline is not None:
                            modified_chapters.append({"title": new_title, "outline": new_outline})
                        else:
                            modified_chapters.append(chapter)
                    else:
                        modified_chapters.append(chapter)
        else:
            # 手动创建章节
            while True:
                add_chapter = ui.confirm("添加一个章节吗？")
                if not add_chapter:
                    break
                    
                title = ui.prompt("章节标题:")
                if not title:
                    continue
                    
                outline = ui.prompt("章节大纲:")
                if outline is None:
                    continue
                    
                modified_chapters.append({"title": title.strip(), "outline": outline.strip()})
        
        if modified_chapters:
            if get_data_manager().write_chapter_outline(modified_chapters):
                ui.print_success("分章细纲已保存.\n")
            else:
                ui.print_error("保存分章细纲时出错.\n")
        else:
            ui.print_warning("未保存任何章节.\n")


def add_chapter():
    """Add a new chapter."""
    title = ui.prompt("请输入章节标题:")
    if not title or not title.strip():
        ui.print_warning("章节标题不能为空.\n")
        return
    
    outline = ui.prompt("请输入章节大纲:")
    if outline is None:
        ui.print_warning("操作已取消.\n")
        return
    
    new_chapter = {"title": title.strip(), "outline": outline.strip()}
    chapters = get_data_manager().read_chapter_outline()
    chapters.append(new_chapter)
    
    if get_data_manager().write_chapter_outline(chapters):
        ui.print_success(f"章节 '{title}' 已添加.\n")
    else:
        ui.print_error("添加章节时出错.\n")


def view_chapter():
    """View chapter details."""
    chapters = get_data_manager().read_chapter_outline()
    if not chapters:
        ui.print_warning("\n当前没有章节信息。\n")
        return
    
    chapter_choices = [f"{ch.get('title', f'第{i+1}章')}" for i, ch in enumerate(chapters)]
    chapter_choices.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要查看的章节：", chapter_choices)
    
    if not choice_str or choice_str == str(len(chapter_choices)):
        return
    
    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(chapters):
            chapter = chapters[choice_index]
            ui.print_info(f"\n--- 章节详情：{chapter.get('title', '无标题')} ---")
            ui.print_info(f"大纲: {chapter.get('outline', '无大纲')}")
            ui.print_info("------------------------\n")
            ui.pause()
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def edit_chapter():
    """Edit chapter details."""
    chapters = get_data_manager().read_chapter_outline()
    if not chapters:
        ui.print_warning("\n当前没有章节信息。\n")
        return
        
    chapter_choices = [f"{ch.get('title', f'第{i+1}章')}" for i, ch in enumerate(chapters)]
    chapter_choices.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要修改的章节：", chapter_choices)
    
    if not choice_str or choice_str == str(len(chapter_choices)):
        return
        
    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(chapters):
            chapter_to_edit = chapters[choice_index]
            
            ui.print_info(f"当前标题: {chapter_to_edit.get('title', '')}")
            new_title = ui.prompt("请输入新标题 (留空不修改):", default=chapter_to_edit.get('title', ''))
            
            ui.print_info(f"当前大纲: {chapter_to_edit.get('outline', '')}")
            new_outline = ui.prompt("请输入新大纲 (留空不修改):", default=chapter_to_edit.get('outline', ''))

            if new_title is None or new_outline is None:
                ui.print_warning("操作已取消。\n")
                return

            # 更新章节信息
            chapters[choice_index]['title'] = new_title.strip()
            chapters[choice_index]['outline'] = new_outline.strip()
            
            if get_data_manager().write_chapter_outline(chapters):
                ui.print_success("章节已更新。\n")
            else:
                ui.print_error("更新章节时出错。\n")
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def delete_chapter():
    """Delete a chapter."""
    chapters = get_data_manager().read_chapter_outline()
    if not chapters:
        ui.print_warning("\n当前没有章节信息。\n")
        return

    chapter_choices = [f"{ch.get('title', f'第{i+1}章')}" for i, ch in enumerate(chapters)]
    chapter_choices.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要删除的章节：", chapter_choices)
    
    if not choice_str or choice_str == str(len(chapter_choices)):
        return

    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(chapters):
            chapter_to_delete = chapters[choice_index]
            
            if ui.confirm(f"确定要删除章节 '{chapter_to_delete.get('title', '')}' 吗?"):
                # 从列表中删除章节
                del chapters[choice_index]
                
                if get_data_manager().write_chapter_outline(chapters):
                    ui.print_success("章节已删除。\n")
                else:
                    ui.print_error("删除章节时出错。\n")
            else:
                ui.print_warning("操作已取消。\n")
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def handle_chapter_summary():
    """Handles chapter summary management with full CRUD operations."""
    ensure_meta_dir()
    
    # 检查前置条件
    chapter_outline_exists = get_data_manager().check_prerequisites_for_chapter_summary()
    
    if not chapter_outline_exists:
        ui.print_warning("\n请先完成步骤5: 编辑分章细纲\n")
        return
    
    # 读取分章细纲
    chapters = get_data_manager().read_chapter_outline()
    
    if not chapters:
        ui.print_warning("\n分章细纲为空，请先完成步骤5。\n")
        return
    
    while True:
        # 每次循环都重新读取数据
        summaries = get_data_manager().read_chapter_summaries()
        
        # 显示当前章节概要状态
        ui.print_info(f"\n--- 章节概要状态 (共{len(chapters)}章) ---")
        
        for i, chapter in enumerate(chapters, 1):
            chapter_key = f"chapter_{i}"
            title = chapter.get('title', f'第{i}章')
            status = "✓ 已完成" if chapter_key in summaries else "○ 未完成"
            ui.print_info(f"{i}. {title}: {status}")
        ui.print_info("------------------------\n")
        
        # 操作选项
        choices = [
            "生成所有章节概要",
            "生成单个章节概要",
            "查看章节概要",
            "修改章节概要",
            "删除章节概要",
            "返回主菜单"
        ]
        
        action = ui.display_menu("请选择您要进行的操作：", choices)
        
        if action is None or action == "6":
            break
        elif action == "1":
            # 生成所有章节概要
            generate_all_summaries(chapters)
        elif action == "2":
            # 生成单个章节概要
            generate_single_summary(chapters)
        elif action == "3":
            # 查看章节概要
            view_chapter_summary(chapters)
        elif action == "4":
            # 修改章节概要
            edit_chapter_summary(chapters)
        elif action == "5":
            # 删除章节概要
            delete_chapter_summary(chapters)


def generate_all_summaries(chapters):
    """Generate summaries for all chapters."""
    ui.print_info(f"准备为所有 {len(chapters)} 个章节生成概要...")
    
    # 提供生成模式选择
    mode_choice = ui.display_menu("请选择生成模式：", [
        "🚀 并发生成（推荐）- 同时生成多个章节，速度更快",
        "📝 顺序生成 - 逐个生成章节，更稳定",
        "🔙 返回上级菜单"
    ])
    
    if mode_choice is None or mode_choice == "3":
        return
    
    use_async = mode_choice == "1"
    
    confirm_msg = f"这将为所有 {len(chapters)} 个章节生成概要"
    if use_async:
        confirm_msg += "（并发模式，速度较快）"
    else:
        confirm_msg += "（顺序模式，较为稳定）"
    confirm_msg += "。确定继续吗？"
    
    confirm = ui.confirm(confirm_msg)
    if not confirm:
        print("操作已取消。\n")
        return
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成章节概要。")
    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）", default="")

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    if not llm_service.is_available():
        print("AI服务不可用，请检查配置。")
        return
    
    if use_async and not llm_service.is_async_available():
        print("异步AI服务不可用，自动切换到顺序模式。")
        use_async = False
    
    # 读取相关信息
    context_info = get_data_manager().get_context_info()
    
    if use_async:
        # 异步并发生成
        async def async_generate():
            progress = AsyncProgressManager()
            mode_desc = "智能生成" if use_refinement else "标准生成"
            progress.start(available_chapters, f"准备开始并发{mode_desc}小说正文...")
            
            try:
                callback = progress.create_callback()
                if use_refinement:
                    results, failed_chapters = await llm_service.generate_all_novels_with_refinement_async(
                        chapters, summaries, context_info, user_prompt, callback
                    )
                else:
                    results, failed_chapters = await llm_service.generate_all_novels_async(
                        chapters, summaries, context_info, user_prompt, callback
                    )
                
                # 保存结果
                if results:
                    if get_data_manager().write_novel_chapters(results):
                        total_words = sum(ch.get('word_count', 0) for ch in results.values())
                        success_msg = f"成功生成 {len(results)} 个章节正文，总计 {total_words} 字"
                        if use_refinement:
                            success_msg += " (已完成智能反思修正)"
                        progress.finish(success_msg)
                        
                        if failed_chapters:
                            print(f"失败的章节: {', '.join(map(str, failed_chapters))}")
                            print("您可以稍后单独重新生成失败的章节。")
                    else:
                        progress.finish("保存小说正文时出错")
                else:
                    progress.finish("所有章节正文生成均失败")
                    
            except Exception as e:
                progress.finish(f"生成过程中出现异常: {e}")
        
        # 运行异步生成
        asyncio.run(async_generate())
    else:
        # 同步顺序生成
        novel_chapters = {}
        failed_chapters = []
        
        processed = 0
        for i in range(1, len(chapters) + 1):
            chapter_key = f"chapter_{i}"
            if chapter_key not in summaries:
                continue
                
            processed += 1
            mode_desc = "智能生成" if use_refinement else "标准生成"
            ui.print_info(f"\n正在{mode_desc}第{i}章正文... ({processed}/{available_chapters})")
            
            if use_refinement:
                chapter_content = llm_service.generate_novel_chapter_with_refinement(
                    chapters[i-1], summaries[chapter_key], i, context_info, user_prompt
                )
            else:
                chapter_content = llm_service.generate_novel_chapter(
                    chapters[i-1], summaries[chapter_key], i, context_info, user_prompt
                )
            
            if chapter_content:
                novel_chapters[chapter_key] = {
                    "title": chapters[i-1].get('title', f'第{i}章'),
                    "content": chapter_content,
                    "word_count": len(chapter_content)
                }
                success_msg = f"✅ 第{i}章正文生成完成 ({len(chapter_content)}字)"
                if use_refinement:
                    success_msg += " (已完成智能反思修正)"
                print(success_msg)
            else:
                failed_chapters.append(i)
                ui.print_error(f"❌ 第{i}章正文生成失败")
        
        # 保存结果
        if novel_chapters:
            if get_data_manager().write_novel_chapters(novel_chapters):
                total_words = sum(ch.get('word_count', 0) for ch in novel_chapters.values())
                success_msg = f"\n✅ 成功生成 {len(novel_chapters)} 个章节正文，总计 {total_words} 字"
                if use_refinement:
                    success_msg += " (已完成智能反思修正)"
                ui.print_success(success_msg)
                
                if failed_chapters:
                    ui.print_warning(f"失败的章节: {', '.join(map(str, failed_chapters))}")
                    ui.print_info("您可以稍后单独重新生成失败的章节。")
            else:
                ui.print_error("❌ 保存小说正文时出错")
        else:
            ui.print_error("\n❌ 所有章节正文生成均失败")


def generate_single_summary(chapters):
    """Generate summary for a single chapter."""
    # 读取现有概要数据
    summaries = get_data_manager().read_chapter_summaries()
    
    # 打印章节列表供用户选择
    chapter_choices = []
    # 使用 enumerate 从 1 开始，方便用户选择
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        title = chapter.get('title', f'第{i}章')
        status = "已完成" if chapter_key in summaries else "未完成"
        chapter_choices.append(f"{title} ({status})")
    
    choice_str = ui.display_menu("请选择要生成概要的章节：", chapter_choices)
    
    if not choice_str:
        return
    
    try:
        chapter_index = int(choice_str) - 1
        
        # 检查选择是否有效
        if not (0 <= chapter_index < len(chapters)):
            ui.print_warning("无效的选择。\n")
            return
            
        chapter_to_generate = chapters[chapter_index]
        chapter_num = chapter_index + 1
        
        # 如果已存在概要，询问是否覆盖
        if chapter_key in summaries:
            overwrite = ui.confirm(f"第{chapter_num}章已有概要，是否覆盖？")
            if not overwrite:
                ui.print_warning("操作已取消。\n")
                return
        
        # 获取用户自定义提示词
        print("您可以输入额外的要求或指导来影响AI生成章节概要。")
        user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）", default="")

        if user_prompt is None:
            print("操作已取消。\n")
            return
        
        if not llm_service.is_available():
            print("AI服务不可用，请检查配置。")
            return
        
        # 读取相关信息
        context_info = get_data_manager().get_context_info()
        
        ui.print_info(f"\n为章节 '{chapter_to_generate.get('title')}' 生成概要...")
        summary = llm_service.generate_chapter_summary(chapter_to_generate, chapter_num, context_info, user_prompt)
        
        if summary:
            ui.print_info(f"\n--- 第{chapter_num}章概要 ---")
            ui.print_info(summary)
            ui.print_info("------------------------\n")
            
            # 提供操作选项
            action = ui.display_menu("请选择您要进行的操作：", [
                "接受并保存",
                "修改后保存", 
                "放弃此次生成"
            ])

            if action is None or action == "3":
                ui.print_warning("已放弃此次生成。\n")
                return
            elif action == "1":
                # 直接保存
                if get_data_manager().set_chapter_summary(chapter_num, chapter_to_generate.get('title', f'第{chapter_num}章'), summary):
                    ui.print_success(f"第{chapter_num}章概要已保存。\n")
                else:
                    ui.print_error("保存章节概要时出错。\n")
            elif action == "2":
                # 修改后保存
                edited_summary = ui.prompt("请修改章节概要:", default=summary)

                if edited_summary and edited_summary.strip():
                    if get_data_manager().set_chapter_summary(chapter_num, chapter_to_generate.get('title', f'第{chapter_num}章'), edited_summary):
                        ui.print_success(f"第{chapter_num}章概要已保存.\n")
                    else:
                        ui.print_error("保存章节概要时出错.\n")
                else:
                    ui.print_warning("操作已取消或内容为空，未保存.\n")
        else:
            ui.print_error(f"第{chapter_num}章概要生成失败。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")
        return


def view_chapter_summary(chapters):
    """View chapter summary details."""
    summaries = get_data_manager().read_chapter_summaries()
    if not summaries:
        ui.print_warning("\n当前没有章节概要信息。\n")
        return
        
    chapter_map = {i + 1: ch for i, ch in enumerate(chapters)}
    summary_keys_sorted = sorted([int(k.split('_')[1]) for k in summaries.keys()])
    available_chapters = [f"{chapter_map.get(key, {}).get('title', f'第{key}章')}" for key in summary_keys_sorted]

    if not available_chapters:
        ui.print_warning("\n没有找到任何可用的章节概要。\n")
        return
    
    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要查看的章节概要：", available_chapters)
    
    if not choice_str or choice_str == str(len(available_chapters)):
        return

    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(summary_keys_sorted):
            chapter_num = summary_keys_sorted[choice_index]
            summary = summaries.get(f"chapter_{chapter_num}", "没有找到概要。")
            ui.print_info(f"\n--- 第{chapter_num}章概要 ---")
            ui.print_info(summary)
            ui.print_info("------------------------\n")
            ui.pause()
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def edit_chapter_summary(chapters):
    """Edit a chapter summary."""
    summaries = get_data_manager().read_chapter_summaries()
    if not summaries:
        ui.print_warning("\n当前没有章节概要信息。\n")
        return

    chapter_map = {i + 1: ch for i, ch in enumerate(chapters)}
    summary_keys_sorted = sorted([int(k.split('_')[1]) for k in summaries.keys()])
    available_chapters = [f"{chapter_map.get(key, {}).get('title', f'第{key}章')}" for key in summary_keys_sorted]
    
    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要修改的章节概要：", available_chapters)
    
    if not choice_str or choice_str == str(len(available_chapters)):
        return

    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(summary_keys_sorted):
            chapter_num = summary_keys_sorted[choice_index]
            summary_key = f"chapter_{chapter_num}"
            current_summary = summaries.get(summary_key, "")

            ui.print_info(f"\n--- 当前概要：第{chapter_num}章 ---")
            ui.print_info(current_summary)
            ui.print_info("------------------------\n")
            
            new_summary = ui.prompt("请输入新的概要:", default=current_summary, multiline=True)

            if new_summary is not None and new_summary.strip() != current_summary:
                summaries[summary_key] = new_summary.strip()
                if get_data_manager().write_chapter_summaries(summaries):
                    ui.print_success("章节概要已更新。\n")
                else:
                    ui.print_error("更新章节概要时出错。\n")
            else:
                ui.print_warning("操作已取消或内容未更改。\n")
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def delete_chapter_summary(chapters):
    """Delete a chapter summary."""
    summaries = get_data_manager().read_chapter_summaries()
    if not summaries:
        ui.print_warning("\n当前没有章节概要信息。\n")
        return

    chapter_map = {i + 1: ch for i, ch in enumerate(chapters)}
    summary_keys_sorted = sorted([int(k.split('_')[1]) for k in summaries.keys()])
    available_chapters = [f"{chapter_map.get(key, {}).get('title', f'第{key}章')}" for key in summary_keys_sorted]

    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要删除的章节概要：", available_chapters)
    
    if not choice_str or choice_str == str(len(available_chapters)):
        return

    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(summary_keys_sorted):
            chapter_num = summary_keys_sorted[choice_index]
            summary_key = f"chapter_{chapter_num}"
            
            if ui.confirm(f"确定要删除第{chapter_num}章的概要吗？"):
                if summary_key in summaries:
                    del summaries[summary_key]
                    if get_data_manager().write_chapter_summaries(summaries):
                        ui.print_success("章节概要已删除。\n")
                    else:
                        ui.print_error("删除章节概要时出错。\n")
                else:
                    ui.print_warning("未找到该章节的概要。\n")
            else:
                ui.print_warning("操作已取消。\n")
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def handle_novel_generation():
    """Handles novel generation management."""
    ensure_meta_dir()
    
    # 检查前置条件
    chapter_summary_exists = get_data_manager().check_prerequisites_for_novel_generation()
    
    if not chapter_summary_exists:
        ui.print_warning("\n请先完成步骤6: 编辑章节概要\n")
        return
    
    # 读取章节概要
    summaries = get_data_manager().read_chapter_summaries()
    
    if not summaries:
        ui.print_warning("\n章节概要为空，请先完成步骤6。\n")
        return
    
    # 读取分章细纲以获取章节顺序
    chapters = get_data_manager().read_chapter_outline()
    
    while True:
        # 每次循环都重新读取数据
        novel_chapters = get_data_manager().read_novel_chapters()
        
        # 显示当前小说正文状态
        ui.print_info(f"\n--- 小说正文状态 (共{len(summaries)}章) ---")
        
        # 按章节顺序显示
        for i in range(1, len(chapters) + 1):
            chapter_key = f"chapter_{i}"
            if chapter_key in summaries:
                chapter_title = chapters[i-1].get('title', f'第{i}章')
                status = "✓ 已完成" if chapter_key in novel_chapters else "○ 未完成"
                word_count = len(novel_chapters.get(chapter_key, {}).get('content', ''))
                word_info = f" ({word_count}字)" if word_count > 0 else ""
                ui.print_info(f"{i}. {chapter_title}: {status}{word_info}")
        ui.print_info("------------------------\n")
        
        # 操作选项
        choices = [
            "生成所有章节正文",
            "生成单个章节正文",
            "查看章节正文",
            "修改章节正文",
            "删除章节正文",
            "分章节导出",
            "返回主菜单"
        ]
        
        action = ui.display_menu("请选择您要进行的操作：", choices)
        
        if action is None or action == "7":
            break
        elif action == "1":
            # 生成所有章节正文
            generate_all_novel_chapters(chapters, summaries)
        elif action == "2":
            # 生成单个章节正文
            generate_single_novel_chapter(chapters, summaries, novel_chapters)
        elif action == "3":
            # 查看章节正文
            view_novel_chapter(chapters, novel_chapters)
        elif action == "4":
            # 修改章节正文
            edit_novel_chapter(chapters, novel_chapters)
        elif action == "5":
            # 删除章节正文
            delete_novel_chapter(chapters, novel_chapters)
        elif action == "6":
            # 分章节导出
            handle_novel_export(chapters, novel_chapters)


def generate_all_novel_chapters(chapters, summaries):
    """Generate novel text for all chapters."""
    available_chapters = sum(1 for i in range(1, len(chapters) + 1) if f"chapter_{i}" in summaries)
    ui.print_info(f"准备为 {available_chapters} 个有概要的章节生成正文...")
    
    if available_chapters == 0:
        ui.print_warning("没有可用的章节概要，请先生成章节概要。")
        return
    
    # 询问是否启用反思修正功能
    from config import GENERATION_CONFIG
    use_refinement = GENERATION_CONFIG.get('enable_refinement', True)
    
    if use_refinement:
        refinement_choice = ui.display_menu("请选择生成模式：", [
            "🔄 智能生成（推荐）- 生成初稿后进行AI反思修正",
            "📝 标准生成 - 仅生成初稿，不进行修正",
            "🔙 返回上级菜单"
        ])
        
        if refinement_choice is None or refinement_choice == "3":
            return
        
        use_refinement = refinement_choice == "1"
    else:
        use_refinement = False
    
    # 提供并发/顺序模式选择
    mode_choice = ui.display_menu("请选择执行模式：", [
        "🚀 并发生成（推荐）- 同时生成多个章节，速度更快",
        "📝 顺序生成 - 逐个生成章节，更稳定",
        "🔙 返回上级菜单"
    ])
    
    if mode_choice is None or mode_choice == "3":
        return
    
    use_async = mode_choice == "1"
    
    confirm_msg = f"这将为 {available_chapters} 个章节生成正文"
    if use_refinement:
        confirm_msg += "（智能反思修正模式）"
    else:
        confirm_msg += "（标准模式）"
    if use_async:
        confirm_msg += "（并发执行）"
    else:
        confirm_msg += "（顺序执行）"
    confirm_msg += "，可能需要较长时间。确定继续吗？"
    
    confirm = ui.confirm(confirm_msg)
    if not confirm:
        print("操作已取消。\n")
        return
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成小说正文。")
    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）", default="")

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    if not llm_service.is_available():
        print("AI服务不可用，请检查配置。")
        return
    
    if use_async and not llm_service.is_async_available():
        print("异步AI服务不可用，自动切换到顺序模式。")
        use_async = False
    
    # 读取相关信息
    context_info = get_data_manager().get_context_info()
    
    if use_async:
        # 异步并发生成
        async def async_generate():
            progress = AsyncProgressManager()
            mode_desc = "智能生成" if use_refinement else "标准生成"
            progress.start(available_chapters, f"准备开始并发{mode_desc}小说正文...")
            
            try:
                callback = progress.create_callback()
                if use_refinement:
                    results, failed_chapters = await llm_service.generate_all_novels_with_refinement_async(
                        chapters, summaries, context_info, user_prompt, callback
                    )
                else:
                    results, failed_chapters = await llm_service.generate_all_novels_async(
                        chapters, summaries, context_info, user_prompt, callback
                    )
                
                # 保存结果
                if results:
                    if get_data_manager().write_novel_chapters(results):
                        total_words = sum(ch.get('word_count', 0) for ch in results.values())
                        success_msg = f"成功生成 {len(results)} 个章节正文，总计 {total_words} 字"
                        if use_refinement:
                            success_msg += " (已完成智能反思修正)"
                        progress.finish(success_msg)
                        
                        if failed_chapters:
                            print(f"失败的章节: {', '.join(map(str, failed_chapters))}")
                            print("您可以稍后单独重新生成失败的章节。")
                    else:
                        progress.finish("保存小说正文时出错")
                else:
                    progress.finish("所有章节正文生成均失败")
                    
            except Exception as e:
                progress.finish(f"生成过程中出现异常: {e}")
        
        # 运行异步生成
        asyncio.run(async_generate())
    else:
        # 同步顺序生成
        novel_chapters = {}
        failed_chapters = []
        
        processed = 0
        for i in range(1, len(chapters) + 1):
            chapter_key = f"chapter_{i}"
            if chapter_key not in summaries:
                continue
                
            processed += 1
            mode_desc = "智能生成" if use_refinement else "标准生成"
            ui.print_info(f"\n正在{mode_desc}第{i}章正文... ({processed}/{available_chapters})")
            
            if use_refinement:
                chapter_content = llm_service.generate_novel_chapter_with_refinement(
                    chapters[i-1], summaries[chapter_key], i, context_info, user_prompt
                )
            else:
                chapter_content = llm_service.generate_novel_chapter(
                    chapters[i-1], summaries[chapter_key], i, context_info, user_prompt
                )
            
            if chapter_content:
                novel_chapters[chapter_key] = {
                    "title": chapters[i-1].get('title', f'第{i}章'),
                    "content": chapter_content,
                    "word_count": len(chapter_content)
                }
                success_msg = f"✅ 第{i}章正文生成完成 ({len(chapter_content)}字)"
                if use_refinement:
                    success_msg += " (已完成智能反思修正)"
                print(success_msg)
            else:
                failed_chapters.append(i)
                ui.print_error(f"❌ 第{i}章正文生成失败")
        
        # 保存结果
        if novel_chapters:
            if get_data_manager().write_novel_chapters(novel_chapters):
                total_words = sum(ch.get('word_count', 0) for ch in novel_chapters.values())
                success_msg = f"\n✅ 成功生成 {len(novel_chapters)} 个章节正文，总计 {total_words} 字"
                if use_refinement:
                    success_msg += " (已完成智能反思修正)"
                ui.print_success(success_msg)
                
                if failed_chapters:
                    ui.print_warning(f"失败的章节: {', '.join(map(str, failed_chapters))}")
                    ui.print_info("您可以稍后单独重新生成失败的章节。")
            else:
                ui.print_error("❌ 保存小说正文时出错")
        else:
            ui.print_error("\n❌ 所有章节正文生成均失败")


def generate_single_novel_chapter(chapters, summaries, novel_data):
    """Generate novel text for a single chapter."""
    # 处理数据格式兼容性：如果传入的直接是章节字典，直接使用；否则从'chapters'键获取
    if isinstance(novel_data, dict) and 'chapters' in novel_data:
        novel_chapters = novel_data['chapters']
    else:
        novel_chapters = novel_data
    
    # 选择章节
    chapter_choices = []
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in summaries:
            title = chapters[i-1].get('title', f'第{i}章')
            status = "已完成" if chapter_key in novel_chapters else "未完成"
            word_count = novel_chapters.get(chapter_key, {}).get('word_count', 0)
            word_info = f" ({word_count}字)" if word_count > 0 else ""
            chapter_choices.append(f"{i}. {title} ({status}){word_info}")
    
    choice_str = ui.display_menu("请选择要生成正文的章节：", chapter_choices)
    
    if not choice_str:
        return
    
    try:
        chapter_num = int(choice_str)
        chapter_index = chapter_num - 1
        
        if not (0 <= chapter_index < len(chapters)):
            ui.print_warning("无效的选择。\n")
            return
            
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")
        return

    chapter = chapters[chapter_index]
    chapter_key = f"chapter_{chapter_num}"
    
    # 如果已存在正文，询问是否覆盖
    if chapter_key in novel_chapters:
        overwrite = ui.confirm(f"第{chapter_num}章已有正文，是否覆盖？")
        if not overwrite:
            ui.print_warning("操作已取消。\n")
            return
    
    # 询问是否启用反思修正功能
    from config import GENERATION_CONFIG
    use_refinement = GENERATION_CONFIG.get('enable_refinement', True)
    
    if use_refinement:
        refinement_choice = ui.display_menu("请选择生成模式：", [
            "🔄 智能生成（推荐）- 生成初稿后进行AI反思修正",
            "📝 标准生成 - 仅生成初稿，不进行修正",
            "🔙 返回上级菜单"
        ])
        
        if refinement_choice is None or refinement_choice == "3":
            return
        
        use_refinement = refinement_choice == "1"
    else:
        use_refinement = False
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成小说正文。")
    user_prompt = ui.prompt("请输入您的额外要求或指导（直接回车跳过）", default="")

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    if not llm_service.is_available():
        print("AI服务不可用，请检查配置。")
        return
    
    # 读取相关信息
    context_info = get_data_manager().get_context_info()
    
    if use_refinement:
        ui.print_info(f"\n正在为第{chapter_num}章执行智能生成流程...")
        ui.print_info("阶段1: 生成初稿...")
        chapter_content = llm_service.generate_novel_chapter_with_refinement(
            chapter, summaries[chapter_key], chapter_num, context_info, user_prompt
        )
    else:
        ui.print_info(f"\n正在生成第{chapter_num}章正文...")
        chapter_content = llm_service.generate_novel_chapter(
            chapter, summaries[chapter_key], chapter_num, context_info, user_prompt
        )
    
    if chapter_content:
        ui.print_info(f"\n--- 第{chapter_num}章正文预览 (前500字) ---")
        preview = chapter_content[:500] + "..." if len(chapter_content) > 500 else chapter_content
        ui.print_info(preview)
        ui.print_info(f"\n总字数: {len(chapter_content)} 字")
        if use_refinement:
            ui.print_info("✨ 已完成智能反思修正流程")
        ui.print_info("------------------------\n")
        
        # 提供操作选项
        action = ui.display_menu("请选择您要进行的操作：", [
            "接受并保存",
            "修改后保存", 
            "放弃此次生成"
        ])

        if action is None or action == "3":
            ui.print_warning("已放弃此次生成。\n")
            return
        elif action == "1":
            # 直接保存
            if get_data_manager().set_novel_chapter(chapter_num, chapter.get('title', f'第{chapter_num}章'), chapter_content):
                ui.print_success(f"第{chapter_num}章正文已保存 ({len(chapter_content)}字)。\n")
            else:
                ui.print_error("保存章节正文时出错。\n")
        elif action == "2":
            # 修改后保存
            edited_content = ui.prompt("请修改章节正文:", default=chapter_content)

            if edited_content and edited_content.strip():
                if get_data_manager().set_novel_chapter(chapter_num, chapter.get('title', f'第{chapter_num}章'), edited_content):
                    ui.print_success(f"第{chapter_num}章正文已保存 ({len(edited_content)}字)。\n")
                else:
                    ui.print_error("保存章节正文时出错。\n")
            else:
                ui.print_warning("操作已取消或内容为空，未保存。\n")
    else:
        ui.print_error(f"第{chapter_num}章正文生成失败。\n")



def view_novel_chapter(chapters, novel_data):
    """View novel chapter content."""
    # 处理数据格式兼容性：如果传入的直接是章节字典，直接使用；否则从'chapters'键获取
    if isinstance(novel_data, dict) and 'chapters' in novel_data:
        novel_chapters = novel_data['chapters']
    else:
        novel_chapters = novel_data
    
    if not novel_chapters:
        ui.print_warning("\n当前没有小说正文信息。\n")
        return

    chapter_map = {i + 1: ch for i, ch in enumerate(chapters)}
    novel_keys_sorted = sorted([int(k.split('_')[1]) for k in novel_chapters.keys()])
    available_chapters = [f"{chapter_map.get(key, {}).get('title', f'第{key}章')}" for key in novel_keys_sorted]

    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要查看的章节正文：", available_chapters)
    
    if not choice_str or choice_str == str(len(available_chapters)):
        return

    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(novel_keys_sorted):
            chapter_num = novel_keys_sorted[choice_index]
            chapter_key = f"chapter_{chapter_num}"
            novel_chapter_data = novel_chapters.get(chapter_key)
            
            if novel_chapter_data:
                ui.print_info(f"\n--- {novel_chapter_data.get('title', '无标题')} ---")
                ui.print_info(novel_chapter_data.get('content', '无内容'))
                ui.print_info("------------------------\n")
                ui.pause()
            else:
                ui.print_warning("未找到该章节的正文。\n")
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def edit_novel_chapter(chapters, novel_data):
    """Edit a novel chapter."""
    novel_chapters = novel_data
    if not novel_chapters:
        ui.print_warning("\n当前没有小说正文信息。\n")
        return

    chapter_map = {i + 1: ch for i, ch in enumerate(chapters)}
    novel_keys_sorted = sorted([int(k.split('_')[1]) for k in novel_chapters.keys()])
    available_chapters = [f"{chapter_map.get(key, {}).get('title', f'第{key}章')}" for key in novel_keys_sorted]

    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要修改的章节正文：", available_chapters)
    
    if not choice_str or choice_str == str(len(available_chapters)):
        return

    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(novel_keys_sorted):
            chapter_num = novel_keys_sorted[choice_index]
            chapter_key = f"chapter_{chapter_num}"
            novel_chapter_data = novel_chapters.get(chapter_key)

            if novel_chapter_data:
                current_content = novel_chapter_data.get('content', '')
                ui.print_info(f"\n--- 正在修改：{novel_chapter_data.get('title', '')} ---")
                
                edited_content = ui.prompt("请编辑章节正文:", default=current_content, multiline=True)
                
                if edited_content is not None and edited_content.strip() != current_content:
                    # 更新内容和字数
                    novel_chapters[chapter_key]['content'] = edited_content.strip()
                    novel_chapters[chapter_key]['word_count'] = len(re.findall(r'[\u4e00-\u9fff]+', edited_content.strip()))
                    
                    if get_data_manager().write_novel_chapters(novel_chapters):
                        ui.print_success("章节正文已更新。\n")
                    else:
                        ui.print_error("更新章节正文时出错。\n")
                else:
                    ui.print_warning("操作已取消或内容未更改。\n")
            else:
                ui.print_warning("未找到该章节的正文。\n")
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def delete_novel_chapter(chapters, novel_data):
    """Delete a novel chapter."""
    novel_chapters = novel_data
    if not novel_chapters:
        ui.print_warning("\n当前没有小说正文信息。\n")
        return

    chapter_map = {i + 1: ch for i, ch in enumerate(chapters)}
    novel_keys_sorted = sorted([int(k.split('_')[1]) for k in novel_chapters.keys()])
    available_chapters = [f"{chapter_map.get(key, {}).get('title', f'第{key}章')}" for key in novel_keys_sorted]

    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要删除的章节正文：", available_chapters)
    
    if not choice_str or choice_str == str(len(available_chapters)):
        return

    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(novel_keys_sorted):
            chapter_num = novel_keys_sorted[choice_index]
            chapter_key = f"chapter_{chapter_num}"
            
            if ui.confirm(f"确定要删除第{chapter_num}章的正文吗？"):
                if chapter_key in novel_chapters:
                    del novel_chapters[chapter_key]
                    if get_data_manager().write_novel_chapters(novel_chapters):
                        ui.print_success("章节正文已删除。\n")
                    else:
                        ui.print_error("删除章节正文时出错。\n")
                else:
                    ui.print_warning("未找到该章节的正文。\n")
            else:
                ui.print_warning("操作已取消。\n")
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def get_export_dir():
    """获取当前项目的导出目录路径"""
    try:
        from project_manager import project_manager
        from config import get_export_base_dir
        
        # 获取导出基础目录（可配置）
        export_base_dir = get_export_base_dir()
        
        # 获取当前活动项目名称
        active_project = project_manager.get_active_project()
        if active_project:
            # 多项目模式：使用 导出基础目录/项目名
            export_dir = export_base_dir / active_project
        else:
            # 单项目模式：使用 导出基础目录/Default
            export_dir = export_base_dir / "Default"
        
        # 确保导出目录存在
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir
        
    except Exception as e:
        ui.print_warning(f"⚠️ 获取导出目录时出错，使用当前目录: {e}")
        from pathlib import Path
        export_dir = Path.cwd() / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        return export_dir


def handle_novel_export(chapters, novel_data):
    """Handle novel export with multiple options."""
    # 处理数据格式：如果 novel_data 直接是章节字典，直接使用；否则从 'chapters' 键获取
    if isinstance(novel_data, dict) and 'chapters' in novel_data:
        novel_chapters = novel_data['chapters']
    else:
        novel_chapters = novel_data
    
    if not novel_chapters:
        print("\n当前没有小说正文可导出。\n")
        return
    
    while True:
        # 显示当前小说状态
        total_chapters = len([ch for ch in novel_chapters.keys() if ch.startswith('chapter_')])
        total_words = sum(ch.get('word_count', len(ch.get('content', ''))) for ch in novel_chapters.values())
        
        print(f"\n--- 小说导出管理 ---")
        print(f"可导出章节: {total_chapters} 章")
        print(f"总字数: {total_words} 字")
        
        # 获取当前小说名称
        current_novel_name = get_novel_name()
        print(f"当前小说名: {current_novel_name}")
        print("------------------------\n")
        
        # 导出选项
        choices = [
            "导出完整小说",
            "导出单个章节",
            "导出章节范围",
            "返回上级菜单"
        ]
        
        action = ui.display_menu("请选择导出操作：", choices)
        
        if action is None or action == "4":
            break
        elif action == "1":
            # 导出完整小说
            export_complete_novel(chapters, novel_chapters)
        elif action == "2":
            # 导出单个章节
            export_single_chapter(chapters, novel_chapters)
        elif action == "3":
            # 导出章节范围
            export_chapter_range(chapters, novel_chapters)


def export_single_chapter(chapters, novel_chapters):
    """Export a single chapter."""
    if not novel_chapters:
        ui.print_warning("\n当前没有可导出的章节。\n")
        return
    
    chapter_map = {i + 1: ch for i, ch in enumerate(chapters)}
    novel_keys_sorted = sorted([int(k.split('_')[1]) for k in novel_chapters.keys()])
    available_chapters = [f"{chapter_map.get(key, {}).get('title', f'第{key}章')}" for key in novel_keys_sorted]

    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要导出的章节：", available_chapters)
    
    if not choice_str or choice_str == str(len(available_chapters)):
        return

    try:
        choice_index = int(choice_str) - 1
        if 0 <= choice_index < len(novel_keys_sorted):
            chapter_num = novel_keys_sorted[choice_index]
            export_dir = get_export_dir()
            novel_chapter_data = novel_chapters.get(f"chapter_{chapter_num}", {})
            content = novel_chapter_data.get('content', '')
            title = novel_chapter_data.get('title', f'第{chapter_num}章')
            filename = f"{title}.txt"
            
            with open(os.path.join(export_dir, filename), 'w', encoding='utf-8') as f:
                f.write(content)
            
            ui.print_success(f"章节 '{title}' 已导出到: {os.path.join(export_dir, filename)}\n")
        else:
            ui.print_warning("无效的选择。\n")
    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")


def export_chapter_range(chapters, novel_chapters):
    """Export a range of chapters."""
    if not novel_chapters:
        ui.print_warning("\n当前没有可导出的章节。\n")
        return
        
    chapter_map = {int(k.split('_')[1]): v.get('title', f"第{k.split('_')[1]}章") for k, v in novel_chapters.items()}
    available_chapter_nums = sorted(chapter_map.keys())

    if not available_chapter_nums:
        ui.print_warning("\n没有找到有效的章节号可供选择。\n")
        return
    
    # 创建起始章节选择列表
    start_choices = [f"第{i}章" for i in available_chapter_nums]
    start_choices.append("返回上级菜单")
    
    start_choice_str = ui.display_menu("请选择起始章节：", start_choices)
    
    if not start_choice_str or start_choice_str == str(len(start_choices)):
        return
    
    start_chapter_index = int(start_choice_str) - 1
    start_chapter = available_chapter_nums[start_chapter_index]
    
    # 创建结束章节选择列表（只包含起始章节及之后的章节）
    end_choices = [f"第{i}章" for i in available_chapter_nums if i >= start_chapter]
    end_choices.append("返回上级菜单")
    
    end_choice_str = ui.display_menu("请选择结束章节：", end_choices)
    
    if not end_choice_str or end_choice_str == str(len(end_choices)):
        return
    
    end_chapter_index = int(end_choice_str) - 1
    # 需要从 end_choices 中获取正确的章节号
    end_chapter = [num for num in available_chapter_nums if num >= start_chapter][end_chapter_index]

    export_dir = get_export_dir()
    novel_name = get_novel_name()
    filename = f"{novel_name} (第{start_chapter}-{end_chapter}章).txt"
    filepath = os.path.join(export_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        for num in range(start_chapter, end_chapter + 1):
            if num in available_chapter_nums:
                chapter_data = novel_chapters.get(f"chapter_{num}", {})
                title = chapter_data.get('title', f"第{num}章")
                content = chapter_data.get('content', '')
                f.write(f"## {title}\n\n")
                f.write(content)
                f.write("\n\n\n")
    
    ui.print_success(f"章节 {start_chapter} 到 {end_chapter} 已合并导出到: {filepath}\n")


def export_complete_novel(chapters, novel_data):
    """Export the complete novel to a single text file."""
    novel_chapters = novel_data.get('chapters', {}) if isinstance(novel_data, dict) and 'chapters' in novel_data else novel_data
    if not novel_chapters:
        print("\n当前没有小说正文可导出。\n")
        return
    
    # 获取小说名
    novel_name = get_novel_name()
    
    # 按章节顺序整理内容，并收集章节信息
    complete_novel = []
    total_words = 0
    exported_chapters = []
    
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in novel_chapters:
            chapter_info = novel_chapters[chapter_key]
            complete_novel.append(f"\n\n{chapter_info['title']}\n")
            complete_novel.append("=" * 30 + "\n\n")
            complete_novel.append(chapter_info['content'])
            total_words += chapter_info.get('word_count', 0)
            exported_chapters.append(i)
    
    if not complete_novel:
        print("\n没有可导出的章节。\n")
        return
    
    # 生成章节范围描述
    if len(exported_chapters) == 1:
        chapter_range = f"第{exported_chapters[0]}章"
    elif len(exported_chapters) == len(chapters):
        chapter_range = "全本"
    else:
        chapter_range = f"第{min(exported_chapters)}-{max(exported_chapters)}章"
    
    # 生成文件名和路径
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{novel_name}_{chapter_range}_{timestamp}.txt"
    
    # 获取导出目录并生成完整文件路径
    export_dir = get_export_dir()
    file_path = export_dir / filename
    
    # 写入文件
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"{novel_name}\n")
            f.write("=" * 50 + "\n")
            f.write(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"导出范围: {chapter_range}\n")
            f.write(f"总字数: {total_words} 字\n")
            f.write(f"章节数: {len(novel_chapters)} 章\n")
            f.write("=" * 50 + "\n")
            f.writelines(complete_novel)
        
        print(f"\n✅ 小说已成功导出到文件: {file_path}")
        print(f"小说名: {novel_name}")
        print(f"导出范围: {chapter_range}")
        print(f"总字数: {total_words} 字")
        print(f"章节数: {len(novel_chapters)} 章")
        print(f"文件位置: {export_dir}\n")
    except Exception as e:
        print(f"\n导出失败: {e}\n")



def handle_system_settings():
    """Handle system settings including retry configuration."""
    while True:
        choice = ui.display_menu("请选择系统设置项:", [
            "查看重试设置",
            "修改重试设置",
            "重置重试设置",
            "查看导出路径设置",
            "修改导出路径设置",
            "重置导出路径设置",
            "返回主菜单"
        ])

        if choice is None or choice == "7":
            break
        elif choice == "1":
            show_retry_config()
        elif choice == "2":
            modify_retry_config()
        elif choice == "3":
            reset_retry_config()
        elif choice == "4":
            show_export_config()
        elif choice == "5":
            modify_export_config()
        elif choice == "6":
            reset_export_config()

def show_retry_config():
    """Display current retry configuration."""
    print("\n🔄 当前重试机制配置:")
    print("=" * 50)
    
    config_descriptions = {
        "max_retries": "最大重试次数",
        "base_delay": "基础延迟时间(秒)",
        "max_delay": "最大延迟时间(秒)",
        "exponential_backoff": "指数退避策略",
        "backoff_multiplier": "退避倍数",
        "jitter": "随机抖动",
        "enable_batch_retry": "批量重试功能",
        "retry_delay_jitter_range": "抖动范围(秒)"
    }
    
    for key, value in RETRY_CONFIG.items():
        if key in config_descriptions:
            desc = config_descriptions[key]
            if isinstance(value, bool):
                status = "启用" if value else "禁用"
                print(f"  {desc}: {status}")
            else:
                print(f"  {desc}: {value}")
    
    print("\n可重试的HTTP状态码:", ", ".join(map(str, RETRY_CONFIG["retryable_status_codes"])))
    print("可重试的异常关键词:", ", ".join(RETRY_CONFIG["retryable_exceptions"]))
    print("=" * 50)
    
    input("\n按回车键继续...")

def modify_retry_config():
    """Modify retry configuration settings."""
    print("\n⚙️  修改重试配置")
    print("=" * 30)
    
    # 选择要修改的配置项
    modifiable_configs = [
        ("重试次数", 'max_retries', RETRY_CONFIG, int, lambda x: x >= 0),
        ("重试延迟（秒）", 'delay', RETRY_CONFIG, float, lambda x: x > 0),
        ("重试退避因子", 'backoff', RETRY_CONFIG, float, lambda x: x >= 1),
        ("返回上级菜单", None, None, None, None)
    ]
    
    choices = [item[0] for item in modifiable_configs]
    
    choice_str = ui.display_menu("请选择要修改的配置项：", choices)
    
    if choice_str is None or int(choice_str) > len(modifiable_configs) -1:
        return
    
    try:
        choice_index = int(choice_str) - 1
        if not (0 <= choice_index < len(modifiable_configs) -1):
            ui.print_warning("无效的选择。\n")
            return

        desc, key, config_dict, type_converter, validator = modifiable_configs[choice_index]
        
        current_value = config_dict[key]
        new_value_str = ui.prompt(f"请输入新的 '{desc}' (当前值: {current_value}):", default=str(current_value))

        if new_value_str is None:
            ui.print_warning("操作已取消。\n")
            return
        
        try:
            new_value = type_converter(new_value_str)
            if validator(new_value):
                if update_retry_config({key: new_value}):
                    ui.print_success(f"{desc} 已更新为: {new_value}\n")
                else:
                    ui.print_error(f"更新配置 '{desc}' 失败。\n")
            else:
                ui.print_warning(f"输入的值 '{new_value}' 无效，请重新输入。\n")
        except ValueError:
            ui.print_warning("输入格式不正确，请重新输入。\n")

    except (ValueError, IndexError):
        ui.print_warning("无效的选择。\n")
        return

def reset_retry_config():
    """Reset retry configuration to default."""
    print("\n⚙️  重置重试配置")
    if ui.confirm("确定要将重试配置重置为默认值吗？"):
        from config import reset_retry_config as reset_config
        if reset_config():
            print("✅ 重试配置已重置为默认值\n")
        else:
            print("❌ 重置重试配置失败\n")
    else:
        print("❌ 操作已取消\n")
    input("\n按回车键继续...")

def show_export_config():
    """Display current export path configuration."""
    from config import get_export_path_info
    
    info = get_export_path_info()
    
    print("\n--- 导出路径配置 ---")
    print(f"📁 当前导出路径: {info['current_path']}")
    print(f"🏠 用户文档目录: {info['documents_dir']}")
    print(f"📋 默认导出路径: {info['default_path']}")
    
    if info['is_custom']:
        print(f"自定义路径: {info['custom_path']}")
    else:
        print("自定义路径: (未设置)")
    
    print("--------------------")
    input("\n按回车键继续...")

def modify_export_config():
    """Modify export path configuration."""
    from config import set_custom_export_path, clear_custom_export_path, get_export_path_info
    
    info = get_export_path_info()
    
    print("\n⚙️  修改导出路径配置")
    print(f"当前导出路径: {info['current_path']}")
    print("--------------------")
    
    choices = [
        "1. 设置自定义导出路径",
        "2. 恢复为默认导出路径",
        "3. 返回上级菜单"
    ]
    
    choice = ui.display_menu("请选择操作：", choices)
    
    if choice is None or choice == "3":
        return
    elif choice == "1":
        new_path = ui.prompt("请输入导出路径:", default=info['custom_path'] if info['is_custom'] else "")
        
        if new_path and new_path.strip():
            if set_custom_export_path(new_path.strip()):
                print("\n✅ 导出路径已更新。")
            else:
                print("\n❌ 更新导出路径失败。")
        else:
            print("\n操作已取消或路径为空，未更改。")
    elif choice == "2":
        if ui.confirm("确定要恢复为默认导出路径吗？"):
            if clear_custom_export_path():
                print("\n✅ 已恢复为默认导出路径。")
            else:
                print("\n❌ 恢复默认导出路径失败。")
        else:
            print("\n操作已取消。")
    
    input("\n按回车键继续...")

def reset_export_config():
    """Reset export path configuration to default."""
    from config import reset_export_path
    
    if ui.confirm("确定要重置导出路径设置为默认值吗？"):
        reset_export_path()
        print("\n✅ 导出路径配置已重置为默认值。")
        show_export_config()
    else:
        print("\n操作已取消。")
    
    input("\n按回车键继续...")


def get_novel_name():
    """获取当前小说名称"""
    data = get_data_manager().read_theme_one_line()
    if data and isinstance(data, dict) and "novel_name" in data:
        return data["novel_name"]
    return "未命名小说"

def set_novel_name():
    """设置小说名称"""
    current_name = get_novel_name()
    print(f"\n当前小说名: {current_name}")
    
    new_name = ui.prompt("请输入新的小说名称:", default=current_name if current_name != "未命名小说" else "")
    
    if new_name is None:
        print("操作已取消。\n")
        return
    
    new_name = new_name.strip()
    if not new_name:
        print("小说名称不能为空。\n")
        return
    
    # 读取现有的一句话主题数据
    current_data = get_data_manager().read_theme_one_line()
    current_theme = ""
    if isinstance(current_data, dict) and "theme" in current_data:
        current_theme = current_data["theme"]
    elif isinstance(current_data, str):
        current_theme = current_data
        
    # 更新小说名称，保持主题不变
    updated_data = {
        "novel_name": new_name,
        "theme": current_theme
    }
    
    if get_data_manager().write_theme_one_line(updated_data):
        print(f"✅ 小说名称已更新为: {new_name}\n")
    else:
        print("❌ 保存小说名称时出错。\n")


def handle_creative_workflow():
    """Handles the main creative workflow menu."""
    while True:
        console.clear()
        
        # 获取当前小说名称，用于第一项显示
        current_novel_name = get_novel_name()
        first_item = f"📝 确立一句话主题 - 《{current_novel_name}》" if current_novel_name != "未命名小说" else "📝 确立一句话主题 - 开始您的创作之旅"
        
        # 创作流程菜单
        menu_options = [
            first_item,
            "📖 扩展成一段话主题 - 将主题扩展为详细描述", 
            "🌍 世界设定 - 构建角色、场景和道具",
            "📋 编辑故事大纲 - 规划整体故事结构",
            "📚 编辑分章细纲 - 细化每章内容安排",
            "📄 编辑章节概要 - 生成章节摘要",
            "📜 生成小说正文 - AI辅助创作正文",
            "🔙 返回项目管理 - 切换或管理项目"
        ]
        choice = ui.display_menu("🎯 请选择您要进行的操作:", menu_options)

        if choice is None or choice == '8':
            break
        
        if choice == '1':
            handle_theme_one_line()
        elif choice == '2':
            handle_theme_paragraph()
        elif choice == '3':
            handle_world_setting()
        elif choice == '4':
            handle_story_outline()
        elif choice == '5':
            handle_chapter_outline()
        elif choice == '6':
            handle_chapter_summary()
        elif choice == '7':
            handle_novel_generation()


def main():
    """主函数，程序的入口点。
    处理项目迁移、主菜单显示和用户交互。
    """
    # # 检查并执行旧版本数据迁移
    # from migrate_to_multi_project import migrate_legacy_data
    # if not migrate_legacy_data():
    #     # 如果迁移失败或用户取消，则退出程序
    #     sys.exit(1)

    # 确保项目数据管理器已初始化
    # project_data_manager.initialize()

    while True:
        console.clear()
        
        # 显示当前活动项目
        active_project_name = project_data_manager.get_current_project_display_name()
        status_text = Text(f"当前项目: [bold green]{active_project_name}[/bold green]", justify="center")
        console.print(Panel(status_text, title="🚀 MetaNovel Engine", border_style="magenta"))
        
        # 主菜单
        menu_options = [
            "项目管理",
            "系统设置",
            "退出"
        ]
        choice = ui.display_menu("🚀 MetaNovel Engine - 主菜单", menu_options)

        if choice == '1':
            handle_project_management()
        elif choice == '2':
            handle_system_settings()
        elif choice == '3':
            console.clear()
            ui.print_goodbye()
            break


if __name__ == "__main__":
    main()