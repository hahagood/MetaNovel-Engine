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
from data_manager import data_manager
from progress_utils import AsyncProgressManager, run_with_progress
from retry_utils import batch_retry_manager
from config import RETRY_CONFIG
from entity_manager import handle_characters, handle_locations, handle_items
from ui_utils import ui, console
from rich.panel import Panel
from rich.text import Text

# --- Helper Functions ---
def ensure_meta_dir():
    """Ensures the meta directory exists."""
    # 现在由data_manager自动处理
    pass



def handle_theme_one_line():
    """Handles creating or updating the one-sentence theme."""
    ensure_meta_dir()
    
    current_theme = data_manager.read_theme_one_line()
    if current_theme:
        print(f"当前主题: {current_theme}")

    new_theme = questionary.text(
        "请输入您的一句话主题:",
        default=current_theme
    ).ask()

    if new_theme is not None and new_theme.strip() and new_theme != current_theme:
        if data_manager.write_theme_one_line(new_theme):
            print(f"主题已更新为: {new_theme}\n")
        else:
            print("保存主题时出错。\n")
    elif new_theme is None:
        print("操作已取消。\n")
    else:
        print("主题未更改。\n")


def handle_theme_paragraph():
    """Handles creating or updating the paragraph-long theme using an LLM."""
    ensure_meta_dir()

    # 首先检查一句话主题是否存在
    one_line_theme = data_manager.read_theme_one_line()
    if not one_line_theme:
        print("\n请先使用选项 [1] 确立一句话主题。")
        return

    # 检查是否已有段落主题
    existing_paragraph = data_manager.read_theme_paragraph()

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
                if data_manager.write_theme_paragraph(edited_paragraph):
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
    if not one_line_theme:
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
        if data_manager.write_theme_paragraph(generated_paragraph):
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
            if data_manager.write_theme_paragraph(edited_paragraph):
                print("段落主题已保存。\n")
            else:
                print("保存段落主题时出错。\n")
        else:
            print("操作已取消或内容为空，未保存。\n")


def handle_world_setting():
    """Handles world setting management including characters, locations, and items."""
    ensure_meta_dir()
    
    # 检查前置条件
    one_line_exists, paragraph_exists = data_manager.check_prerequisites_for_world_setting()
    
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
    one_line_exists, paragraph_exists = data_manager.check_prerequisites_for_story_outline()
    
    if not one_line_exists or not paragraph_exists:
        print("\n请先完成前面的步骤：")
        if not one_line_exists:
            print("- 步骤1: 确立一句话主题")
        if not paragraph_exists:
            print("- 步骤2: 扩展成一段话主题")
        print()
        return
    
    # 读取现有大纲数据
    current_outline = data_manager.read_story_outline()
    
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
            return
        elif action.startswith("1."):
            print("\n--- 完整故事大纲 ---")
            print(current_outline)
            print("------------------------\n")
            return
        elif action.startswith("2."):
            edit_outline()
            return
        elif action.startswith("3."):
            print("\n正在重新生成故事大纲...")
        else:
            return
    else:
        print("\n当前没有故事大纲，让我们来生成一个。\n")
    
    # 生成新的故事大纲
    generate_story_outline()


def generate_story_outline():
    """Generate a new story outline based on existing themes and characters."""
    # 读取主题信息
    one_line_theme = data_manager.read_theme_one_line()
    paragraph_theme = data_manager.read_theme_paragraph()
    
    # 读取角色信息（如果有的话）
    characters_info = data_manager.get_characters_info_string()
    
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
        if data_manager.write_story_outline(generated_outline):
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
            if data_manager.write_story_outline(edited_outline):
                print("故事大纲已保存。\n")
            else:
                print("保存故事大纲时出错。\n")
        else:
            print("操作已取消或内容为空，未保存。\n")


def edit_outline():
    """Edit existing story outline."""
    current_outline = data_manager.read_story_outline()
    print("\n--- 当前故事大纲 ---")
    print(current_outline)
    print("------------------------\n")
    
    edited_outline = questionary.text(
        "请修改故事大纲:",
        default=current_outline,
        multiline=True
    ).ask()
    
    if edited_outline and edited_outline.strip() and edited_outline != current_outline:
        if data_manager.write_story_outline(edited_outline):
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
    story_outline_exists = data_manager.check_prerequisites_for_chapter_outline()
    
    if not story_outline_exists:
        print("\n请先完成步骤4: 编辑故事大纲\n")
        return
    
    while True:
        # 每次循环都重新读取数据
        chapters = data_manager.read_chapter_outline()
        
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
    story_outline = data_manager.read_story_outline()
    one_line_theme = data_manager.read_theme_one_line()
    characters_info = data_manager.get_characters_info_string()
    
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
    chapters = chapter_outline_data.get('chapters', [])
    for i, chapter in enumerate(chapters, 1):
        print(f"\n第{i}章: {chapter.get('title', '无标题')}")
        print(f"大纲: {chapter.get('outline', '无大纲')}")
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
        chapters_list = chapter_outline_data.get('chapters', [])
        if data_manager.write_chapter_outline(chapters_list):
            print("分章细纲已保存。\n")
        else:
            print("保存分章细纲时出错。\n")
    elif action.startswith("2."):
        # 修改后保存（这里可以让用户逐个修改章节）
        print("请逐个确认或修改每个章节：\n")
        modified_chapters = []
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
        
        if modified_chapters:
            if data_manager.write_chapter_outline(modified_chapters):
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
    
    chapters = data_manager.read_chapter_outline()
    chapters.append(new_chapter)
    
    if data_manager.write_chapter_outline(chapters):
        print(f"章节 '{title}' 已添加。\n")
    else:
        print("添加章节时出错。\n")


