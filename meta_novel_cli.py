import sys

# --- 导入配置模块并设置代理 ---
from config import setup_proxy
setup_proxy()  # 必须在导入网络库之前设置代理
# ----------------------------------------------------

import questionary
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
    print(f"\n--- 当前状态 ---")
    print(f"小说名称: {current_novel_name}")
    if current_theme:
        print(f"一句话主题: {current_theme}")
    else:
        print("一句话主题: (尚未设置)")
    print("------------------\n")
    
    # 提供操作选项
    action = questionary.select(
        "请选择您要进行的操作：",
        choices=[
            "1. 设置小说名称",
            "2. 设置一句话主题",
            "3. 同时设置名称和主题",
            "4. 返回主菜单"
        ],
        use_indicator=True
    ).ask()
    
    if action is None or action.startswith("4."):
        print("返回主菜单。\n")
        return
    elif action.startswith("1."):
        # 只设置小说名称
        set_novel_name()
    elif action.startswith("2."):
        # 只设置一句话主题
        new_theme = questionary.text(
            "请输入您的一句话主题:",
            default=current_theme
        ).ask()
        
        if new_theme is not None and new_theme.strip():
            # 保存主题，保持现有的小说名称
            new_data = {
                "novel_name": current_novel_name,
                "theme": new_theme.strip()
            }
            if get_data_manager().write_theme_one_line(new_data):
                print(f"✅ 主题已更新为: {new_theme}\n")
            else:
                print("❌ 保存主题时出错。\n")
        elif new_theme is None:
            print("操作已取消。\n")
        else:
            print("主题不能为空。\n")
    elif action.startswith("3."):
        # 同时设置名称和主题
        new_novel_name = questionary.text(
            "请输入小说名称:",
            default=current_novel_name if current_novel_name != "未命名小说" else ""
        ).ask()
        
        if new_novel_name is None:
            print("操作已取消。\n")
            return
        
        new_novel_name = new_novel_name.strip()
        if not new_novel_name:
            print("小说名称不能为空。\n")
            return
        
        new_theme = questionary.text(
            "请输入您的一句话主题:",
            default=current_theme
        ).ask()
        
        if new_theme is None:
            print("操作已取消。\n")
            return
        
        new_theme = new_theme.strip()
        if not new_theme:
            print("主题不能为空。\n")
            return
        
        # 保存名称和主题
        new_data = {
            "novel_name": new_novel_name,
            "theme": new_theme
        }
        if get_data_manager().write_theme_one_line(new_data):
            print(f"✅ 小说名称已设置为: {new_novel_name}")
            print(f"✅ 主题已设置为: {new_theme}\n")
        else:
            print("❌ 保存时出错。\n")


def handle_theme_paragraph():
    """Handles creating or updating the paragraph-long theme using an LLM."""
    ensure_meta_dir()

    # 首先检查一句话主题是否存在
    one_line_data = get_data_manager().read_theme_one_line()
    if not one_line_data:
        print("\n请先使用选项 [1] 确立一句话主题。")
        return
    
    # 获取实际的主题内容
    if isinstance(one_line_data, dict):
        one_line_theme = one_line_data.get("theme", "")
    elif isinstance(one_line_data, str):
        one_line_theme = one_line_data
    else:
        one_line_theme = ""
    
    if not one_line_theme.strip():
        print("\n请先使用选项 [1] 确立一句话主题。")
        return

    # 检查是否已有段落主题
    existing_paragraph = get_data_manager().read_theme_paragraph()

    if existing_paragraph:
        # 如果已有段落主题，显示并提供操作选项
        print("\n--- 当前段落主题 ---")
        print(existing_paragraph)
        print("------------------------\n")

        action = questionary.select(
            "请选择您要进行的操作：",
            choices=[
                "1. 查看当前内容（已显示）",
                "2. 修改当前内容",
                "3. 重新生成内容",
                "4. 返回主菜单"
            ],
            use_indicator=True
        ).ask()

        if action is None or action.startswith("4."):
            print("返回主菜单。\n")
            return
        elif action.startswith("1."):
            print("当前内容已在上方显示。\n")
            return
        elif action.startswith("2."):
            edited_paragraph = questionary.text(
                "请修改您的段落主题:",
                default=existing_paragraph,
                multiline=True
            ).ask()
            if edited_paragraph and edited_paragraph.strip() and edited_paragraph != existing_paragraph:
                if get_data_manager().write_theme_paragraph(edited_paragraph):
                    print("段落主题已更新。\n")
                else:
                    print("保存段落主题时出错。\n")
            elif edited_paragraph is None:
                print("操作已取消。\n")
            else:
                print("内容未更改。\n")
            return
        elif action.startswith("3."):
            # 继续执行重新生成逻辑
            print("\n正在重新生成段落主题...")
        else:
            return

    # 生成新的段落主题（无论是首次生成还是重新生成）
    if not one_line_theme.strip():
        print("\n一句话主题为空，请先使用选项 [1] 确立主题。")
        return
            
    print(f'\n基于主题 "{one_line_theme}" 进行扩展...')

    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成的内容。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    # 如果用户不想继续，提供确认选项
    if not user_prompt.strip():
        confirm = questionary.confirm("确定要继续生成段落主题吗？").ask()
        if not confirm:
            print("操作已取消。\n")
            return

    if not llm_service.is_available():
        print("AI服务不可用，请检查配置。")
        return

    if user_prompt.strip():
        print(f"用户指导：{user_prompt.strip()}")
    
    print("正在调用 AI 生成段落主题，请稍候...")
    generated_paragraph = llm_service.generate_theme_paragraph(one_line_theme, user_prompt)
    
    if not generated_paragraph:
        print("AI生成失败，请稍后重试。")
        return

    print("\n--- AI 生成的段落主题 ---")
    print(generated_paragraph)
    print("------------------------\n")
    
    # 提供更清晰的操作选项
    action = questionary.select(
        "请选择您要进行的操作：",
        choices=[
            "1. 接受并保存",
            "2. 修改后保存", 
            "3. 放弃此次生成"
        ],
        use_indicator=True
    ).ask()

    if action is None or action.startswith("3."):
        print("已放弃此次生成。\n")
        return
    elif action.startswith("1."):
        # 直接保存
        if get_data_manager().write_theme_paragraph(generated_paragraph):
            print("段落主题已保存。\n")
        else:
            print("保存段落主题时出错。\n")
    elif action.startswith("2."):
        # 修改后保存
        edited_paragraph = questionary.text(
            "请修改您的段落主题:",
            default=generated_paragraph,
            multiline=True
        ).ask()

        if edited_paragraph and edited_paragraph.strip():
            if get_data_manager().write_theme_paragraph(edited_paragraph):
                print("段落主题已保存。\n")
            else:
                print("保存段落主题时出错。\n")
        else:
            print("操作已取消或内容为空，未保存。\n")


