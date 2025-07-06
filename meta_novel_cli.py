import sys

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
from config import RETRY_CONFIG
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

        if action is None or action == "4":            ui.print_info("返回主菜单。\n")            return        elif action == "1":            ui.print_info("当前内容已在上方显示。\n")            return        elif action == "2":            edited_paragraph = ui.prompt("请修改您的段落主题:", default=existing_paragraph)            if edited_paragraph and edited_paragraph.strip() and edited_paragraph != existing_paragraph:                if get_data_manager().write_theme_paragraph(edited_paragraph):                    ui.print_success("段落主题已更新.\n")                else:                    ui.print_error("保存段落主题时出错.\n")            elif edited_paragraph is None:                ui.print_warning("操作已取消.\n")            else:                ui.print_warning("内容未更改.\n")            return        elif action == "3":            # 继续执行重新生成逻辑            ui.print_info("\n正在重新生成段落主题...")        else:            return

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

        if edited_paragraph and edited_paragraph.strip():            if get_data_manager().write_theme_paragraph(edited_paragraph):                ui.print_success("段落主题已保存.\n")            else:                ui.print_error("保存段落主题时出错.\n")        else:            ui.print_warning("操作已取消或内容为空，未保存.\n")


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
            
            if action is None or action == "4":                break            elif action == "1":                ui.print_info("\n--- 完整故事大纲 ---")                ui.print_info(current_outline)                ui.print_info("------------------------\n")                                # 等待用户确认后继续循环                ui.prompt("按任意键继续...")                continue            elif action == "2":                edit_outline()                continue            elif action == "3":                ui.print_info("\n正在重新生成故事大纲...")                generate_story_outline()                continue            else:                break
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

    if action is None or action == "3":        ui.print_warning("已放弃此次生成。\n")        return    elif action == "1":        # 直接保存        if get_data_manager().write_story_outline(generated_outline):            ui.print_success("故事大纲已保存。\n")        else:            ui.print_error("保存故事大纲时出错。\n")    elif action == "2":        # 修改后保存        edited_outline = ui.prompt("请修改故事大纲:", default=generated_outline)        if edited_outline and edited_outline.strip():            if get_data_manager().write_story_outline(edited_outline):                ui.print_success("故事大纲已保存.\n")            else:                ui.print_error("保存故事大纲时出错.\n")        else:            ui.print_warning("操作已取消或内容为空，未保存.\n")


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
        choices = [
            "生成分章细纲",
            "添加新章节",
            "查看章节详情",
            "修改章节信息", 
            "删除章节",
            "返回主菜单"
        ]
        
        if not chapters:
            # 如果没有章节，只显示生成和返回选项
            choices = [
                "生成分章细纲",
                "返回主菜单"
            ]
        
        action = ui.display_menu("请选择您要进行的操作：", choices)
        
        if action is None:
            break
        elif action == "1":
            # 生成分章细纲
            generate_chapter_outline()
        elif action == "2" and chapters:
            # 添加新章节
            add_chapter()
        elif action == "2" and not chapters:
            # 返回主菜单（当没有章节时）
            break
        elif action == "3":
            # 查看章节详情
            view_chapter()
        elif action == "4":
            # 修改章节信息
            edit_chapter()
        elif action == "5":
            # 删除章节
            delete_chapter()
        elif action == "6" or action == "2":
            # 返回主菜单
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
    if not user_prompt.strip():        confirm = ui.confirm("确定要继续生成分章细纲吗？")        if not confirm:            ui.print_warning("操作已取消。
")            return

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
                ui.print_info(f"
第{i}章: {chapter.get('title', '无标题')}")
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


def add_chapter():    """Add a new chapter."""    title = ui.prompt("请输入章节标题:")    if not title or not title.strip():        ui.print_warning("章节标题不能为空.\n")        return        outline = ui.prompt("请输入章节大纲:")    if outline is None:        ui.print_warning("操作已取消.\n")        return        new_chapter = {"title": title.strip(), "outline": outline.strip()}        chapters = get_data_manager().read_chapter_outline()    chapters.append(new_chapter)        if get_data_manager().write_chapter_outline(chapters):        ui.print_success(f"章节 '{title}' 已添加.\n")    else:        ui.print_error("添加章节时出错.\n")


def view_chapter():    """View chapter details."""    chapters = get_data_manager().read_chapter_outline()    if not chapters:        ui.print_warning("\n当前没有章节信息。\n")        return        chapter_choices = [f"{i+1}. {ch.get('title', f'第{i+1}章')}" for i, ch in enumerate(chapters)]    # 添加返回选项    chapter_choices.append("返回上级菜单")        choice_str = ui.display_menu("请选择要查看的章节：", chapter_choices)    choice = int(choice_str)        if choice and choice != len(chapter_choices):        chapter_index = choice - 1        chapter = chapters[chapter_index]        ui.print_info(f"\n--- {chapter.get('title', f'第{chapter_index+1}章')} ---")        ui.print_info(chapter.get('outline', '无大纲'))        ui.print_info("------------------------\n")


def edit_chapter():
    """Edit chapter information."""
    chapters = get_data_manager().read_chapter_outline()
    if not chapters:
        ui.print_warning("\n当前没有章节信息可编辑。\n")
        return
    
    chapter_choices = [f"{i+1}. {ch.get('title', f'第{i+1}章')}" for i, ch in enumerate(chapters)]
    # 添加返回选项
    chapter_choices.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要修改的章节：", chapter_choices)
    choice = int(choice_str)
    
    if not choice or choice == len(chapter_choices):
        return
    
    chapter_index = choice - 1
    chapter = chapters[chapter_index]
    
    ui.print_info(f"\n--- 当前章节信息 ---")
    ui.print_info(f"标题: {chapter.get('title', '无标题')}")
    ui.print_info(f"大纲: {chapter.get('outline', '无大纲')}")
    ui.print_info("------------------------\n")
    
    new_title = ui.prompt("章节标题:", default=chapter.get('title', ''))
    if new_title is None:
        ui.print_warning("操作已取消。\n")
        return
    
    new_outline = ui.prompt("章节大纲:", default=chapter.get('outline', ''))
    if new_outline is None:
        ui.print_warning("操作已取消。\n")
        return
    
    # 更新章节信息
    chapters[chapter_index] = {"title": new_title.strip(), "outline": new_outline.strip()}
    if get_data_manager().write_chapter_outline(chapters):
        ui.print_success("章节信息已更新。\n")
    else:
        ui.print_error("更新章节信息时出错。\n")


def delete_chapter():    """Delete a chapter."""    chapters = get_data_manager().read_chapter_outline()    if not chapters:        ui.print_warning("\n当前没有章节信息可删除.\n")        return        chapter_choices = [f"{i+1}. {ch.get('title', f'第{i+1}章')}" for i, ch in enumerate(chapters)]    # 添加返回选项    chapter_choices.append("返回上级菜单")        choice_str = ui.display_menu("请选择要删除的章节：", chapter_choices)    choice = int(choice)        if not choice or choice == len(chapter_choices):        return        chapter_index = choice - 1    chapter_title = chapters[chapter_index].get('title', f'第{chapter_index+1}章')        confirm = ui.confirm(f"确定要删除章节 '{chapter_title}' 吗？")    if confirm:        chapters.pop(chapter_index)        if get_data_manager().write_chapter_outline(chapters):            ui.print_success(f"章节 '{chapter_title}' 已删除.\n")        else:            ui.print_error("删除章节时出错.\n")    else:        ui.print_warning("操作已取消.\n")


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
            progress.start(len(chapters), "准备开始并发生成...")
            
            try:
                callback = progress.create_callback()
                results, failed_chapters = await llm_service.generate_all_summaries_async(
                    chapters, context_info, user_prompt, callback
                )
                
                # 保存结果
                if results:
                    if get_data_manager().write_chapter_summaries(results):
                        progress.finish(f"成功生成 {len(results)} 个章节概要")
                        
                        if failed_chapters:
                            print(f"失败的章节: {', '.join(map(str, failed_chapters))}")
                            print("您可以稍后单独重新生成失败的章节。")
                    else:
                        progress.finish("保存章节概要时出错")
                else:
                    progress.finish("所有章节概要生成均失败")
                    
            except Exception as e:
                progress.finish(f"生成过程中出现异常: {e}")
        
        # 运行异步生成
        asyncio.run(async_generate())
    else:
        # 同步顺序生成
        summaries = {}
        failed_chapters = []
        
        for i, chapter in enumerate(chapters, 1):
            chapter_key = f"chapter_{i}"
            print(f"
正在生成第{i}章概要... ({i}/{len(chapters)})")
            
            summary = llm_service.generate_chapter_summary(chapter, i, context_info, user_prompt)
            
            if summary:
                summaries[chapter_key] = {
                    "title": chapter.get('title', f'第{i}章'),
                    "summary": summary
                }
                ui.print_success(f"✅ 第{i}章概要生成完成")
            else:
                failed_chapters.append(i)
                ui.print_error(f"❌ 第{i}章概要生成失败")
        
        # 保存结果
        if summaries:
            if get_data_manager().write_chapter_summaries(summaries):
                ui.print_success(f"\n✅ 成功生成 {len(summaries)} 个章节概要")
                
                if failed_chapters:
                    ui.print_warning(f"失败的章节: {', '.join(map(str, failed_chapters))}")
                    ui.print_info("您可以稍后单独重新生成失败的章节。")
            else:
                ui.print_error("❌ 保存章节概要时出错")
        else:
            ui.print_error("\n❌ 所有章节概要生成均失败")


def generate_single_summary(chapters):
    """Generate summary for a single chapter."""
    # 读取现有概要数据
    summaries = get_data_manager().read_chapter_summaries()
    
    # 选择章节
    chapter_choices = []
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        title = chapter.get('title', f'第{i}章')
        status = "已完成" if chapter_key in summaries else "未完成"
        chapter_choices.append(f"{i}. {title} ({status})")
    
    choice_str = ui.display_menu("请选择要生成概要的章节：", chapter_choices)
    
    if not choice_str:
        return
    
    chapter_index = int(choice_str.split('.')[0]) - 1
    chapter_num = chapter_index + 1
    chapter = chapters[chapter_index]
    chapter_key = f"chapter_{chapter_num}"
    
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
    
    ui.print_info(f"
正在生成第{chapter_num}章概要...")
    summary = llm_service.generate_chapter_summary(chapter, chapter_num, context_info, user_prompt)
    
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
            if get_data_manager().set_chapter_summary(chapter_num, chapter.get('title', f'第{chapter_num}章'), summary):
                ui.print_success(f"第{chapter_num}章概要已保存。\n")
            else:
                ui.print_error("保存章节概要时出错。\n")
        elif action == "2":
            # 修改后保存
            edited_summary = ui.prompt("请修改章节概要:", default=summary)

            if edited_summary and edited_summary.strip():                if get_data_manager().set_chapter_summary(chapter_num, chapter.get('title', f'第{chapter_num}章'), edited_summary):                    ui.print_success(f"第{chapter_num}章概要已保存.\n")                else:                    ui.print_error("保存章节概要时出错.\n")            else:                ui.print_warning("操作已取消或内容为空，未保存.\n")
    else:
        ui.print_error(f"第{chapter_num}章概要生成失败。\n")





def view_chapter_summary(chapters):
    """View chapter summary details."""
    summaries = get_data_manager().read_chapter_summaries()
    if not summaries:
        ui.print_warning("\n当前没有章节概要。\n")
        return
    
    # 只显示有概要的章节
    available_chapters = []
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in summaries:
            title = chapter.get('title', f'第{i}章')
            available_chapters.append(f"{i}. {title}")
    
    if not available_chapters:
        ui.print_warning("\n当前没有章节概要。\n")
        return
    
    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要查看的章节概要：", available_chapters)
    
    if choice_str and (int(choice_str) -1) != len(available_chapters):
        chapter_num = int(choice_str.split('.')[0])
        chapter_key = f"chapter_{chapter_num}"
        summary_info = summaries[chapter_key]
        
        ui.print_info(f"
--- {summary_info['title']} ---")
        ui.print_info(summary_info['summary'])
        ui.print_info("------------------------\n")


def edit_chapter_summary(chapters):
    """Edit chapter summary."""
    summaries = get_data_manager().read_chapter_summaries()
    if not summaries:
        ui.print_warning("\n当前没有章节概要可编辑。\n")
        return
    
    # 只显示有概要的章节
    available_chapters = []
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in summaries:
            title = chapter.get('title', f'第{i}章')
            available_chapters.append(f"{i}. {title}")
    
    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要修改的章节概要：", available_chapters)
    
    if not choice_str or (int(choice_str)-1) == len(available_chapters):
        return
    
    chapter_num = int(choice_str.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    summary_info = summaries[chapter_key]
    
    ui.print_info(f"\n--- 当前概要：{summary_info['title']} ---")
    ui.print_info(summary_info['summary'])
    ui.print_info("------------------------\n")
    
    edited_summary = ui.prompt("请修改章节概要:", default=summary_info['summary'])
    
    if edited_summary and edited_summary.strip() and edited_summary != summary_info['summary']:
        if get_data_manager().set_chapter_summary(chapter_num, summary_info['title'], edited_summary):
            ui.print_success(f"第{chapter_num}章概要已更新。\n")
        else:
            ui.print_error("更新章节概要时出错。\n")
    elif edited_summary is None:
        ui.print_warning("操作已取消。\n")
    else:
        ui.print_warning("内容未更改。\n")


def delete_chapter_summary(chapters):
    """Delete chapter summary."""
    summaries = get_data_manager().read_chapter_summaries()
    if not summaries:
        ui.print_warning("\n当前没有章节概要可删除。\n")
        return
    
    # 只显示有概要的章节
    available_chapters = []
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in summaries:
            title = chapter.get('title', f'第{i}章')
            available_chapters.append(f"{i}. {title}")
    
    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要删除的章节概要：", available_chapters)
    
    if not choice_str or (int(choice_str)-1) == len(available_chapters):
        return
    
    chapter_num = int(choice_str.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    title = summaries[chapter_key]['title']
    
    confirm = ui.confirm(f"确定要删除第{chapter_num}章 '{title}' 的概要吗？")
    if confirm:
        if get_data_manager().delete_chapter_summary(chapter_num):
            ui.print_success(f"第{chapter_num}章概要已删除.\n")
        else:
            ui.print_error("删除章节概要时出错.\n")
    else:
        ui.print_warning("操作已取消.\n")


def handle_novel_generation():
    """Handles novel text generation with full management operations."""
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
            choices = [
            choices = [
            "导出完整小说",
            "导出单个章节",
            "导出章节范围",
            "返回上级菜单"
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
            ui.print_info(f"
正在{mode_desc}第{i}章正文... ({processed}/{available_chapters})")
            
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
    
    chapter_num = int(choice_str.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    chapter = chapters[chapter_num - 1]
    
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
        ui.print_info(f"
正在为第{chapter_num}章执行智能生成流程...")
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
        ui.print_warning("\n当前没有小说正文。\n")
        return
    
    # 只显示有正文的章节
    available_chapters = []
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in novel_chapters:
            title = chapters[i-1].get('title', f'第{i}章')
            word_count = novel_chapters[chapter_key].get('word_count', 0)
            available_chapters.append(f"{i}. {title} ({word_count}字)")
    
    if not available_chapters:
        ui.print_warning("\n当前没有小说正文。\n")
        return
    
    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要查看的章节正文：", available_chapters)
    
    if choice_str and (int(choice_str)-1) != len(available_chapters):
        chapter_num = int(choice_str.split('.')[0])
        chapter_key = f"chapter_{chapter_num}"
        chapter_info = novel_chapters[chapter_key]
        
        ui.print_info(f"\n--- {chapter_info['title']} ---")
        ui.print_info(f"字数: {chapter_info.get('word_count', 0)} 字\n")
        ui.print_info(chapter_info['content'])
        ui.print_info("------------------------\n")


def edit_novel_chapter(chapters, novel_data):
    """Edit novel chapter content."""
    # 处理数据格式兼容性：如果传入的直接是章节字典，直接使用；否则从'chapters'键获取
    if isinstance(novel_data, dict) and 'chapters' in novel_data:
        novel_chapters = novel_data['chapters']
    else:
        novel_chapters = novel_data
    
    if not novel_chapters:
        ui.print_warning("\n当前没有小说正文可编辑。\n")
        return
    
    # 只显示有正文的章节
    available_chapters = []
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in novel_chapters:
            title = chapters[i-1].get('title', f'第{i}章')
            word_count = novel_chapters[chapter_key].get('word_count', 0)
            available_chapters.append(f"{i}. {title} ({word_count}字)")
    
    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要修改的章节正文：", available_chapters)
    
    if not choice_str or (int(choice_str)-1) == len(available_chapters):
        return
    
    chapter_num = int(choice_str.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    chapter_info = novel_chapters[chapter_key]
    
    ui.print_info(f"\n--- 当前正文：{chapter_info['title']} ---")
    ui.print_info(f"字数: {chapter_info.get('word_count', 0)} 字")
    ui.print_info("------------------------\n")
    
    edited_content = ui.prompt("请修改章节正文:", default=chapter_info['content'])
    
    if edited_content and edited_content.strip() and edited_content != chapter_info['content']:
        if get_data_manager().set_novel_chapter(chapter_num, chapter_info['title'], edited_content):
            ui.print_success(f"第{chapter_num}章正文已更新 ({len(edited_content)}字)。\n")
        else:
            ui.print_error("更新章节正文时出错。\n")
    elif edited_content is None:
        ui.print_warning("操作已取消。\n")
    else:
        ui.print_warning("内容未更改。\n")


def delete_novel_chapter(chapters, novel_data):
    """Delete novel chapter content."""
    # 处理数据格式兼容性：如果传入的直接是章节字典，直接使用；否则从'chapters'键获取
    if isinstance(novel_data, dict) and 'chapters' in novel_data:
        novel_chapters = novel_data['chapters']
    else:
        novel_chapters = novel_data
    
    if not novel_chapters:
        ui.print_warning("\n当前没有小说正文可删除。\n")
        return
    
    # 只显示有正文的章节
    available_chapters = []
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in novel_chapters:
            title = chapters[i-1].get('title', f'第{i}章')
            word_count = novel_chapters[chapter_key].get('word_count', 0)
            available_chapters.append(f"{i}. {title} ({word_count}字)")
    
    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要删除的章节正文：", available_chapters)
    
    if not choice_str or (int(choice_str)-1) == len(available_chapters):
        return
    
    chapter_num = int(choice_str.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    title = novel_chapters[chapter_key]['title']
    
    confirm = ui.confirm(f"确定要删除第{chapter_num}章 '{title}' 的正文吗？")
    if confirm:
        if get_data_manager().delete_novel_chapter(chapter_num):
            ui.print_success(f"第{chapter_num}章正文已删除.\n")
        else:
            ui.print_error("删除章节正文时出错.\n")
    else:
        ui.print_warning("操作已取消.\n")


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
    # 获取可导出的章节
    available_chapters = []
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in novel_chapters:
            chapter_title = chapters[i-1].get('title', f'第{i}章')
            word_count = novel_chapters[chapter_key].get('word_count', len(novel_chapters[chapter_key].get('content', '')))
            available_chapters.append(f"{i}. {chapter_title} ({word_count}字)")
    
    if not available_chapters:
        print("\n没有可导出的章节。\n")
        return
    
    # 添加返回选项
    available_chapters.append("返回上级菜单")
    
    choice_str = ui.display_menu("请选择要导出的章节：", available_chapters)
    
    if not choice_str or (int(choice_str)-1) == len(available_chapters):
        return
    
    chapter_num = int(choice_str.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    chapter_info = novel_chapters[chapter_key]
    
    # 生成文件名和路径
    novel_name = get_novel_name()
    chapter_title = chapters[chapter_num-1].get('title', f'第{chapter_num}章')
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{novel_name}_{chapter_title}_{timestamp}.txt"
    
    # 获取导出目录并生成完整文件路径
    export_dir = get_export_dir()
    file_path = export_dir / filename
    
    # 写入文件
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"{novel_name}\n")
            f.write("=" * 50 + "\n")
            f.write(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"导出章节: {chapter_title}\n")
            f.write(f"字数: {chapter_info.get('word_count', len(chapter_info.get('content', '')))} 字\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"{chapter_info['title']}\n")
            f.write("=" * 30 + "\n\n")
            f.write(chapter_info['content'])
        
        print(f"\n✅ 章节已成功导出到文件: {file_path}")
        print(f"小说名: {novel_name}")
        print(f"章节: {chapter_title}")
        print(f"字数: {chapter_info.get('word_count', len(chapter_info.get('content', '')))} 字")
        print(f"文件位置: {export_dir}\n")
    except Exception as e:
        print(f"\n❌ 导出失败: {e}\n")


def export_chapter_range(chapters, novel_chapters):
    """Export a range of chapters."""
    # 获取可导出的章节号
    available_chapter_nums = []
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in novel_chapters:
            available_chapter_nums.append(i)
    
    if not available_chapter_nums:
        print("\n没有可导出的章节。\n")
        return
    
    print(f"\n可导出的章节: {', '.join(map(str, available_chapter_nums))}")
    
    # 创建起始章节选择列表
    start_choices = [f"{i}. 第{i}章" for i in available_chapter_nums]
    start_choices.append("返回上级菜单")
    
    start_choice_str = ui.display_menu("请选择起始章节：", start_choices)
    
    if not start_choice_str or (int(start_choice_str.split('.')[0]) - 1) == len(start_choices) -1:
        return
    
    start_chapter = int(start_choice_str.split('.')[0])
    
    # 创建结束章节选择列表（只包含起始章节及之后的章节）
    end_choices = [f"{i}. 第{i}章" for i in available_chapter_nums if i >= start_chapter]
    end_choices.append("返回上级菜单")
    
    end_choice_str = ui.display_menu("请选择结束章节：", end_choices)
    
    if not end_choice_str or (int(end_choice_str.split('.')[0]) - 1) == len(end_choices) -1:
        return
    
    end_chapter = int(end_choice_str.split('.')[0])
    
    # 导出选定范围的章节
    export_chapters = [i for i in available_chapter_nums if start_chapter <= i <= end_chapter]
    
    if not export_chapters:
        print("\n没有可导出的章节。\n")
        return
    
    # 生成文件名和路径
    novel_name = get_novel_name()
    if start_chapter == end_chapter:
        chapter_range = f"第{start_chapter}章"
    else:
        chapter_range = f"第{start_chapter}-{end_chapter}章"
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{novel_name}_{chapter_range}_{timestamp}.txt"
    
    # 获取导出目录并生成完整文件路径
    export_dir = get_export_dir()
    file_path = export_dir / filename
    
    # 写入文件
    try:
        total_words = 0
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(f"{novel_name}\n")
            f.write("=" * 50 + "\n")
            f.write(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"导出范围: {chapter_range}\n")
            f.write(f"章节数: {len(export_chapters)} 章\n")
            f.write("=" * 50 + "\n")
            
            for chapter_num in export_chapters:
                chapter_key = f"chapter_{chapter_num}"
                chapter_info = novel_chapters[chapter_key]
                
                f.write(f"\n\n{chapter_info['title']}\n")
                f.write("=" * 30 + "\n\n")
                f.write(chapter_info['content'])
                
                total_words += chapter_info.get('word_count', len(chapter_info.get('content', '')))
        
        print(f"\n✅ 章节范围已成功导出到文件: {file_path}")
        print(f"小说名: {novel_name}")
        print(f"导出范围: {chapter_range}")
        print(f"章节数: {len(export_chapters)} 章")
        print(f"总字数: {total_words} 字")
        print(f"文件位置: {export_dir}\n")
    except Exception as e:
        print(f"\n❌ 导出失败: {e}\n")


def export_complete_novel(chapters, novel_data):
    """Export complete novel to a text file."""
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
        ("最大重试次数", "max_retries", "int", 1, 10),
        ("基础延迟时间(秒)", "base_delay", "float", 0.1, 10.0),
        ("最大延迟时间(秒)", "max_delay", "float", 1.0, 120.0),
        ("指数退避策略", "exponential_backoff", "bool", None, None),
        ("退避倍数", "backoff_multiplier", "float", 1.1, 5.0),
        ("随机抖动", "jitter", "bool", None, None),
        ("批量重试功能", "enable_batch_retry", "bool", None, None),
        ("抖动范围(秒)", "retry_delay_jitter_range", "float", 0.01, 1.0),
        ("返回上级菜单", None, None, None, None)
    ]
    
    choices = [f"{i+1}. {desc}" for i, (desc, _, _, _, _) in enumerate(modifiable_configs)]
    
    choice_str = ui.display_menu("请选择要修改的配置项：", choices)
    
    if choice_str is None or int(choice_str) == len(modifiable_configs) + 1: # +1 for "返回上级菜单"
        return
    
    choice = int(choice_str)
    desc, key, type, min_val, max_val = modifiable_configs[choice - 1]
    current_value = RETRY_CONFIG.get(key)
    
    if type == "bool":
        new_value = ui.confirm(f"启用 {desc}")
    else:
        prompt = f"请输入新的 {desc} (范围: {min_val}-{max_val}):"
        while True:
            input_value = ui.prompt(prompt, default=str(current_value))
            try:
                if type == "int":
                    new_value = int(input_value)
                else:
                    new_value = float(input_value)
                
                if min_val is not None and new_value < min_val:
                    print(f"输入值不能小于 {min_val}")
                    continue
                if max_val is not None and new_value > max_val:
                    print(f"输入值不能大于 {max_val}")
                    continue
                break
            except (ValueError, TypeError):
                print("无效输入，请输入正确的数值。")
    
    # 更新配置
    from config import update_retry_config
    if update_retry_config({key: new_value}):
        print(f"✅ 配置 '{desc}' 已更新为: {new_value}")
    else:
        print(f"❌ 更新配置失败")
    
    input("\n按回车键继续...")

def reset_retry_config():    """Reset retry configuration to defaults."""    print("\n⚙️  重置重试配置")        if ui.confirm("确定要将重试配置重置为默认值吗？"):        from config import reset_retry_config as reset_config        if reset_config():            print("✅ 重试配置已重置为默认值\n")        else:            print("❌ 重置重试配置失败\n")    else:        print("❌ 操作已取消\n")    input("\n按回车键继续...")


def show_export_config():
    """Display current export path configuration."""
    from config import get_export_path_info
    
    info = get_export_path_info()
    
    print("\n--- 导出路径配置 ---")
    print(f"📁 当前导出路径: {info['current_path']}")
    print(f"🏠 用户文档目录: {info['documents_dir']}")
    print(f"📋 默认导出路径: {info['default_path']}")
    
    if info['is_custom']:
        print(f"⚙️ 自定义路径: {info['custom_path']} (已启用)")
        print("📌 当前使用自定义导出路径")
    else:
        print("📌 当前使用默认导出路径")
    
    print("\n💡 说明:")
    print("- 默认路径：保存在用户文档目录的 MetaNovel 文件夹中")
    print("- 自定义路径：可以是绝对路径或相对于文档目录的路径")
    print("- 项目文件：每个项目会在导出目录下创建独立的文件夹")
    print("=" * 50)
    
    input("\n按回车键继续...")


def modify_export_config():
    """Modify export path configuration."""
    from config import set_custom_export_path, get_export_path_info
    
    info = get_export_path_info()
    
    print("\n--- 修改导出路径设置 ---")
    print(f"📁 当前导出路径: {info['current_path']}")
    print(f"🏠 用户文档目录: {info['documents_dir']}")
    
    choices = [
        "1. 设置自定义导出路径",
        "2. 使用默认导出路径",
        "3. 返回上级菜单"
    ]
    
    choice = ui.display_menu("请选择操作：", choices)
    
    if choice is None or choice.startswith("3."):
        return
    elif choice.startswith("1."):
        # 设置自定义导出路径
        print("\n📝 设置自定义导出路径")
        print("💡 提示:")
        print("- 可以输入绝对路径，如: /home/user/MyExports")
        print("- 也可以输入相对路径，如: MyNovelExports (相对于文档目录)")
        print("- Windows示例: D:\\MyExports 或 MyNovelExports")
        print("- 程序会自动创建目录并验证权限")
        
        new_path = questionary.text(
            "请输入导出路径:",
            default=info['custom_path'] if info['is_custom'] else ""
        new_path = ui.prompt("请输入新的导出路径:")
        
        if new_path and new_path.strip():
            if set_custom_export_path(new_path.strip()):
                print(f"\n✅ 导出路径已设置为: {new_path}")
                # 显示更新后的配置
                show_export_config()
            else:
                print(f"\n❌ 设置导出路径失败，请检查路径是否有效且有写入权限")
        else:
            print("\n❌ 路径不能为空")
            
    elif choice.startswith("2."):
        # 使用默认导出路径
        from config import reset_export_path
        reset_export_path()
        print(f"\n✅ 已切换到默认导出路径: {info['default_path']}")
        show_export_config()


def reset_export_config():
    """Reset export path configuration to default."""
    from config import reset_export_path
    
    if ui.confirm("确定要重置导出路径设置为默认值吗？"):
        reset_export_path()
        print("\n✅ 导出路径配置已重置为默认值。")
        show_export_config()
    else:
        print("\n❌ 操作已取消。")


def get_novel_name():
    """获取当前小说名称"""
    try:
        # 优先使用项目显示名称
        project_name = project_data_manager.get_current_project_display_name()
        
        # 如果项目名称不是默认值，返回项目名称
        if project_name != "未命名小说":
            return project_name
        
        # 否则尝试从主题数据中获取
        theme_data = get_data_manager().read_theme_one_line()
        if isinstance(theme_data, dict):
            return theme_data.get("novel_name", "未命名小说")
        elif isinstance(theme_data, str) and theme_data.strip():
            # 尝试从主题文本中提取小说名
            lines = theme_data.strip().split('\n')
            first_line = lines[0] if lines else theme_data
            if '《' in first_line and '》' in first_line:
                return first_line[first_line.find('《')+1:first_line.find('》')]
            else:
                return "未命名小说"
        else:
            return "未命名小说"
    except:
        return "未命名小说"


def set_novel_name():
    """设置小说名称"""
    current_name = get_novel_name()
    print(f"\n当前小说名: {current_name}")
    
        new_name = ui.prompt("请输入新的小说名称:", default=current_name if current_name != "未命名小说" else "")
    
    if new_name is None:
        print("操作已取消。\n")
        return False
    
    new_name = new_name.strip()
    if not new_name:
        print("小说名称不能为空。\n")
        return False
    
    if new_name == current_name:
        print("名称未更改。\n")
        return True
    
    # 保存小说名称到主题文件
    try:
        # 读取现有主题数据
        theme_data = get_data_manager().read_theme_one_line()
        
        if isinstance(theme_data, str):
            # 如果是字符串，转换为字典格式
            new_theme_data = {
                "novel_name": new_name,
                "theme": theme_data
            }
        elif isinstance(theme_data, dict):
            # 如果已经是字典，更新小说名
            new_theme_data = theme_data.copy()
            new_theme_data["novel_name"] = new_name
        else:
            # 如果没有主题数据，创建新的
            new_theme_data = {
                "novel_name": new_name,
                "theme": ""
            }
        
        # 保存更新后的数据
        if get_data_manager().write_theme_one_line(new_theme_data):
            print(f"✅ 小说名称已设置为: {new_name}\n")
            return True
        else:
            print("❌ 设置小说名称失败\n")
            return False
    except Exception as e:
        print(f"❌ 设置小说名称失败: {e}\n")
        return False


def show_project_status():
    """显示项目完成状态"""
    # 收集详细状态信息
    status_details = {}
    
    # 1. 一句话主题
    theme_one_line = get_data_manager().read_theme_one_line()
    if theme_one_line:
        # 获取小说名和主题内容
        novel_name = get_novel_name()
        
        if isinstance(theme_one_line, dict):
            theme_content = theme_one_line.get('theme', '')
        elif isinstance(theme_one_line, str):
            theme_content = theme_one_line
        else:
            theme_content = ''
        
        status_details["theme_one_line"] = {
            "completed": True,
            "details": f"小说：《{novel_name}》"
        }
    else:
        status_details["theme_one_line"] = {
            "completed": False,
            "details": "尚未设置"
        }
    
    # 2. 段落主题
    theme_paragraph = get_data_manager().read_theme_paragraph()
    if theme_paragraph and theme_paragraph.strip():
        word_count = len(theme_paragraph)
        status_details["theme_paragraph"] = {
            "completed": True,
            "details": f"{word_count}字"
        }
    else:
        status_details["theme_paragraph"] = {
            "completed": False,
            "details": "尚未生成"
        }
    
    # 3. 世界设定
    characters = get_data_manager().read_characters()
    locations = get_data_manager().read_locations() 
    items = get_data_manager().read_items()
    
    char_count = len(characters) if characters else 0
    loc_count = len(locations) if locations else 0
    item_count = len(items) if items else 0
    
    if char_count > 0 or loc_count > 0 or item_count > 0:
        details_parts = []
        if char_count > 0:
            # 获取主要角色名（前3个）
            main_chars = list(characters.keys())[:3]
            char_names = "、".join(main_chars)
            if len(characters) > 3:
                char_names += "等"
            details_parts.append(f"角色{char_count}个({char_names})")
        if loc_count > 0:
            details_parts.append(f"场景{loc_count}个")
        if item_count > 0:
            details_parts.append(f"道具{item_count}个")
        
        status_details["world_settings"] = {
            "completed": True,
            "details": "、".join(details_parts)
        }
    else:
        status_details["world_settings"] = {
            "completed": False,
            "details": "尚未创建"
        }
    
    # 4. 故事大纲
    story_outline = get_data_manager().read_story_outline()
    if story_outline and story_outline.strip():
        word_count = len(story_outline)
        status_details["story_outline"] = {
            "completed": True,
            "details": f"{word_count}字"
        }
    else:
        status_details["story_outline"] = {
            "completed": False,
            "details": "尚未编写"
        }
    
    # 5. 分章细纲
    chapters = get_data_manager().read_chapter_outline()
    if chapters and len(chapters) > 0:
        chapter_count = len(chapters)
        total_outline_words = sum(len(ch.get('outline', '')) for ch in chapters)
        avg_words = total_outline_words // chapter_count if chapter_count > 0 else 0
        
        status_details["chapter_outline"] = {
            "completed": True,
            "details": f"{chapter_count}章，平均{avg_words}字/章"
        }
    else:
        status_details["chapter_outline"] = {
            "completed": False,
            "details": "尚未规划"
        }
    
    # 6. 章节概要
    summaries = get_data_manager().read_chapter_summaries()
    if summaries and len(summaries) > 0:
        total_chapters = len(chapters) if chapters else 0
        completed_summaries = len(summaries)
        
        if total_chapters > 0:
            completion_rate = int((completed_summaries / total_chapters) * 100)
            total_summary_words = sum(len(s.get('summary', '')) for s in summaries.values())
            avg_words = total_summary_words // completed_summaries if completed_summaries > 0 else 0
            
            status_details["chapter_summaries"] = {
                "completed": completion_rate == 100,
                "details": f"完成度{completion_rate}%，平均{avg_words}字/章"
            }
        else:
            status_details["chapter_summaries"] = {
                "completed": False,
                "details": "需先完成分章细纲"
            }
    else:
        status_details["chapter_summaries"] = {
            "completed": False,
            "details": "尚未生成"
        }
    
    # 7. 小说正文
    novel_chapters = get_data_manager().read_novel_chapters()
    if novel_chapters and len(novel_chapters) > 0:
        total_chapters = len(chapters) if chapters else 0
        completed_novels = len(novel_chapters)
        
        if total_chapters > 0:
            completion_rate = int((completed_novels / total_chapters) * 100)
            total_words = sum(ch.get('word_count', len(ch.get('content', ''))) for ch in novel_chapters.values())
            avg_words = total_words // completed_novels if completed_novels > 0 else 0
            
            status_details["novel_chapters"] = {
                "completed": completion_rate == 100,
                "details": f"完成度{completion_rate}%，总计{total_words}字，平均{avg_words}字/章"
            }
        else:
            status_details["novel_chapters"] = {
                "completed": False,
                "details": "需先完成前置步骤"
            }
    else:
        status_details["novel_chapters"] = {
            "completed": False,
            "details": "尚未开始"
        }
    
    ui.print_project_status(status_details)



def handle_creative_workflow():
    """处理创作流程菜单（7步创作流程）"""
    while True:
        # 清屏并显示界面
        console.clear()
        
        # 显示项目状态
        show_project_status()
        console.print()  # 空行
        
        # 获取当前小说名称，用于第一项显示
        current_novel_name = get_novel_name()
        first_item = f"📝 确立一句话主题 - 《{current_novel_name}》" if current_novel_name != "未命名小说" else "📝 确立一句话主题 - 开始您的创作之旅"
        
        # 创作流程菜单
        menu_options = [
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
    """
    Main function to display the main menu.
    """
    # 显示欢迎信息（只在首次启动时显示）
    first_run = True
    
    while True:
        # 清屏并显示界面
        console.clear()
        
        if first_run:
            ui.print_welcome()
            console.print()  # 空行
            first_run = False
        
        # 显示当前活动项目信息
        current_project = project_data_manager.get_current_project_display_name()
        if current_project != "未命名小说":
            status_text = f"[green]当前项目: {current_project}[/green]"
            console.print(Panel(status_text, title="📁 项目状态", border_style="blue"))
            console.print()
        
        # 主菜单
        menu_options = [
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