def view_chapter():
    """View chapter details."""
    chapters = data_manager.read_chapter_outline()
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
    chapters = data_manager.read_chapter_outline()
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
    if data_manager.write_chapter_outline(chapters):
        print("章节信息已更新。\n")
    else:
        print("更新章节信息时出错。\n")


def delete_chapter():
    """Delete a chapter."""
    chapters = data_manager.read_chapter_outline()
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
        if data_manager.write_chapter_outline(chapters):
            print(f"章节 '{chapter_title}' 已删除。\n")
        else:
            print("删除章节时出错。\n")
    else:
        print("操作已取消。\n")


def handle_chapter_summary():
    """Handles chapter summary management with full CRUD operations."""
    ensure_meta_dir()
    
    # 检查前置条件
    chapter_outline_exists = data_manager.check_prerequisites_for_chapter_summary()
    
    if not chapter_outline_exists:
        print("\n请先完成步骤5: 编辑分章细纲\n")
        return
    
    # 读取分章细纲
    chapters = data_manager.read_chapter_outline()
    
    if not chapters:
        print("\n分章细纲为空，请先完成步骤5。\n")
        return
    
    while True:
        # 每次循环都重新读取数据
        summaries = data_manager.read_chapter_summaries()
        
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
    context_info = data_manager.get_context_info()
    
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
                    if data_manager.write_chapter_summaries(results):
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
            if data_manager.write_chapter_summaries(summaries):
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
    summaries = data_manager.read_chapter_summaries()
    
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
    context_info = data_manager.get_context_info()
    
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
            if data_manager.set_chapter_summary(chapter_num, chapter.get('title', f'第{chapter_num}章'), summary):
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
                if data_manager.set_chapter_summary(chapter_num, chapter.get('title', f'第{chapter_num}章'), edited_summary):
                    print(f"第{chapter_num}章概要已保存。\n")
                else:
                    print("保存章节概要时出错。\n")
            else:
                print("操作已取消或内容为空，未保存。\n")
    else:
        print(f"第{chapter_num}章概要生成失败。\n")





def view_chapter_summary(chapters):
    """View chapter summary details."""
    summaries = data_manager.read_chapter_summaries()
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
    summaries = data_manager.read_chapter_summaries()
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
        if data_manager.set_chapter_summary(chapter_num, summary_info['title'], edited_summary):
            print(f"第{chapter_num}章概要已更新。\n")
        else:
            print("更新章节概要时出错。\n")
    elif edited_summary is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def delete_chapter_summary(chapters):
    """Delete chapter summary."""
    summaries = data_manager.read_chapter_summaries()
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
        if data_manager.delete_chapter_summary(chapter_num):
            print(f"第{chapter_num}章概要已删除。\n")
        else:
            print("删除章节概要时出错。\n")
    else:
        print("操作已取消。\n")


def handle_novel_generation():
    """Handles novel text generation with full management operations."""
    ensure_meta_dir()
    
    # 检查前置条件
    chapter_summary_exists = data_manager.check_prerequisites_for_novel_generation()
    
    if not chapter_summary_exists:
        print("\n请先完成步骤6: 编辑章节概要\n")
        return
    
    # 读取章节概要
    summaries = data_manager.read_chapter_summaries()
    
    if not summaries:
        print("\n章节概要为空，请先完成步骤6。\n")
        return
    
    # 读取分章细纲以获取章节顺序
    chapters = data_manager.read_chapter_outline()
    
    while True:
        # 每次循环都重新读取数据
        novel_chapters = data_manager.read_novel_chapters()
        
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
            "6. 导出完整小说",
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
            # 导出完整小说
            export_complete_novel(chapters, novel_chapters)


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
    context_info = data_manager.get_context_info()
    
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
                    if data_manager.write_novel_chapters(results):
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
            if data_manager.write_novel_chapters(novel_chapters):
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
    context_info = data_manager.get_context_info()
    
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
            if data_manager.set_novel_chapter(chapter_num, chapter.get('title', f'第{chapter_num}章'), chapter_content):
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
                if data_manager.set_novel_chapter(chapter_num, chapter.get('title', f'第{chapter_num}章'), edited_content):
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
        if data_manager.set_novel_chapter(chapter_num, chapter_info['title'], edited_content):
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
        if data_manager.delete_novel_chapter(chapter_num):
            print(f"第{chapter_num}章正文已删除。\n")
        else:
            print("删除章节正文时出错。\n")
    else:
        print("操作已取消。\n")