def handle_world_setting():
    """Handles world setting management including characters, locations, and items."""
    ensure_meta_dir()
    
    # 检查前置条件
    one_line_exists, paragraph_exists = get_data_manager().check_prerequisites_for_world_setting()
    
    if not one_line_exists or not paragraph_exists:
        print("\n请先完成前面的步骤：")
        if not one_line_exists:
            print("- 步骤1: 确立一句话主题")
        if not paragraph_exists:
            print("- 步骤2: 扩展成一段话主题")
        print("\n世界设定需要基于明确的主题来创建角色、场景和道具。\n")
        return
    
    while True:
        choice = questionary.select(
            "请选择要管理的世界设定类型：",
            choices=[
                "1. 角色管理",
                "2. 场景管理",
                "3. 道具管理",
                "4. 返回主菜单"
            ],
            use_indicator=True
        ).ask()
        
        if choice is None or choice.startswith("4."):
            break
        elif choice.startswith("1."):
            handle_characters()
        elif choice.startswith("2."):
            handle_locations()
        elif choice.startswith("3."):
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
        print("\n请先完成前面的步骤：")
        if not one_line_exists:
            print("- 步骤1: 确立一句话主题")
        if not paragraph_exists:
            print("- 步骤2: 扩展成一段话主题")
        print()
        return
    
    while True:
        # 每次循环都重新读取大纲数据
        current_outline = get_data_manager().read_story_outline()
        
        # 显示当前大纲状态
        if current_outline:
            print("\n--- 当前故事大纲 ---")
            # 显示前200字符作为预览
            preview = current_outline[:200] + "..." if len(current_outline) > 200 else current_outline
            print(preview)
            print("------------------------\n")
            
            action = questionary.select(
                "请选择您要进行的操作：",
                choices=[
                    "1. 查看完整大纲",
                    "2. 修改当前大纲",
                    "3. 重新生成大纲",
                    "4. 返回主菜单"
                ],
                use_indicator=True
            ).ask()
            
            if action is None or action.startswith("4."):
                break
            elif action.startswith("1."):
                print("\n--- 完整故事大纲 ---")
                print(current_outline)
                print("------------------------\n")
                
                # 等待用户确认后继续循环
                questionary.press_any_key_to_continue("按任意键继续...").ask()
                continue
            elif action.startswith("2."):
                edit_outline()
                continue
            elif action.startswith("3."):
                print("\n正在重新生成故事大纲...")
                generate_story_outline()
                continue
            else:
                break
        else:
            print("\n当前没有故事大纲，让我们来生成一个。\n")
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
    
    print(f"基于主题和角色信息生成故事大纲...")
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成故事大纲。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    # 如果用户不想继续，提供确认选项
    if not user_prompt.strip():
        confirm = questionary.confirm("确定要继续生成故事大纲吗？").ask()
        if not confirm:
            print("操作已取消。\n")
            return

    if user_prompt.strip():
        print(f"用户指导：{user_prompt.strip()}")
    
    print("正在调用 AI 生成故事大纲，请稍候...")
    generated_outline = llm_service.generate_story_outline(one_line_theme, paragraph_theme, characters_info, user_prompt)
    
    if not generated_outline:
        print("AI生成失败，请稍后重试。")
        return

    print("\n--- AI 生成的故事大纲 ---")
    print(generated_outline)
    print("------------------------\n")
    
    # 提供操作选项
    action = questionary.select(
        "请选择您要进行的操作：",
        choices=[
            "1. 接受并保存",
            "2. 修改后保存", 
            "3. 放弃此次生成"
        ],
        use_indicator=True
    ).ask()

    if action is None or action.startswith("3."):
        print("已放弃此次生成。\n")
        return
    elif action.startswith("1."):
        # 直接保存
        if get_data_manager().write_story_outline(generated_outline):
            print("故事大纲已保存。\n")
        else:
            print("保存故事大纲时出错。\n")
    elif action.startswith("2."):
        # 修改后保存
        edited_outline = questionary.text(
            "请修改故事大纲:",
            default=generated_outline,
            multiline=True
        ).ask()

        if edited_outline and edited_outline.strip():
            if get_data_manager().write_story_outline(edited_outline):
                print("故事大纲已保存。\n")
            else:
                print("保存故事大纲时出错。\n")
        else:
            print("操作已取消或内容为空，未保存。\n")