def export_complete_novel(chapters, novel_data):
    """Export complete novel to a text file."""
    novel_chapters = novel_data.get('chapters', {})
    if not novel_chapters:
        print("\n当前没有小说正文可导出。\n")
        return
    
    # 获取小说名（基于主题）
    novel_name = "未命名小说"
    try:
        with FILE_PATHS["theme_one_line"].open('r', encoding='utf-8') as f:
            theme_data = json.load(f)
            theme = theme_data.get("theme", "")
            if theme:
                # 清理主题作为文件名，移除特殊字符
                import re
                novel_name = re.sub(r'[<>:"/\\|?*]', '_', theme)
                # 限制长度
                if len(novel_name) > 20:
                    novel_name = novel_name[:20] + "..."
    except:
        pass
    
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


def show_project_status():
    """显示项目完成状态"""
    # 检查各个步骤的完成情况
    completion_status = {
        "theme_one_line": bool(data_manager.read_theme_one_line()),
        "theme_paragraph": bool(data_manager.read_theme_paragraph()),
        "world_settings": bool(data_manager.read_characters() or data_manager.read_locations() or data_manager.read_items()),
        "story_outline": bool(data_manager.read_story_outline()),
        "chapter_outline": bool(data_manager.read_chapter_outline()),
        "chapter_summaries": bool(data_manager.read_chapter_summaries()),
        "novel_chapters": bool(data_manager.read_novel_chapters())
    }
    
    ui.print_project_status(completion_status)


def create_beautiful_menu():
    """创建美化的主菜单"""
    # 菜单选项
    menu_options = [
        ("📝", "1. 确立一句话主题", "开始您的创作之旅"),
        ("📖", "2. 扩展成一段话主题", "将主题扩展为详细描述"),
        ("🌍", "3. 世界设定", "构建角色、场景和道具"),
        ("📋", "4. 编辑故事大纲", "规划整体故事结构"),
        ("📚", "5. 编辑分章细纲", "细化每章内容安排"),
        ("📄", "6. 编辑章节概要", "生成章节摘要"),
        ("✍️", "7. 生成小说正文", "AI辅助创作正文"),
        ("⚙️", "8. 系统设置", "配置系统参数"),
        ("👋", "9. 退出", "结束本次创作")
    ]
    
    # 创建美化的菜单面板
    menu_content = []
    for emoji, option, description in menu_options:
        menu_content.append(f"{emoji} [bold cyan]{option}[/bold cyan]")
        menu_content.append(f"   [dim]{description}[/dim]")
        menu_content.append("")  # 空行
    
    # 移除最后的空行
    if menu_content:
        menu_content.pop()
    
    menu_panel = Panel(
        "\n".join(menu_content),
        title="🎯 [bold magenta]创作菜单[/bold magenta]",
        subtitle="[dim]使用方向键选择，回车确认[/dim]",
        style="bright_blue",
        padding=(1, 2)
    )
    
    console.print(menu_panel)


def main():
    """
    Main function to display the interactive menu.
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
        
        # 显示项目状态
        show_project_status()
        console.print()  # 空行
        
        # 显示美化的菜单
        create_beautiful_menu()
        console.print()  # 空行
        
        # 使用questionary选择
        choice = questionary.select(
            "请选择您要进行的操作:",
            choices=[
                "1. 确立一句话主题",
                "2. 扩展成一段话主题",
                "3. 世界设定",
                "4. 编辑故事大纲",
                "5. 编辑分章细纲",
                "6. 编辑章节概要",
                "7. 生成小说正文",
                "8. 系统设置",
                "9. 退出"
            ],
            use_indicator=True,
            style=questionary.Style([
                ('question', 'bold'),
                ('answer', 'fg:#ff9d00 bold'),
                ('pointer', 'fg:#ff9d00 bold'),
                ('highlighted', 'fg:#ff9d00 bold'),
                ('selected', 'fg:#cc5454'),
                ('separator', 'fg:#cc5454'),
                ('instruction', ''),
                ('text', ''),
                ('disabled', 'fg:#858585 italic')
            ])
        ).ask()

        if choice is None or choice.endswith("退出"):
            console.clear()
            ui.print_goodbye()
            break
        
        if choice.startswith("1."):
            handle_theme_one_line()
        elif choice.startswith("2."):
            handle_theme_paragraph()
        elif choice.startswith("3."):
            handle_world_setting()
        elif choice.startswith("4."):
            handle_story_outline()
        elif choice.startswith("5."):
            handle_chapter_outline()
        elif choice.startswith("6."):
            handle_chapter_summary()
        elif choice.startswith("7."):
            handle_novel_generation()
        elif choice.startswith("8."):
            handle_system_settings()
        else:
            print(f"您选择了: {choice} (功能开发中...)\n")


if __name__ == "__main__":
    main()