def edit_outline():
    """Edit existing story outline."""
    current_outline = get_data_manager().read_story_outline()
    print("\n--- 当前故事大纲 ---")
    print(current_outline)
    print("------------------------\n")
    
    edited_outline = questionary.text(
        "请修改故事大纲:",
        default=current_outline,
        multiline=True
    ).ask()
    
    if edited_outline and edited_outline.strip() and edited_outline != current_outline:
        if get_data_manager().write_story_outline(edited_outline):
            print("故事大纲已更新。\n")
        else:
            print("更新故事大纲时出错。\n")
    elif edited_outline is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def handle_chapter_outline():
    """Handles chapter outline management with full CRUD operations."""
    ensure_meta_dir()
    
    # 检查前置条件
    story_outline_exists = get_data_manager().check_prerequisites_for_chapter_outline()
    
    if not story_outline_exists:
        print("\n请先完成步骤4: 编辑故事大纲\n")
        return
    
    while True:
        # 每次循环都重新读取数据
        chapters = get_data_manager().read_chapter_outline()
        
        # 显示当前章节列表
        if chapters:
            print("\n--- 当前分章细纲 ---")
            for i, chapter in enumerate(chapters, 1):
                title = chapter.get('title', f'第{i}章')
                outline = chapter.get('outline', '无大纲')
                preview = outline[:50] + "..." if len(outline) > 50 else outline
                print(f"{i}. {title}: {preview}")
            print("------------------------\n")
        else:
            print("\n当前没有分章细纲。\n")
        
        # 操作选项
        choices = [
            "1. 生成分章细纲",
            "2. 添加新章节",
            "3. 查看章节详情",
            "4. 修改章节信息", 
            "5. 删除章节",
            "6. 返回主菜单"
        ]
        
        if not chapters:
            # 如果没有章节，只显示生成和返回选项
            choices = [
                "1. 生成分章细纲",
                "2. 返回主菜单"
            ]
        
        action = questionary.select(
            "请选择您要进行的操作：",
            choices=choices,
            use_indicator=True
        ).ask()
        
        if action is None:
            break
        elif action.startswith("1."):
            # 生成分章细纲
            generate_chapter_outline()
        elif action.startswith("2.") and chapters:
            # 添加新章节
            add_chapter()
        elif action.startswith("2.") and not chapters:
            # 返回主菜单（当没有章节时）
            break
        elif action.startswith("3."):
            # 查看章节详情
            view_chapter()
        elif action.startswith("4."):
            # 修改章节信息
            edit_chapter()
        elif action.startswith("5."):
            # 删除章节
            delete_chapter()
        elif action.startswith("6.") or action.startswith("2."):
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
    
    print("基于故事大纲生成分章细纲...")
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成分章细纲。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    # 如果用户不想继续，提供确认选项
    if not user_prompt.strip():
        confirm = questionary.confirm("确定要继续生成分章细纲吗？").ask()
        if not confirm:
            print("操作已取消。\n")
            return

    if user_prompt.strip():
        print(f"用户指导：{user_prompt.strip()}")
    
    print("正在调用 AI 生成分章细纲，请稍候...")
    chapter_outline_data = llm_service.generate_chapter_outline(one_line_theme, story_outline, characters_info, user_prompt)
    
    if not chapter_outline_data:
        print("AI生成失败，请稍后重试。")
        return

    # 显示生成的章节
    print("\n--- AI 生成的分章细纲 ---")
    
    # 处理不同的返回格式
    if isinstance(chapter_outline_data, dict):
        chapters = chapter_outline_data.get('chapters', [])
        if not chapters:
            # 如果没有chapters字段，可能是直接返回的章节列表或其他格式
            print("JSON解析结果：")
            print(chapter_outline_data)
        else:
            for i, chapter in enumerate(chapters, 1):
                print(f"\n第{i}章: {chapter.get('title', '无标题')}")
                print(f"大纲: {chapter.get('outline', '无大纲')}")
    else:
        # 如果不是字典格式，直接显示原始内容
        print("AI返回的原始内容：")
        print(chapter_outline_data)
    
    print("------------------------\n")
    
    # 提供操作选项
    action = questionary.select(
        "请选择您要进行的操作：",
        choices=[
            "1. 接受并保存",
            "2. 修改后保存", 
            "3. 放弃此次生成"
        ],
        use_indicator=True
    ).ask()

    if action is None or action.startswith("3."):
        print("已放弃此次生成。\n")
        return
    elif action.startswith("1."):
        # 直接保存
        if isinstance(chapter_outline_data, dict):
            chapters_list = chapter_outline_data.get('chapters', [])
            if chapters_list:
                if get_data_manager().write_chapter_outline(chapters_list):
                    print("分章细纲已保存。\n")
                else:
                    print("保存分章细纲时出错。\n")
            else:
                print("生成的数据格式不正确，无法保存。请检查AI返回的内容格式。\n")
        else:
            print("生成的数据不是预期的JSON格式，无法直接保存。请选择修改后保存。\n")
    elif action.startswith("2."):
        # 修改后保存
        if isinstance(chapter_outline_data, dict):
            chapters = chapter_outline_data.get('chapters', [])
            if not chapters:
                print("无有效的章节数据可以修改。\n")
                return
        else:
            print("由于数据格式问题，请手动输入章节信息：\n")
            chapters = []
            
        # 让用户逐个确认或修改章节
        print("请逐个确认或修改每个章节：\n")
        modified_chapters = []
        
        if chapters:
            for i, chapter in enumerate(chapters, 1):
                print(f"--- 第{i}章 ---")
                print(f"当前标题: {chapter.get('title', '无标题')}")
                print(f"当前大纲: {chapter.get('outline', '无大纲')}")
                
                keep_chapter = questionary.confirm(f"保留第{i}章吗？").ask()
                if keep_chapter:
                    # 可以选择修改标题和大纲
                    modify = questionary.confirm("需要修改这一章吗？").ask()
                    if modify:
                        new_title = questionary.text("章节标题:", default=chapter.get('title', '')).ask()
                        new_outline = questionary.text("章节大纲:", default=chapter.get('outline', ''), multiline=True).ask()
                        if new_title is not None and new_outline is not None:
                            modified_chapters.append({"title": new_title, "outline": new_outline})
                        else:
                            modified_chapters.append(chapter)
                    else:
                        modified_chapters.append(chapter)
        else:
            # 手动创建章节
            while True:
                add_chapter = questionary.confirm("添加一个章节吗？").ask()
                if not add_chapter:
                    break
                    
                title = questionary.text("章节标题:").ask()
                if not title:
                    continue
                    
                outline = questionary.text("章节大纲:", multiline=True).ask()
                if outline is None:
                    continue
                    
                modified_chapters.append({"title": title.strip(), "outline": outline.strip()})
        
        if modified_chapters:
            if get_data_manager().write_chapter_outline(modified_chapters):
                print("分章细纲已保存。\n")
            else:
                print("保存分章细纲时出错。\n")
        else:
            print("未保存任何章节。\n")


def add_chapter():
    """Add a new chapter."""
    title = questionary.text("请输入章节标题:").ask()
    if not title or not title.strip():
        print("章节标题不能为空。\n")
        return
    
    outline = questionary.text("请输入章节大纲:", multiline=True).ask()
    if outline is None:
        print("操作已取消。\n")
        return
    
    new_chapter = {"title": title.strip(), "outline": outline.strip()}
    
    chapters = get_data_manager().read_chapter_outline()
    chapters.append(new_chapter)
    
    if get_data_manager().write_chapter_outline(chapters):
        print(f"章节 '{title}' 已添加。\n")
    else:
        print("添加章节时出错。\n")


def view_chapter():
    """View chapter details."""
    chapters = get_data_manager().read_chapter_outline()
    if not chapters:
        print("\n当前没有章节信息。\n")
        return
    
    chapter_choices = [f"{i+1}. {ch.get('title', f'第{i+1}章')}" for i, ch in enumerate(chapters)]
    choice = questionary.select(
        "请选择要查看的章节：",
        choices=chapter_choices,
        use_indicator=True
    ).ask()
    
    if choice:
        chapter_index = int(choice.split('.')[0]) - 1
        chapter = chapters[chapter_index]
        print(f"\n--- {chapter.get('title', f'第{chapter_index+1}章')} ---")
        print(chapter.get('outline', '无大纲'))
        print("------------------------\n")


def edit_chapter():
    """Edit chapter information."""
    chapters = get_data_manager().read_chapter_outline()
    if not chapters:
        print("\n当前没有章节信息可编辑。\n")
        return
    
    chapter_choices = [f"{i+1}. {ch.get('title', f'第{i+1}章')}" for i, ch in enumerate(chapters)]
    choice = questionary.select(
        "请选择要修改的章节：",
        choices=chapter_choices,
        use_indicator=True
    ).ask()
    
    if not choice:
        return
    
    chapter_index = int(choice.split('.')[0]) - 1
    chapter = chapters[chapter_index]
    
    print(f"\n--- 当前章节信息 ---")
    print(f"标题: {chapter.get('title', '无标题')}")
    print(f"大纲: {chapter.get('outline', '无大纲')}")
    print("------------------------\n")
    
    new_title = questionary.text("章节标题:", default=chapter.get('title', '')).ask()
    if new_title is None:
        print("操作已取消。\n")
        return
    
    new_outline = questionary.text("章节大纲:", default=chapter.get('outline', ''), multiline=True).ask()
    if new_outline is None:
        print("操作已取消。\n")
        return
    
    # 更新章节信息
    chapters[chapter_index] = {"title": new_title.strip(), "outline": new_outline.strip()}
    if get_data_manager().write_chapter_outline(chapters):
        print("章节信息已更新。\n")
    else:
        print("更新章节信息时出错。\n")


def delete_chapter():
    """Delete a chapter."""
    chapters = get_data_manager().read_chapter_outline()
    if not chapters:
        print("\n当前没有章节信息可删除。\n")
        return
    
    chapter_choices = [f"{i+1}. {ch.get('title', f'第{i+1}章')}" for i, ch in enumerate(chapters)]
    choice = questionary.select(
        "请选择要删除的章节：",
        choices=chapter_choices,
        use_indicator=True
    ).ask()
    
    if not choice:
        return
    
    chapter_index = int(choice.split('.')[0]) - 1
    chapter_title = chapters[chapter_index].get('title', f'第{chapter_index+1}章')
    
    confirm = questionary.confirm(f"确定要删除章节 '{chapter_title}' 吗？").ask()
    if confirm:
        chapters.pop(chapter_index)
        if get_data_manager().write_chapter_outline(chapters):
            print(f"章节 '{chapter_title}' 已删除。\n")
        else:
            print("删除章节时出错。\n")
    else:
        print("操作已取消。\n")


def handle_chapter_summary():
    """Handles chapter summary management with full CRUD operations."""
    ensure_meta_dir()
    
    # 检查前置条件
    chapter_outline_exists = get_data_manager().check_prerequisites_for_chapter_summary()
    
    if not chapter_outline_exists:
        print("\n请先完成步骤5: 编辑分章细纲\n")
        return
    
    # 读取分章细纲
    chapters = get_data_manager().read_chapter_outline()
    
    if not chapters:
        print("\n分章细纲为空，请先完成步骤5。\n")
        return
    
    while True:
        # 每次循环都重新读取数据
        summaries = get_data_manager().read_chapter_summaries()
        
        # 显示当前章节概要状态
        print(f"\n--- 章节概要状态 (共{len(chapters)}章) ---")
        
        for i, chapter in enumerate(chapters, 1):
            chapter_key = f"chapter_{i}"
            title = chapter.get('title', f'第{i}章')
            status = "✓ 已完成" if chapter_key in summaries else "○ 未完成"
            print(f"{i}. {title}: {status}")
        print("------------------------\n")
        
        # 操作选项
        choices = [
            "1. 生成所有章节概要",
            "2. 生成单个章节概要",
            "3. 查看章节概要",
            "4. 修改章节概要",
            "5. 删除章节概要",
            "6. 返回主菜单"
        ]
        
        action = questionary.select(
            "请选择您要进行的操作：",
            choices=choices,
            use_indicator=True
        ).ask()
        
        if action is None or action.startswith("6."):
            break
        elif action.startswith("1."):
            # 生成所有章节概要
            generate_all_summaries(chapters)
        elif action.startswith("2."):
            # 生成单个章节概要
            generate_single_summary(chapters)
        elif action.startswith("3."):
            # 查看章节概要
            view_chapter_summary(chapters)
        elif action.startswith("4."):
            # 修改章节概要
            edit_chapter_summary(chapters)
        elif action.startswith("5."):
            # 删除章节概要
            delete_chapter_summary(chapters)


def generate_all_summaries(chapters):
    """Generate summaries for all chapters."""
    print(f"准备为所有 {len(chapters)} 个章节生成概要...")
    
    # 提供生成模式选择
    mode_choice = questionary.select(
        "请选择生成模式：",
        choices=[
            "1. 🚀 并发生成（推荐）- 同时生成多个章节，速度更快",
            "2. 📝 顺序生成 - 逐个生成章节，更稳定",
            "3. 🔙 返回上级菜单"
        ],
        use_indicator=True
    ).ask()
    
    if mode_choice is None or mode_choice.startswith("3."):
        return
    
    use_async = mode_choice.startswith("1.")
    
    confirm_msg = f"这将为所有 {len(chapters)} 个章节生成概要"
    if use_async:
        confirm_msg += "（并发模式，速度较快）"
    else:
        confirm_msg += "（顺序模式，较为稳定）"
    confirm_msg += "。确定继续吗？"
    
    confirm = questionary.confirm(confirm_msg).ask()
    if not confirm:
        print("操作已取消。\n")
        return
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成章节概要。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

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
            print(f"\n正在生成第{i}章概要... ({i}/{len(chapters)})")
            
            summary = llm_service.generate_chapter_summary(chapter, i, context_info, user_prompt)
            
            if summary:
                summaries[chapter_key] = {
                    "title": chapter.get('title', f'第{i}章'),
                    "summary": summary
                }
                print(f"✅ 第{i}章概要生成完成")
            else:
                failed_chapters.append(i)
                print(f"❌ 第{i}章概要生成失败")
        
        # 保存结果
        if summaries:
            if get_data_manager().write_chapter_summaries(summaries):
                print(f"\n✅ 成功生成 {len(summaries)} 个章节概要")
                
                if failed_chapters:
                    print(f"失败的章节: {', '.join(map(str, failed_chapters))}")
                    print("您可以稍后单独重新生成失败的章节。")
            else:
                print("❌ 保存章节概要时出错")
        else:
            print("\n❌ 所有章节概要生成均失败")


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
    
    choice = questionary.select(
        "请选择要生成概要的章节：",
        choices=chapter_choices,
        use_indicator=True
    ).ask()
    
    if not choice:
        return
    
    chapter_index = int(choice.split('.')[0]) - 1
    chapter_num = chapter_index + 1
    chapter = chapters[chapter_index]
    chapter_key = f"chapter_{chapter_num}"
    
    # 如果已存在概要，询问是否覆盖
    if chapter_key in summaries:
        overwrite = questionary.confirm(f"第{chapter_num}章已有概要，是否覆盖？").ask()
        if not overwrite:
            print("操作已取消。\n")
            return
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成章节概要。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    if not llm_service.is_available():
        print("AI服务不可用，请检查配置。")
        return
    
    # 读取相关信息
    context_info = get_data_manager().get_context_info()
    
    print(f"\n正在生成第{chapter_num}章概要...")
    summary = llm_service.generate_chapter_summary(chapter, chapter_num, context_info, user_prompt)
    
    if summary:
        print(f"\n--- 第{chapter_num}章概要 ---")
        print(summary)
        print("------------------------\n")
        
        # 提供操作选项
        action = questionary.select(
            "请选择您要进行的操作：",
            choices=[
                "1. 接受并保存",
                "2. 修改后保存", 
                "3. 放弃此次生成"
            ],
            use_indicator=True
        ).ask()

        if action is None or action.startswith("3."):
            print("已放弃此次生成。\n")
            return
        elif action.startswith("1."):
            # 直接保存
            if get_data_manager().set_chapter_summary(chapter_num, chapter.get('title', f'第{chapter_num}章'), summary):
                print(f"第{chapter_num}章概要已保存。\n")
            else:
                print("保存章节概要时出错。\n")
        elif action.startswith("2."):
            # 修改后保存
            edited_summary = questionary.text(
                "请修改章节概要:",
                default=summary,
                multiline=True
            ).ask()

            if edited_summary and edited_summary.strip():
                if get_data_manager().set_chapter_summary(chapter_num, chapter.get('title', f'第{chapter_num}章'), edited_summary):
                    print(f"第{chapter_num}章概要已保存。\n")
                else:
                    print("保存章节概要时出错。\n")
            else:
                print("操作已取消或内容为空，未保存。\n")
    else:
        print(f"第{chapter_num}章概要生成失败。\n")





def view_chapter_summary(chapters):
    """View chapter summary details."""
    summaries = get_data_manager().read_chapter_summaries()
    if not summaries:
        print("\n当前没有章节概要。\n")
        return
    
    # 只显示有概要的章节
    available_chapters = []
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in summaries:
            title = chapter.get('title', f'第{i}章')
            available_chapters.append(f"{i}. {title}")
    
    if not available_chapters:
        print("\n当前没有章节概要。\n")
        return
    
    choice = questionary.select(
        "请选择要查看的章节概要：",
        choices=available_chapters,
        use_indicator=True
    ).ask()
    
    if choice:
        chapter_num = int(choice.split('.')[0])
        chapter_key = f"chapter_{chapter_num}"
        summary_info = summaries[chapter_key]
        
        print(f"\n--- {summary_info['title']} ---")
        print(summary_info['summary'])
        print("------------------------\n")


def edit_chapter_summary(chapters):
    """Edit chapter summary."""
    summaries = get_data_manager().read_chapter_summaries()
    if not summaries:
        print("\n当前没有章节概要可编辑。\n")
        return
    
    # 只显示有概要的章节
    available_chapters = []
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in summaries:
            title = chapter.get('title', f'第{i}章')
            available_chapters.append(f"{i}. {title}")
    
    choice = questionary.select(
        "请选择要修改的章节概要：",
        choices=available_chapters,
        use_indicator=True
    ).ask()
    
    if not choice:
        return
    
    chapter_num = int(choice.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    summary_info = summaries[chapter_key]
    
    print(f"\n--- 当前概要：{summary_info['title']} ---")
    print(summary_info['summary'])
    print("------------------------\n")
    
    edited_summary = questionary.text(
        "请修改章节概要:",
        default=summary_info['summary'],
        multiline=True
    ).ask()
    
    if edited_summary and edited_summary.strip() and edited_summary != summary_info['summary']:
        if get_data_manager().set_chapter_summary(chapter_num, summary_info['title'], edited_summary):
            print(f"第{chapter_num}章概要已更新。\n")
        else:
            print("更新章节概要时出错。\n")
    elif edited_summary is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def delete_chapter_summary(chapters):
    """Delete chapter summary."""
    summaries = get_data_manager().read_chapter_summaries()
    if not summaries:
        print("\n当前没有章节概要可删除。\n")
        return
    
    # 只显示有概要的章节
    available_chapters = []
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in summaries:
            title = chapter.get('title', f'第{i}章')
            available_chapters.append(f"{i}. {title}")
    
    choice = questionary.select(
        "请选择要删除的章节概要：",
        choices=available_chapters,
        use_indicator=True
    ).ask()
    
    if not choice:
        return
    
    chapter_num = int(choice.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    title = summaries[chapter_key]['title']
    
    confirm = questionary.confirm(f"确定要删除第{chapter_num}章 '{title}' 的概要吗？").ask()
    if confirm:
        if get_data_manager().delete_chapter_summary(chapter_num):
            print(f"第{chapter_num}章概要已删除。\n")
        else:
            print("删除章节概要时出错。\n")
    else:
        print("操作已取消。\n")


def handle_novel_generation():
    """Handles novel text generation with full management operations."""
    ensure_meta_dir()
    
    # 检查前置条件
    chapter_summary_exists = get_data_manager().check_prerequisites_for_novel_generation()
    
    if not chapter_summary_exists:
        print("\n请先完成步骤6: 编辑章节概要\n")
        return
    
    # 读取章节概要
    summaries = get_data_manager().read_chapter_summaries()
    
    if not summaries:
        print("\n章节概要为空，请先完成步骤6。\n")
        return
    
    # 读取分章细纲以获取章节顺序
    chapters = get_data_manager().read_chapter_outline()
    
    while True:
        # 每次循环都重新读取数据
        novel_chapters = get_data_manager().read_novel_chapters()
        
        # 显示当前小说正文状态
        print(f"\n--- 小说正文状态 (共{len(summaries)}章) ---")
        
        # 按章节顺序显示
        for i in range(1, len(chapters) + 1):
            chapter_key = f"chapter_{i}"
            if chapter_key in summaries:
                chapter_title = chapters[i-1].get('title', f'第{i}章')
                status = "✓ 已完成" if chapter_key in novel_chapters else "○ 未完成"
                word_count = len(novel_chapters.get(chapter_key, {}).get('content', ''))
                word_info = f" ({word_count}字)" if word_count > 0 else ""
                print(f"{i}. {chapter_title}: {status}{word_info}")
        print("------------------------\n")
        
        # 操作选项
        choices = [
            "1. 生成所有章节正文",
            "2. 生成单个章节正文",
            "3. 查看章节正文",
            "4. 修改章节正文",
            "5. 删除章节正文",
            "6. 分章节导出",
            "7. 返回主菜单"
        ]
        
        action = questionary.select(
            "请选择您要进行的操作：",
            choices=choices,
            use_indicator=True
        ).ask()
        
        if action is None or action.startswith("7."):
            break
        elif action.startswith("1."):
            # 生成所有章节正文
            generate_all_novel_chapters(chapters, summaries)
        elif action.startswith("2."):
            # 生成单个章节正文
            generate_single_novel_chapter(chapters, summaries, novel_chapters)
        elif action.startswith("3."):
            # 查看章节正文
            view_novel_chapter(chapters, novel_chapters)
        elif action.startswith("4."):
            # 修改章节正文
            edit_novel_chapter(chapters, novel_chapters)
        elif action.startswith("5."):
            # 删除章节正文
            delete_novel_chapter(chapters, novel_chapters)
        elif action.startswith("6."):
            # 分章节导出
            handle_novel_export(chapters, novel_chapters)


def generate_all_novel_chapters(chapters, summaries):
    """Generate novel text for all chapters."""
    available_chapters = sum(1 for i in range(1, len(chapters) + 1) if f"chapter_{i}" in summaries)
    print(f"准备为 {available_chapters} 个有概要的章节生成正文...")
    
    if available_chapters == 0:
        print("没有可用的章节概要，请先生成章节概要。")
        return
    
    # 提供生成模式选择
    mode_choice = questionary.select(
        "请选择生成模式：",
        choices=[
            "1. 🚀 并发生成（推荐）- 同时生成多个章节，速度更快",
            "2. 📝 顺序生成 - 逐个生成章节，更稳定",
            "3. 🔙 返回上级菜单"
        ],
        use_indicator=True
    ).ask()
    
    if mode_choice is None or mode_choice.startswith("3."):
        return
    
    use_async = mode_choice.startswith("1.")
    
    confirm_msg = f"这将为 {available_chapters} 个章节生成正文"
    if use_async:
        confirm_msg += "（并发模式，速度较快）"
    else:
        confirm_msg += "（顺序模式，较为稳定）"
    confirm_msg += "，可能需要较长时间。确定继续吗？"
    
    confirm = questionary.confirm(confirm_msg).ask()
    if not confirm:
        print("操作已取消。\n")
        return
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成小说正文。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

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
            progress.start(available_chapters, "准备开始并发生成小说正文...")
            
            try:
                callback = progress.create_callback()
                results, failed_chapters = await llm_service.generate_all_novels_async(
                    chapters, summaries, context_info, user_prompt, callback
                )
                
                # 保存结果
                if results:
                    if get_data_manager().write_novel_chapters(results):
                        total_words = sum(ch.get('word_count', 0) for ch in results.values())
                        progress.finish(f"成功生成 {len(results)} 个章节正文，总计 {total_words} 字")
                        
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
            print(f"\n正在生成第{i}章正文... ({processed}/{available_chapters})")
            
            chapter_content = llm_service.generate_novel_chapter(
                chapters[i-1], summaries[chapter_key], i, context_info, user_prompt
            )
            
            if chapter_content:
                novel_chapters[chapter_key] = {
                    "title": chapters[i-1].get('title', f'第{i}章'),
                    "content": chapter_content,
                    "word_count": len(chapter_content)
                }
                print(f"✅ 第{i}章正文生成完成 ({len(chapter_content)}字)")
            else:
                failed_chapters.append(i)
                print(f"❌ 第{i}章正文生成失败")
        
        # 保存结果
        if novel_chapters:
            if get_data_manager().write_novel_chapters(novel_chapters):
                total_words = sum(ch.get('word_count', 0) for ch in novel_chapters.values())
                print(f"\n✅ 成功生成 {len(novel_chapters)} 个章节正文，总计 {total_words} 字")
                
                if failed_chapters:
                    print(f"失败的章节: {', '.join(map(str, failed_chapters))}")
                    print("您可以稍后单独重新生成失败的章节。")
            else:
                print("❌ 保存小说正文时出错")
        else:
            print("\n❌ 所有章节正文生成均失败")


def generate_single_novel_chapter(chapters, summaries, novel_data):
    """Generate novel text for a single chapter."""
    # 选择章节
    chapter_choices = []
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in summaries:
            title = chapters[i-1].get('title', f'第{i}章')
            status = "已完成" if chapter_key in novel_data.get('chapters', {}) else "未完成"
            word_count = novel_data.get('chapters', {}).get(chapter_key, {}).get('word_count', 0)
            word_info = f" ({word_count}字)" if word_count > 0 else ""
            chapter_choices.append(f"{i}. {title} ({status}){word_info}")
    
    choice = questionary.select(
        "请选择要生成正文的章节：",
        choices=chapter_choices,
        use_indicator=True
    ).ask()
    
    if not choice:
        return
    
    chapter_num = int(choice.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    chapter = chapters[chapter_num - 1]
    
    # 如果已存在正文，询问是否覆盖
    if chapter_key in novel_data.get('chapters', {}):
        overwrite = questionary.confirm(f"第{chapter_num}章已有正文，是否覆盖？").ask()
        if not overwrite:
            print("操作已取消。\n")
            return
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成小说正文。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    if not llm_service.is_available():
        print("AI服务不可用，请检查配置。")
        return
    
    # 读取相关信息
    context_info = get_data_manager().get_context_info()
    
    print(f"\n正在生成第{chapter_num}章正文...")
    chapter_content = llm_service.generate_novel_chapter(
        chapter, summaries[chapter_key], chapter_num, context_info, user_prompt
    )
    
    if chapter_content:
        print(f"\n--- 第{chapter_num}章正文预览 (前500字) ---")
        preview = chapter_content[:500] + "..." if len(chapter_content) > 500 else chapter_content
        print(preview)
        print(f"\n总字数: {len(chapter_content)} 字")
        print("------------------------\n")
        
        # 提供操作选项
        action = questionary.select(
            "请选择您要进行的操作：",
            choices=[
                "1. 接受并保存",
                "2. 修改后保存", 
                "3. 放弃此次生成"
            ],
            use_indicator=True
        ).ask()

        if action is None or action.startswith("3."):
            print("已放弃此次生成。\n")
            return
        elif action.startswith("1."):
            # 直接保存
            if get_data_manager().set_novel_chapter(chapter_num, chapter.get('title', f'第{chapter_num}章'), chapter_content):
                print(f"第{chapter_num}章正文已保存 ({len(chapter_content)}字)。\n")
            else:
                print("保存章节正文时出错。\n")
        elif action.startswith("2."):
            # 修改后保存
            edited_content = questionary.text(
                "请修改章节正文:",
                default=chapter_content,
                multiline=True
            ).ask()

            if edited_content and edited_content.strip():
                if get_data_manager().set_novel_chapter(chapter_num, chapter.get('title', f'第{chapter_num}章'), edited_content):
                    print(f"第{chapter_num}章正文已保存 ({len(edited_content)}字)。\n")
                else:
                    print("保存章节正文时出错。\n")
            else:
                print("操作已取消或内容为空，未保存。\n")
    else:
        print(f"第{chapter_num}章正文生成失败。\n")



def view_novel_chapter(chapters, novel_data):
    """View novel chapter content."""
    novel_chapters = novel_data.get('chapters', {})
    if not novel_chapters:
        print("\n当前没有小说正文。\n")
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
        print("\n当前没有小说正文。\n")
        return
    
    choice = questionary.select(
        "请选择要查看的章节正文：",
        choices=available_chapters,
        use_indicator=True
    ).ask()
    
    if choice:
        chapter_num = int(choice.split('.')[0])
        chapter_key = f"chapter_{chapter_num}"
        chapter_info = novel_chapters[chapter_key]
        
        print(f"\n--- {chapter_info['title']} ---")
        print(f"字数: {chapter_info.get('word_count', 0)} 字\n")
        print(chapter_info['content'])
        print("------------------------\n")


def edit_novel_chapter(chapters, novel_data):
    """Edit novel chapter content."""
    novel_chapters = novel_data.get('chapters', {})
    if not novel_chapters:
        print("\n当前没有小说正文可编辑。\n")
        return
    
    # 只显示有正文的章节
    available_chapters = []
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in novel_chapters:
            title = chapters[i-1].get('title', f'第{i}章')
            word_count = novel_chapters[chapter_key].get('word_count', 0)
            available_chapters.append(f"{i}. {title} ({word_count}字)")
    
    choice = questionary.select(
        "请选择要修改的章节正文：",
        choices=available_chapters,
        use_indicator=True
    ).ask()
    
    if not choice:
        return
    
    chapter_num = int(choice.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    chapter_info = novel_chapters[chapter_key]
    
    print(f"\n--- 当前正文：{chapter_info['title']} ---")
    print(f"字数: {chapter_info.get('word_count', 0)} 字")
    print("------------------------\n")
    
    edited_content = questionary.text(
        "请修改章节正文:",
        default=chapter_info['content'],
        multiline=True
    ).ask()
    
    if edited_content and edited_content.strip() and edited_content != chapter_info['content']:
        if get_data_manager().set_novel_chapter(chapter_num, chapter_info['title'], edited_content):
            print(f"第{chapter_num}章正文已更新 ({len(edited_content)}字)。\n")
        else:
            print("更新章节正文时出错。\n")
    elif edited_content is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def delete_novel_chapter(chapters, novel_data):
    """Delete novel chapter content."""
    novel_chapters = novel_data.get('chapters', {})
    if not novel_chapters:
        print("\n当前没有小说正文可删除。\n")
        return
    
    # 只显示有正文的章节
    available_chapters = []
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key in novel_chapters:
            title = chapters[i-1].get('title', f'第{i}章')
            word_count = novel_chapters[chapter_key].get('word_count', 0)
            available_chapters.append(f"{i}. {title} ({word_count}字)")
    
    choice = questionary.select(
        "请选择要删除的章节正文：",
        choices=available_chapters,
        use_indicator=True
    ).ask()
    
    if not choice:
        return
    
    chapter_num = int(choice.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    title = novel_chapters[chapter_key]['title']
    
    confirm = questionary.confirm(f"确定要删除第{chapter_num}章 '{title}' 的正文吗？").ask()
    if confirm:
        if get_data_manager().delete_novel_chapter(chapter_num):
            print(f"第{chapter_num}章正文已删除。\n")
        else:
            print("删除章节正文时出错。\n")
    else:
        print("操作已取消。\n")


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
            "1. 导出完整小说",
            "2. 导出单个章节",
            "3. 导出章节范围",
            "4. 返回上级菜单"
        ]
        
        action = questionary.select(
            "请选择导出操作：",
            choices=choices,
            use_indicator=True
        ).ask()
        
        if action is None or action.startswith("4."):
            break
        elif action.startswith("1."):
            # 导出完整小说
            export_complete_novel(chapters, novel_chapters)
        elif action.startswith("2."):
            # 导出单个章节
            export_single_chapter(chapters, novel_chapters)
        elif action.startswith("3."):
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
    
    choice = questionary.select(
        "请选择要导出的章节：",
        choices=available_chapters,
        use_indicator=True
    ).ask()
    
    if not choice or choice == "返回上级菜单":
        return
    
    chapter_num = int(choice.split('.')[0])
    chapter_key = f"chapter_{chapter_num}"
    chapter_info = novel_chapters[chapter_key]
    
    # 生成文件名
    novel_name = get_novel_name()
    chapter_title = chapters[chapter_num-1].get('title', f'第{chapter_num}章')
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{novel_name}_{chapter_title}_{timestamp}.txt"
    
    # 写入文件
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{novel_name}\n")
            f.write("=" * 50 + "\n")
            f.write(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"导出章节: {chapter_title}\n")
            f.write(f"字数: {chapter_info.get('word_count', len(chapter_info.get('content', '')))} 字\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"{chapter_info['title']}\n")
            f.write("=" * 30 + "\n\n")
            f.write(chapter_info['content'])
        
        print(f"\n✅ 章节已成功导出到文件: {filename}")
        print(f"小说名: {novel_name}")
        print(f"章节: {chapter_title}")
        print(f"字数: {chapter_info.get('word_count', len(chapter_info.get('content', '')))} 字\n")
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
    
    start_choice = questionary.select(
        "请选择起始章节：",
        choices=start_choices,
        use_indicator=True
    ).ask()
    
    if not start_choice or start_choice == "返回上级菜单":
        return
    
    start_chapter = int(start_choice.split('.')[0])
    
    # 创建结束章节选择列表（只包含起始章节及之后的章节）
    end_choices = [f"{i}. 第{i}章" for i in available_chapter_nums if i >= start_chapter]
    end_choices.append("返回上级菜单")
    
    end_choice = questionary.select(
        "请选择结束章节：",
        choices=end_choices,
        use_indicator=True
    ).ask()
    
    if not end_choice or end_choice == "返回上级菜单":
        return
    
    end_chapter = int(end_choice.split('.')[0])
    
    # 导出选定范围的章节
    export_chapters = [i for i in available_chapter_nums if start_chapter <= i <= end_chapter]
    
    if not export_chapters:
        print("\n没有可导出的章节。\n")
        return
    
    # 生成文件名
    novel_name = get_novel_name()
    if start_chapter == end_chapter:
        chapter_range = f"第{start_chapter}章"
    else:
        chapter_range = f"第{start_chapter}-{end_chapter}章"
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{novel_name}_{chapter_range}_{timestamp}.txt"
    
    # 写入文件
    try:
        total_words = 0
        with open(filename, 'w', encoding='utf-8') as f:
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
        
        print(f"\n✅ 章节范围已成功导出到文件: {filename}")
        print(f"小说名: {novel_name}")
        print(f"导出范围: {chapter_range}")
        print(f"章节数: {len(export_chapters)} 章")
        print(f"总字数: {total_words} 字\n")
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
    
    # 生成文件名
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{novel_name}_{chapter_range}_{timestamp}.txt"
    
    # 写入文件
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"{novel_name}\n")
            f.write("=" * 50 + "\n")
            f.write(f"导出时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"导出范围: {chapter_range}\n")
            f.write(f"总字数: {total_words} 字\n")
            f.write(f"章节数: {len(novel_chapters)} 章\n")
            f.write("=" * 50 + "\n")
            f.writelines(complete_novel)
        
        print(f"\n小说已成功导出到文件: {filename}")
        print(f"小说名: {novel_name}")
        print(f"导出范围: {chapter_range}")
        print(f"总字数: {total_words} 字")
        print(f"章节数: {len(novel_chapters)} 章\n")
    except Exception as e:
        print(f"\n导出失败: {e}\n")




def handle_system_settings():
    """Handle system settings including retry configuration."""
    while True:
        choice = questionary.select(
            "请选择系统设置项:",
            choices=[
                "1. 查看重试设置",
                "2. 修改重试设置",
                "3. 重置重试设置",
                "4. 返回主菜单"
            ],
            use_indicator=True
        ).ask()

        if choice is None or choice.startswith("4."):
            break
        elif choice.startswith("1."):
            show_retry_config()
        elif choice.startswith("2."):
            modify_retry_config()
        elif choice.startswith("3."):
            reset_retry_config()

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
    
    choice = questionary.select(
        "请选择要修改的配置项:",
        choices=choices,
        use_indicator=True
    ).ask()
    
    if choice is None or choice.endswith("返回上级菜单"):
        return
    
    # 解析选择
    idx = int(choice.split('.')[0]) - 1
    desc, key, value_type, min_val, max_val = modifiable_configs[idx]
    
    current_value = RETRY_CONFIG[key]
    
    print(f"\n当前 {desc}: {current_value}")
    
    if value_type == "bool":
        new_value = questionary.confirm(f"启用 {desc}").ask()
        if new_value is not None:
            RETRY_CONFIG[key] = new_value
            print(f"✅ {desc} 已设置为: {'启用' if new_value else '禁用'}")
        else:
            print("❌ 操作已取消")
    elif value_type in ["int", "float"]:
        try:
            prompt = f"请输入新的 {desc}"
            if min_val is not None and max_val is not None:
                prompt += f" (范围: {min_val}-{max_val})"
            prompt += ":"
            
            input_value = questionary.text(prompt, default=str(current_value)).ask()
            
            if input_value is None:
                print("❌ 操作已取消")
                return
                
            if value_type == "int":
                new_value = int(input_value)
            else:
                new_value = float(input_value)
            
            # 验证范围
            if min_val is not None and new_value < min_val:
                print(f"❌ 值太小，最小值为 {min_val}")
                return
            if max_val is not None and new_value > max_val:
                print(f"❌ 值太大，最大值为 {max_val}")
                return
                
            RETRY_CONFIG[key] = new_value
            print(f"✅ {desc} 已设置为: {new_value}")
            
        except ValueError:
            print("❌ 输入的值格式不正确")
    
    input("\n按回车键继续...")

def reset_retry_config():
    """Reset retry configuration to defaults."""
    print("\n🔄 重置重试配置")
    
    confirm = questionary.confirm("确定要将重试配置重置为默认值吗？").ask()
    
    if confirm:
        # 重置为默认配置
        default_config = {
            "max_retries": 3,
            "base_delay": 1.0,
            "max_delay": 30.0,
            "exponential_backoff": True,
            "backoff_multiplier": 2.0,
            "jitter": True,
            "retryable_status_codes": [429, 500, 502, 503, 504],
            "retryable_exceptions": ["timeout", "connection", "network", "dns", "ssl"],
            "enable_batch_retry": True,
            "retry_delay_jitter_range": 0.1
        }
        
        for key, value in default_config.items():
            RETRY_CONFIG[key] = value
        
        print("✅ 重试配置已重置为默认值")
    else:
        print("❌ 操作已取消")
    
    input("\n按回车键继续...")


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
    
    new_name = questionary.text(
        "请输入新的小说名称:",
        default=current_name if current_name != "未命名小说" else ""
    ).ask()
    
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
        first_item = f"📝 1. 确立一句话主题 - 《{current_novel_name}》" if current_novel_name != "未命名小说" else "📝 1. 确立一句话主题 - 开始您的创作之旅"
        
        # 创作流程菜单
        choice = questionary.select(
            "🎯 请选择您要进行的操作:",
            choices=[
                first_item,
                "📖 2. 扩展成一段话主题 - 将主题扩展为详细描述", 
                "🌍 3. 世界设定 - 构建角色、场景和道具",
                "📋 4. 编辑故事大纲 - 规划整体故事结构",
                "📚 5. 编辑分章细纲 - 细化每章内容安排",
                "📄 6. 编辑章节概要 - 生成章节摘要",
                "📜 7. 生成小说正文 - AI辅助创作正文",
                "🔧 8. 系统设置 - 配置系统参数",
                "🔙 9. 返回项目管理 - 切换或管理项目"
            ],
            use_indicator=True,
            style=questionary.Style([
                ('question', 'bold fg:#ff00ff'),
                ('answer', 'fg:#ff9d00 bold'),
                ('pointer', 'fg:#ff9d00 bold'),
                ('highlighted', 'fg:#ff9d00 bold'),
                ('selected', 'fg:#cc5454'),
                ('separator', 'fg:#cc5454'),
                ('instruction', 'fg:#888888'),
                ('text', ''),
                ('disabled', 'fg:#858585 italic')
            ])
        ).ask()

        if choice is None or choice.startswith("🔙"):
            break
        
        if choice.startswith("📝"):
            handle_theme_one_line()
        elif choice.startswith("📖"):
            handle_theme_paragraph()
        elif choice.startswith("🌍"):
            handle_world_setting()
        elif choice.startswith("📋"):
            handle_story_outline()
        elif choice.startswith("📚"):
            handle_chapter_outline()
        elif choice.startswith("📄"):
            handle_chapter_summary()
        elif choice.startswith("📜"):
            handle_novel_generation()
        elif choice.startswith("🔧"):
            handle_system_settings()
        else:
            print(f"您选择了: {choice} (功能开发中...)\n")

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
        choice = questionary.select(
            "🚀 MetaNovel Engine - 主菜单",
            choices=[
                "📁 项目管理 - 管理和切换小说项目",
                "🔧 系统设置 - 配置系统参数",
                "👋 退出 - 结束程序"
            ],
            use_indicator=True,
            style=questionary.Style([
                ('question', 'bold fg:#ff00ff'),
                ('answer', 'fg:#ff9d00 bold'),
                ('pointer', 'fg:#ff9d00 bold'),
                ('highlighted', 'fg:#ff9d00 bold'),
                ('selected', 'fg:#cc5454'),
                ('separator', 'fg:#cc5454'),
                ('instruction', 'fg:#888888'),
                ('text', ''),
                ('disabled', 'fg:#858585 italic')
            ])
        ).ask()

        if choice is None or choice.startswith("👋"):
            console.clear()
            ui.print_goodbye()
            break
        elif choice.startswith("📁"):
            handle_project_management()
        elif choice.startswith("🔧"):
            handle_system_settings()
        else:
            print(f"您选择了: {choice} (功能开发中...)\n")


if __name__ == "__main__":
    main()
