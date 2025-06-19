import os
import sys

# --- Force Python's HTTP libraries to use a proxy ---
# This must be done BEFORE importing openai or other network libraries.
PROXY_URL = "http://127.0.0.1:8118"
os.environ['http_proxy'] = PROXY_URL
os.environ['https_proxy'] = PROXY_URL
# ----------------------------------------------------

import questionary
import json
from pathlib import Path
import os
from openai import OpenAI, APIStatusError

# --- Constants ---
META_DIR = Path("meta")
OPENROUTER_MODEL = "google/gemini-2.5-pro-preview-06-05" # 可以替换为任何 OpenRouter 支持的模型

# --- Helper Functions ---
def ensure_meta_dir():
    """Ensures the meta directory exists."""
    META_DIR.mkdir(exist_ok=True)

def configure_llm():
    """Configures the generative AI model, checking for the API key."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("\n错误: 找不到 OPENROUTER_API_KEY 环境变量。")
        print("请确保您已在环境中正确设置了您的 OpenRouter API 密钥。")
        return None
    try:
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        )
        return client
    except Exception as e:
        print(f"\n初始化大语言模型时出错: {e}")
        return None

def handle_theme_one_line():
    """Handles creating or updating the one-sentence theme."""
    ensure_meta_dir()
    target_path = META_DIR / "theme_one_line.json"
    
    current_theme = ""
    if target_path.exists():
        try:
            with target_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                current_theme = data.get("theme", "")
            if current_theme:
                print(f"当前主题: {current_theme}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"无法读取现有主题文件: {e}")

    new_theme = questionary.text(
        "请输入您的一句话主题:",
        default=current_theme
    ).ask()

    if new_theme is not None and new_theme.strip() and new_theme != current_theme:
        data = {"theme": new_theme}
        with target_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"主题已更新为: {new_theme}\n")
    elif new_theme is None:
        print("操作已取消。\n")
    else:
        print("主题未更改。\n")


def handle_theme_paragraph():
    """Handles creating or updating the paragraph-long theme using an LLM."""
    ensure_meta_dir()
    one_line_theme_path = META_DIR / "theme_one_line.json"
    paragraph_theme_path = META_DIR / "theme_paragraph.json"

    # 首先检查一句话主题是否存在
    if not one_line_theme_path.exists():
        print("\n请先使用选项 [1] 确立一句话主题。")
        return

    # 检查是否已有段落主题
    existing_paragraph = ""
    if paragraph_theme_path.exists():
        try:
            with paragraph_theme_path.open('r', encoding='utf-8') as f:
                data = json.load(f)
                existing_paragraph = data.get("theme_paragraph", "").strip()
        except (json.JSONDecodeError, IOError):
            pass  # 如果文件损坏或无法读取，就重新生成

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
                data = {"theme_paragraph": edited_paragraph}
                with paragraph_theme_path.open('w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                print("段落主题已更新。\n")
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
    with one_line_theme_path.open('r', encoding='utf-8') as f:
        one_line_data = json.load(f)
        one_line_theme = one_line_data.get("theme")
        if not one_line_theme:
            print("\n一句话主题文件为空，请先使用选项 [1] 确立主题。")
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

    llm = configure_llm()
    if not llm:
        return

    # 构建完整的提示词
    base_prompt = f"请将以下这个一句话小说主题，扩展成一段更加具体、包含更多情节可能性的段落大纲，字数在200字左右。请直接输出扩写后的段落，不要包含额外说明和标题。\n\n一句话主题：{one_line_theme}"
    
    if user_prompt.strip():
        full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        print(f"用户指导：{user_prompt.strip()}")
    else:
        full_prompt = base_prompt
    
    print("正在调用 AI 生成段落主题，请稍候...")
    try:
        completion = llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            timeout=60,
        )
        generated_paragraph = completion.choices[0].message.content
    except APIStatusError as e:
        print(f"\n错误: 调用 API 时出错 (状态码: {e.status_code})")
        if e.status_code == 429:
             print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
        else:
            print(f"详细信息: {e.response.text}")
        return
    except Exception as e:
        print(f"\n调用 AI 时出错: {e}")
        if "Timeout" in str(e) or "timed out" in str(e):
             print("\n错误：请求超时。")
             print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
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
        data = {"theme_paragraph": generated_paragraph}
        with paragraph_theme_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("段落主题已保存。\n")
    elif action.startswith("2."):
        # 修改后保存
        edited_paragraph = questionary.text(
            "请修改您的段落主题:",
            default=generated_paragraph,
            multiline=True
        ).ask()

        if edited_paragraph and edited_paragraph.strip():
            data = {"theme_paragraph": edited_paragraph}
            with paragraph_theme_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print("段落主题已保存。\n")
        else:
            print("操作已取消或内容为空，未保存。\n")


def handle_world_setting():
    """Handles world setting management including characters, locations, and items."""
    ensure_meta_dir()
    
    # 检查前置条件
    one_line_theme_path = META_DIR / "theme_one_line.json"
    paragraph_theme_path = META_DIR / "theme_paragraph.json"
    
    if not one_line_theme_path.exists() or not paragraph_theme_path.exists():
        print("\n请先完成前面的步骤：")
        if not one_line_theme_path.exists():
            print("- 步骤1: 确立一句话主题")
        if not paragraph_theme_path.exists():
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


def handle_characters():
    """Handles character management with full CRUD operations."""
    ensure_meta_dir()
    characters_path = META_DIR / "characters.json"
    
    # 读取现有角色数据
    characters_data = {}
    if characters_path.exists():
        try:
            with characters_path.open('r', encoding='utf-8') as f:
                characters_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            characters_data = {}
    
    while True:
        # 显示当前角色列表
        if characters_data:
            print("\n--- 当前角色列表 ---")
            for i, (char_name, char_info) in enumerate(characters_data.items(), 1):
                print(f"{i}. {char_name}: {char_info.get('description', '无描述')[:50]}{'...' if len(char_info.get('description', '')) > 50 else ''}")
            print("------------------------\n")
        else:
            print("\n当前没有角色信息。\n")
        
        # 操作选项
        choices = [
            "1. 添加新角色",
            "2. 查看角色详情",
            "3. 修改角色信息", 
            "4. 删除角色",
            "5. 返回上级菜单"
        ]
        
        if not characters_data:
            # 如果没有角色，隐藏查看、修改、删除选项
            choices = [
                "1. 添加新角色",
                "2. 返回上级菜单"
            ]
        
        action = questionary.select(
            "请选择您要进行的操作：",
            choices=choices,
            use_indicator=True
        ).ask()
        
        if action is None:
            break
        elif action.startswith("1."):
            # 添加新角色
            add_character(characters_data, characters_path)
        elif action.startswith("2.") and characters_data:
            # 查看角色详情
            view_character(characters_data)
        elif action.startswith("2.") and not characters_data:
            # 返回上级菜单（当没有角色时）
            break
        elif action.startswith("3."):
            # 修改角色信息
            edit_character(characters_data, characters_path)
        elif action.startswith("4."):
            # 删除角色
            delete_character(characters_data, characters_path)
        elif action.startswith("5.") or action.startswith("2."):
            # 返回上级菜单
            break


def handle_locations():
    """Handles location/scene management with full CRUD operations."""
    ensure_meta_dir()
    locations_path = META_DIR / "locations.json"
    
    # 读取现有场景数据
    locations_data = {}
    if locations_path.exists():
        try:
            with locations_path.open('r', encoding='utf-8') as f:
                locations_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            locations_data = {}
    
    while True:
        # 显示当前场景列表
        if locations_data:
            print("\n--- 当前场景列表 ---")
            for i, (loc_name, loc_info) in enumerate(locations_data.items(), 1):
                print(f"{i}. {loc_name}: {loc_info.get('description', '无描述')[:50]}{'...' if len(loc_info.get('description', '')) > 50 else ''}")
            print("------------------------\n")
        else:
            print("\n当前没有场景信息。\n")
        
        # 操作选项
        choices = [
            "1. 添加新场景",
            "2. 查看场景详情",
            "3. 修改场景信息", 
            "4. 删除场景",
            "5. 返回上级菜单"
        ]
        
        if not locations_data:
            # 如果没有场景，隐藏查看、修改、删除选项
            choices = [
                "1. 添加新场景",
                "2. 返回上级菜单"
            ]
        
        action = questionary.select(
            "请选择您要进行的操作：",
            choices=choices,
            use_indicator=True
        ).ask()
        
        if action is None:
            break
        elif action.startswith("1."):
            # 添加新场景
            add_location(locations_data, locations_path)
        elif action.startswith("2.") and locations_data:
            # 查看场景详情
            view_location(locations_data)
        elif action.startswith("2.") and not locations_data:
            # 返回上级菜单（当没有场景时）
            break
        elif action.startswith("3."):
            # 修改场景信息
            edit_location(locations_data, locations_path)
        elif action.startswith("4."):
            # 删除场景
            delete_location(locations_data, locations_path)
        elif action.startswith("5.") or action.startswith("2."):
            # 返回上级菜单
            break


def handle_items():
    """Handles item/prop management with full CRUD operations."""
    ensure_meta_dir()
    items_path = META_DIR / "items.json"
    
    # 读取现有道具数据
    items_data = {}
    if items_path.exists():
        try:
            with items_path.open('r', encoding='utf-8') as f:
                items_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            items_data = {}
    
    while True:
        # 显示当前道具列表
        if items_data:
            print("\n--- 当前道具列表 ---")
            for i, (item_name, item_info) in enumerate(items_data.items(), 1):
                print(f"{i}. {item_name}: {item_info.get('description', '无描述')[:50]}{'...' if len(item_info.get('description', '')) > 50 else ''}")
            print("------------------------\n")
        else:
            print("\n当前没有道具信息。\n")
        
        # 操作选项
        choices = [
            "1. 添加新道具",
            "2. 查看道具详情",
            "3. 修改道具信息", 
            "4. 删除道具",
            "5. 返回上级菜单"
        ]
        
        if not items_data:
            # 如果没有道具，隐藏查看、修改、删除选项
            choices = [
                "1. 添加新道具",
                "2. 返回上级菜单"
            ]
        
        action = questionary.select(
            "请选择您要进行的操作：",
            choices=choices,
            use_indicator=True
        ).ask()
        
        if action is None:
            break
        elif action.startswith("1."):
            # 添加新道具
            add_item(items_data, items_path)
        elif action.startswith("2.") and items_data:
            # 查看道具详情
            view_item(items_data)
        elif action.startswith("2.") and not items_data:
            # 返回上级菜单（当没有道具时）
            break
        elif action.startswith("3."):
            # 修改道具信息
            edit_item(items_data, items_path)
        elif action.startswith("4."):
            # 删除道具
            delete_item(items_data, items_path)
        elif action.startswith("5.") or action.startswith("2."):
            # 返回上级菜单
            break


def add_character(characters_data, characters_path):
    """Add a new character."""
    char_name = questionary.text("请输入角色名称:").ask()
    if not char_name or not char_name.strip():
        print("角色名称不能为空。\n")
        return
    
    char_name = char_name.strip()
    if char_name in characters_data:
        print(f"角色 '{char_name}' 已存在。\n")
        return
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成角色描述。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    # 如果用户不想继续，提供确认选项
    if not user_prompt.strip():
        confirm = questionary.confirm("确定要继续生成角色描述吗？").ask()
        if not confirm:
            print("操作已取消。\n")
            return

    llm = configure_llm()
    if not llm:
        return

    # 构建提示词
    base_prompt = f"请为小说角色 '{char_name}' 创建一个详细的角色描述，包括外貌特征、性格特点、背景故事、能力特长等方面，字数在150-200字左右。请直接输出角色描述，不要包含额外说明和标题。"
    
    if user_prompt.strip():
        full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        print(f"用户指导：{user_prompt.strip()}")
    else:
        full_prompt = base_prompt
    
    print("正在调用 AI 生成角色描述，请稍候...")
    try:
        completion = llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            timeout=60,
        )
        generated_description = completion.choices[0].message.content
    except APIStatusError as e:
        print(f"\n错误: 调用 API 时出错 (状态码: {e.status_code})")
        if e.status_code == 429:
             print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
        else:
            print(f"详细信息: {e.response.text}")
        return
    except Exception as e:
        print(f"\n调用 AI 时出错: {e}")
        if "Timeout" in str(e) or "timed out" in str(e):
             print("\n错误：请求超时。")
             print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
        return

    print(f"\n--- AI 生成的角色描述：{char_name} ---")
    print(generated_description)
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
        characters_data[char_name] = {"description": generated_description}
        save_characters_data(characters_data, characters_path)
        print(f"角色 '{char_name}' 已保存。\n")
    elif action.startswith("2."):
        # 修改后保存
        edited_description = questionary.text(
            "请修改角色描述:",
            default=generated_description,
            multiline=True
        ).ask()

        if edited_description and edited_description.strip():
            characters_data[char_name] = {"description": edited_description}
            save_characters_data(characters_data, characters_path)
            print(f"角色 '{char_name}' 已保存。\n")
        else:
            print("操作已取消或内容为空，未保存。\n")


def view_character(characters_data):
    """View character details."""
    char_names = list(characters_data.keys())
    char_name = questionary.select(
        "请选择要查看的角色：",
        choices=char_names,
        use_indicator=True
    ).ask()
    
    if char_name:
        char_info = characters_data[char_name]
        print(f"\n--- 角色详情：{char_name} ---")
        print(char_info.get('description', '无描述'))
        print("------------------------\n")


def edit_character(characters_data, characters_path):
    """Edit character information."""
    char_names = list(characters_data.keys())
    char_name = questionary.select(
        "请选择要修改的角色：",
        choices=char_names,
        use_indicator=True
    ).ask()
    
    if not char_name:
        return
    
    current_description = characters_data[char_name].get('description', '')
    print(f"\n--- 当前角色描述：{char_name} ---")
    print(current_description)
    print("------------------------\n")
    
    edited_description = questionary.text(
        "请修改角色描述:",
        default=current_description,
        multiline=True
    ).ask()
    
    if edited_description and edited_description.strip() and edited_description != current_description:
        characters_data[char_name]['description'] = edited_description
        save_characters_data(characters_data, characters_path)
        print(f"角色 '{char_name}' 已更新。\n")
    elif edited_description is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def delete_character(characters_data, characters_path):
    """Delete a character."""
    char_names = list(characters_data.keys())
    char_name = questionary.select(
        "请选择要删除的角色：",
        choices=char_names,
        use_indicator=True
    ).ask()
    
    if not char_name:
        return
    
    confirm = questionary.confirm(f"确定要删除角色 '{char_name}' 吗？").ask()
    if confirm:
        del characters_data[char_name]
        save_characters_data(characters_data, characters_path)
        print(f"角色 '{char_name}' 已删除。\n")
    else:
        print("操作已取消。\n")


def save_characters_data(characters_data, characters_path):
    """Save characters data to file."""
    with characters_path.open('w', encoding='utf-8') as f:
        json.dump(characters_data, f, ensure_ascii=False, indent=4)


# ===== 场景管理函数 =====

def add_location(locations_data, locations_path):
    """Add a new location/scene."""
    loc_name = questionary.text("请输入场景名称:").ask()
    if not loc_name or not loc_name.strip():
        print("场景名称不能为空。\n")
        return
    
    loc_name = loc_name.strip()
    if loc_name in locations_data:
        print(f"场景 '{loc_name}' 已存在。\n")
        return
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成场景描述。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    # 如果用户不想继续，提供确认选项
    if not user_prompt.strip():
        confirm = questionary.confirm("确定要继续生成场景描述吗？").ask()
        if not confirm:
            print("操作已取消。\n")
            return

    llm = configure_llm()
    if not llm:
        return

    # 构建提示词
    base_prompt = f"请为小说场景 '{loc_name}' 创建一个详细的场景描述，包括地理位置、环境特色、建筑风格、氛围感受、历史背景、重要特征等方面，字数在150-200字左右。请直接输出场景描述，不要包含额外说明和标题。"
    
    if user_prompt.strip():
        full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        print(f"用户指导：{user_prompt.strip()}")
    else:
        full_prompt = base_prompt
    
    print("正在调用 AI 生成场景描述，请稍候...")
    try:
        completion = llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            timeout=60,
        )
        generated_description = completion.choices[0].message.content
    except APIStatusError as e:
        print(f"\n错误: 调用 API 时出错 (状态码: {e.status_code})")
        if e.status_code == 429:
             print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
        else:
            print(f"详细信息: {e.response.text}")
        return
    except Exception as e:
        print(f"\n调用 AI 时出错: {e}")
        if "Timeout" in str(e) or "timed out" in str(e):
             print("\n错误：请求超时。")
             print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
        return

    print(f"\n--- AI 生成的场景描述：{loc_name} ---")
    print(generated_description)
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
        locations_data[loc_name] = {"description": generated_description}
        save_locations_data(locations_data, locations_path)
        print(f"场景 '{loc_name}' 已保存。\n")
    elif action.startswith("2."):
        # 修改后保存
        edited_description = questionary.text(
            "请修改场景描述:",
            default=generated_description,
            multiline=True
        ).ask()

        if edited_description and edited_description.strip():
            locations_data[loc_name] = {"description": edited_description}
            save_locations_data(locations_data, locations_path)
            print(f"场景 '{loc_name}' 已保存。\n")
        else:
            print("操作已取消或内容为空，未保存。\n")


def view_location(locations_data):
    """View location details."""
    loc_names = list(locations_data.keys())
    loc_name = questionary.select(
        "请选择要查看的场景：",
        choices=loc_names,
        use_indicator=True
    ).ask()
    
    if loc_name:
        loc_info = locations_data[loc_name]
        print(f"\n--- 场景详情：{loc_name} ---")
        print(loc_info.get('description', '无描述'))
        print("------------------------\n")


def edit_location(locations_data, locations_path):
    """Edit location information."""
    loc_names = list(locations_data.keys())
    loc_name = questionary.select(
        "请选择要修改的场景：",
        choices=loc_names,
        use_indicator=True
    ).ask()
    
    if not loc_name:
        return
    
    current_description = locations_data[loc_name].get('description', '')
    print(f"\n--- 当前场景描述：{loc_name} ---")
    print(current_description)
    print("------------------------\n")
    
    edited_description = questionary.text(
        "请修改场景描述:",
        default=current_description,
        multiline=True
    ).ask()
    
    if edited_description and edited_description.strip() and edited_description != current_description:
        locations_data[loc_name]['description'] = edited_description
        save_locations_data(locations_data, locations_path)
        print(f"场景 '{loc_name}' 已更新。\n")
    elif edited_description is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def delete_location(locations_data, locations_path):
    """Delete a location."""
    loc_names = list(locations_data.keys())
    loc_name = questionary.select(
        "请选择要删除的场景：",
        choices=loc_names,
        use_indicator=True
    ).ask()
    
    if not loc_name:
        return
    
    confirm = questionary.confirm(f"确定要删除场景 '{loc_name}' 吗？").ask()
    if confirm:
        del locations_data[loc_name]
        save_locations_data(locations_data, locations_path)
        print(f"场景 '{loc_name}' 已删除。\n")
    else:
        print("操作已取消。\n")


def save_locations_data(locations_data, locations_path):
    """Save locations data to file."""
    with locations_path.open('w', encoding='utf-8') as f:
        json.dump(locations_data, f, ensure_ascii=False, indent=4)


# ===== 道具管理函数 =====

def add_item(items_data, items_path):
    """Add a new item/prop."""
    item_name = questionary.text("请输入道具名称:").ask()
    if not item_name or not item_name.strip():
        print("道具名称不能为空。\n")
        return
    
    item_name = item_name.strip()
    if item_name in items_data:
        print(f"道具 '{item_name}' 已存在。\n")
        return
    
    # 获取用户自定义提示词
    print("您可以输入额外的要求或指导来影响AI生成道具描述。")
    user_prompt = questionary.text(
        "请输入您的额外要求或指导（直接回车跳过）:",
        default=""
    ).ask()

    if user_prompt is None:
        print("操作已取消。\n")
        return
    
    # 如果用户不想继续，提供确认选项
    if not user_prompt.strip():
        confirm = questionary.confirm("确定要继续生成道具描述吗？").ask()
        if not confirm:
            print("操作已取消。\n")
            return

    llm = configure_llm()
    if not llm:
        return

    # 构建提示词
    base_prompt = f"请为小说道具 '{item_name}' 创建一个详细的道具描述，包括外观特征、材质工艺、功能用途、历史来源、特殊能力、重要意义等方面，字数在150-200字左右。请直接输出道具描述，不要包含额外说明和标题。"
    
    if user_prompt.strip():
        full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        print(f"用户指导：{user_prompt.strip()}")
    else:
        full_prompt = base_prompt
    
    print("正在调用 AI 生成道具描述，请稍候...")
    try:
        completion = llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            timeout=60,
        )
        generated_description = completion.choices[0].message.content
    except APIStatusError as e:
        print(f"\n错误: 调用 API 时出错 (状态码: {e.status_code})")
        if e.status_code == 429:
             print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
        else:
            print(f"详细信息: {e.response.text}")
        return
    except Exception as e:
        print(f"\n调用 AI 时出错: {e}")
        if "Timeout" in str(e) or "timed out" in str(e):
             print("\n错误：请求超时。")
             print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
        return

    print(f"\n--- AI 生成的道具描述：{item_name} ---")
    print(generated_description)
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
        items_data[item_name] = {"description": generated_description}
        save_items_data(items_data, items_path)
        print(f"道具 '{item_name}' 已保存。\n")
    elif action.startswith("2."):
        # 修改后保存
        edited_description = questionary.text(
            "请修改道具描述:",
            default=generated_description,
            multiline=True
        ).ask()

        if edited_description and edited_description.strip():
            items_data[item_name] = {"description": edited_description}
            save_items_data(items_data, items_path)
            print(f"道具 '{item_name}' 已保存。\n")
        else:
            print("操作已取消或内容为空，未保存。\n")


def view_item(items_data):
    """View item details."""
    item_names = list(items_data.keys())
    item_name = questionary.select(
        "请选择要查看的道具：",
        choices=item_names,
        use_indicator=True
    ).ask()
    
    if item_name:
        item_info = items_data[item_name]
        print(f"\n--- 道具详情：{item_name} ---")
        print(item_info.get('description', '无描述'))
        print("------------------------\n")


def edit_item(items_data, items_path):
    """Edit item information."""
    item_names = list(items_data.keys())
    item_name = questionary.select(
        "请选择要修改的道具：",
        choices=item_names,
        use_indicator=True
    ).ask()
    
    if not item_name:
        return
    
    current_description = items_data[item_name].get('description', '')
    print(f"\n--- 当前道具描述：{item_name} ---")
    print(current_description)
    print("------------------------\n")
    
    edited_description = questionary.text(
        "请修改道具描述:",
        default=current_description,
        multiline=True
    ).ask()
    
    if edited_description and edited_description.strip() and edited_description != current_description:
        items_data[item_name]['description'] = edited_description
        save_items_data(items_data, items_path)
        print(f"道具 '{item_name}' 已更新。\n")
    elif edited_description is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def delete_item(items_data, items_path):
    """Delete an item."""
    item_names = list(items_data.keys())
    item_name = questionary.select(
        "请选择要删除的道具：",
        choices=item_names,
        use_indicator=True
    ).ask()
    
    if not item_name:
        return
    
    confirm = questionary.confirm(f"确定要删除道具 '{item_name}' 吗？").ask()
    if confirm:
        del items_data[item_name]
        save_items_data(items_data, items_path)
        print(f"道具 '{item_name}' 已删除。\n")
    else:
        print("操作已取消。\n")


def save_items_data(items_data, items_path):
    """Save items data to file."""
    with items_path.open('w', encoding='utf-8') as f:
        json.dump(items_data, f, ensure_ascii=False, indent=4)


def handle_story_outline():
    """Handles story outline management with full CRUD operations."""
    ensure_meta_dir()
    outline_path = META_DIR / "story_outline.json"
    
    # 检查前置条件
    one_line_theme_path = META_DIR / "theme_one_line.json"
    paragraph_theme_path = META_DIR / "theme_paragraph.json"
    
    if not one_line_theme_path.exists() or not paragraph_theme_path.exists():
        print("\n请先完成前面的步骤：")
        if not one_line_theme_path.exists():
            print("- 步骤1: 确立一句话主题")
        if not paragraph_theme_path.exists():
            print("- 步骤2: 扩展成一段话主题")
        print()
        return
    
    # 读取现有大纲数据
    outline_data = {}
    if outline_path.exists():
        try:
            with outline_path.open('r', encoding='utf-8') as f:
                outline_data = json.load(f)
        except (json.JSONDecodeError, IOError):
            outline_data = {}
    
    # 显示当前大纲状态
    if outline_data and outline_data.get('outline'):
        print("\n--- 当前故事大纲 ---")
        outline_text = outline_data['outline']
        # 显示前200字符作为预览
        preview = outline_text[:200] + "..." if len(outline_text) > 200 else outline_text
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
            print(outline_data['outline'])
            print("------------------------\n")
            return
        elif action.startswith("2."):
            edit_outline(outline_data, outline_path)
            return
        elif action.startswith("3."):
            print("\n正在重新生成故事大纲...")
        else:
            return
    else:
        print("\n当前没有故事大纲，让我们来生成一个。\n")
    
    # 生成新的故事大纲
    generate_story_outline(outline_path)


def generate_story_outline(outline_path):
    """Generate a new story outline based on existing themes and characters."""
    # 读取主题信息
    one_line_theme_path = META_DIR / "theme_one_line.json"
    paragraph_theme_path = META_DIR / "theme_paragraph.json"
    characters_path = META_DIR / "characters.json"
    
    with one_line_theme_path.open('r', encoding='utf-8') as f:
        one_line_theme = json.load(f).get("theme", "")
    
    with paragraph_theme_path.open('r', encoding='utf-8') as f:
        paragraph_theme = json.load(f).get("theme_paragraph", "")
    
    # 读取角色信息（如果有的话）
    characters_info = ""
    if characters_path.exists():
        try:
            with characters_path.open('r', encoding='utf-8') as f:
                characters_data = json.load(f)
                if characters_data:
                    characters_info = "\n\n已有角色信息：\n"
                    for char_name, char_data in characters_data.items():
                        characters_info += f"- {char_name}: {char_data.get('description', '无描述')}\n"
        except (json.JSONDecodeError, IOError):
            pass
    
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

    llm = configure_llm()
    if not llm:
        return

    # 构建提示词
    base_prompt = f"""请基于以下信息创建一个详细的小说故事大纲：

一句话主题：{one_line_theme}

段落主题：{paragraph_theme}{characters_info}

请创建一个包含以下要素的完整故事大纲：
1. 故事背景设定
2. 主要情节线索
3. 关键转折点
4. 冲突与高潮
5. 结局方向

大纲应该详细具体，字数在500-800字左右。请直接输出故事大纲，不要包含额外说明和标题。"""
    
    if user_prompt.strip():
        full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        print(f"用户指导：{user_prompt.strip()}")
    else:
        full_prompt = base_prompt
    
    print("正在调用 AI 生成故事大纲，请稍候...")
    try:
        completion = llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            timeout=60,
        )
        generated_outline = completion.choices[0].message.content
    except APIStatusError as e:
        print(f"\n错误: 调用 API 时出错 (状态码: {e.status_code})")
        if e.status_code == 429:
             print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
        else:
            print(f"详细信息: {e.response.text}")
        return
    except Exception as e:
        print(f"\n调用 AI 时出错: {e}")
        if "Timeout" in str(e) or "timed out" in str(e):
             print("\n错误：请求超时。")
             print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
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
        outline_data = {"outline": generated_outline}
        save_outline_data(outline_data, outline_path)
        print("故事大纲已保存。\n")
    elif action.startswith("2."):
        # 修改后保存
        edited_outline = questionary.text(
            "请修改故事大纲:",
            default=generated_outline,
            multiline=True
        ).ask()

        if edited_outline and edited_outline.strip():
            outline_data = {"outline": edited_outline}
            save_outline_data(outline_data, outline_path)
            print("故事大纲已保存。\n")
        else:
            print("操作已取消或内容为空，未保存。\n")


def edit_outline(outline_data, outline_path):
    """Edit existing story outline."""
    current_outline = outline_data.get('outline', '')
    print("\n--- 当前故事大纲 ---")
    print(current_outline)
    print("------------------------\n")
    
    edited_outline = questionary.text(
        "请修改故事大纲:",
        default=current_outline,
        multiline=True
    ).ask()
    
    if edited_outline and edited_outline.strip() and edited_outline != current_outline:
        outline_data['outline'] = edited_outline
        save_outline_data(outline_data, outline_path)
        print("故事大纲已更新。\n")
    elif edited_outline is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def save_outline_data(outline_data, outline_path):
    """Save outline data to file."""
    with outline_path.open('w', encoding='utf-8') as f:
        json.dump(outline_data, f, ensure_ascii=False, indent=4)


def handle_chapter_outline():
    """Handles chapter outline management with full CRUD operations."""
    ensure_meta_dir()
    chapter_outline_path = META_DIR / "chapter_outline.json"
    
    # 检查前置条件
    story_outline_path = META_DIR / "story_outline.json"
    
    if not story_outline_path.exists():
        print("\n请先完成步骤4: 编辑故事大纲\n")
        return
    
    while True:
        # 每次循环都重新读取数据
        chapter_data = {}
        if chapter_outline_path.exists():
            try:
                with chapter_outline_path.open('r', encoding='utf-8') as f:
                    chapter_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                chapter_data = {}
        
        # 显示当前章节列表
        if chapter_data and chapter_data.get('chapters'):
            print("\n--- 当前分章细纲 ---")
            chapters = chapter_data['chapters']
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
        
        if not chapter_data or not chapter_data.get('chapters'):
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
            generate_chapter_outline(chapter_outline_path)
        elif action.startswith("2.") and chapter_data and chapter_data.get('chapters'):
            # 添加新章节
            add_chapter(chapter_data, chapter_outline_path)
        elif action.startswith("2.") and (not chapter_data or not chapter_data.get('chapters')):
            # 返回主菜单（当没有章节时）
            break
        elif action.startswith("3."):
            # 查看章节详情
            view_chapter(chapter_data)
        elif action.startswith("4."):
            # 修改章节信息
            edit_chapter(chapter_data, chapter_outline_path)
        elif action.startswith("5."):
            # 删除章节
            delete_chapter(chapter_data, chapter_outline_path)
        elif action.startswith("6.") or action.startswith("2."):
            # 返回主菜单
            break


def generate_chapter_outline(chapter_outline_path):
    """Generate chapter outline based on story outline."""
    # 读取故事大纲和其他信息
    story_outline_path = META_DIR / "story_outline.json"
    one_line_theme_path = META_DIR / "theme_one_line.json"
    characters_path = META_DIR / "characters.json"
    
    with story_outline_path.open('r', encoding='utf-8') as f:
        story_outline = json.load(f).get("outline", "")
    
    with one_line_theme_path.open('r', encoding='utf-8') as f:
        one_line_theme = json.load(f).get("theme", "")
    
    # 读取角色信息（如果有的话）
    characters_info = ""
    if characters_path.exists():
        try:
            with characters_path.open('r', encoding='utf-8') as f:
                characters_data = json.load(f)
                if characters_data:
                    characters_info = "\n\n已有角色信息：\n"
                    for char_name, char_data in characters_data.items():
                        characters_info += f"- {char_name}: {char_data.get('description', '无描述')}\n"
        except (json.JSONDecodeError, IOError):
            pass
    
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

    llm = configure_llm()
    if not llm:
        return

    # 构建提示词
    base_prompt = f"""请基于以下信息创建详细的分章细纲：

主题：{one_line_theme}

故事大纲：{story_outline}{characters_info}

请将故事分解为5-10个章节，每个章节包含：
1. 章节标题
2. 章节大纲（150-200字）
3. 主要情节点
4. 角色发展

请以JSON格式输出，格式如下：
{{
  "chapters": [
    {{
      "title": "章节标题",
      "outline": "章节详细大纲内容"
    }}
  ]
}}

请确保输出的是有效的JSON格式。"""
    
    if user_prompt.strip():
        full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        print(f"用户指导：{user_prompt.strip()}")
    else:
        full_prompt = base_prompt
    
    print("正在调用 AI 生成分章细纲，请稍候...")
    try:
        completion = llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            timeout=60,
        )
        generated_response = completion.choices[0].message.content
        
        # 尝试解析JSON
        try:
            # 提取JSON部分（如果AI返回了额外的文本）
            import re
            json_match = re.search(r'\{.*\}', generated_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                chapter_outline_data = json.loads(json_str)
            else:
                raise ValueError("未找到有效的JSON格式")
        except (json.JSONDecodeError, ValueError) as e:
            print(f"\n解析AI响应时出错: {e}")
            print("AI返回的原始内容：")
            print(generated_response)
            print("\n请稍后重试或手动添加章节。")
            return
            
    except APIStatusError as e:
        print(f"\n错误: 调用 API 时出错 (状态码: {e.status_code})")
        if e.status_code == 429:
             print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
        else:
            print(f"详细信息: {e.response.text}")
        return
    except Exception as e:
        print(f"\n调用 AI 时出错: {e}")
        if "Timeout" in str(e) or "timed out" in str(e):
             print("\n错误：请求超时。")
             print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
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
        save_chapter_data(chapter_outline_data, chapter_outline_path)
        print("分章细纲已保存。\n")
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
            final_data = {"chapters": modified_chapters}
            save_chapter_data(final_data, chapter_outline_path)
            print("分章细纲已保存。\n")
        else:
            print("未保存任何章节。\n")


def add_chapter(chapter_data, chapter_outline_path):
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
    
    if 'chapters' not in chapter_data:
        chapter_data['chapters'] = []
    
    chapter_data['chapters'].append(new_chapter)
    save_chapter_data(chapter_data, chapter_outline_path)
    print(f"章节 '{title}' 已添加。\n")


def view_chapter(chapter_data):
    """View chapter details."""
    chapters = chapter_data.get('chapters', [])
    if not chapters:
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


def edit_chapter(chapter_data, chapter_outline_path):
    """Edit chapter information."""
    chapters = chapter_data.get('chapters', [])
    if not chapters:
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
    save_chapter_data(chapter_data, chapter_outline_path)
    print("章节信息已更新。\n")


def delete_chapter(chapter_data, chapter_outline_path):
    """Delete a chapter."""
    chapters = chapter_data.get('chapters', [])
    if not chapters:
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
        save_chapter_data(chapter_data, chapter_outline_path)
        print(f"章节 '{chapter_title}' 已删除。\n")
    else:
        print("操作已取消。\n")


def save_chapter_data(chapter_data, chapter_outline_path):
    """Save chapter data to file."""
    with chapter_outline_path.open('w', encoding='utf-8') as f:
        json.dump(chapter_data, f, ensure_ascii=False, indent=4)


def handle_chapter_summary():
    """Handles chapter summary management with full CRUD operations."""
    ensure_meta_dir()
    chapter_summary_path = META_DIR / "chapter_summary.json"
    
    # 检查前置条件
    chapter_outline_path = META_DIR / "chapter_outline.json"
    
    if not chapter_outline_path.exists():
        print("\n请先完成步骤5: 编辑分章细纲\n")
        return
    
    # 读取分章细纲
    try:
        with chapter_outline_path.open('r', encoding='utf-8') as f:
            chapter_outline_data = json.load(f)
            chapters = chapter_outline_data.get('chapters', [])
    except (json.JSONDecodeError, IOError):
        print("\n无法读取分章细纲文件，请检查步骤5是否正确完成。\n")
        return
    
    if not chapters:
        print("\n分章细纲为空，请先完成步骤5。\n")
        return
    
    while True:
        # 每次循环都重新读取数据
        summary_data = {}
        if chapter_summary_path.exists():
            try:
                with chapter_summary_path.open('r', encoding='utf-8') as f:
                    summary_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                summary_data = {}
        
        # 显示当前章节概要状态
        print(f"\n--- 章节概要状态 (共{len(chapters)}章) ---")
        summaries = summary_data.get('summaries', {})
        
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
            generate_all_summaries(chapters, chapter_summary_path)
        elif action.startswith("2."):
            # 生成单个章节概要
            generate_single_summary(chapters, summary_data, chapter_summary_path)
        elif action.startswith("3."):
            # 查看章节概要
            view_chapter_summary(chapters, summary_data)
        elif action.startswith("4."):
            # 修改章节概要
            edit_chapter_summary(chapters, summary_data, chapter_summary_path)
        elif action.startswith("5."):
            # 删除章节概要
            delete_chapter_summary(chapters, summary_data, chapter_summary_path)


def generate_all_summaries(chapters, chapter_summary_path):
    """Generate summaries for all chapters."""
    print(f"准备为所有 {len(chapters)} 个章节生成概要...")
    
    confirm = questionary.confirm("这将为所有章节生成概要，可能需要较长时间。确定继续吗？").ask()
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
    
    llm = configure_llm()
    if not llm:
        return
    
    # 读取相关信息
    context_info = get_context_info()
    
    summaries = {}
    failed_chapters = []
    
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        print(f"\n正在生成第{i}章概要...")
        
        summary = generate_chapter_summary_content(
            llm, chapter, i, len(chapters), context_info, user_prompt
        )
        
        if summary:
            summaries[chapter_key] = {
                "title": chapter.get('title', f'第{i}章'),
                "summary": summary
            }
            print(f"第{i}章概要生成完成。")
        else:
            failed_chapters.append(i)
            print(f"第{i}章概要生成失败。")
    
    # 保存结果
    if summaries:
        summary_data = {"summaries": summaries}
        save_summary_data(summary_data, chapter_summary_path)
        print(f"\n成功生成 {len(summaries)} 个章节概要。")
        
        if failed_chapters:
            print(f"失败的章节: {', '.join(map(str, failed_chapters))}")
            print("您可以稍后单独重新生成失败的章节。")
    else:
        print("\n所有章节概要生成均失败。")


def generate_single_summary(chapters, summary_data, chapter_summary_path):
    """Generate summary for a single chapter."""
    # 选择章节
    chapter_choices = []
    for i, chapter in enumerate(chapters, 1):
        chapter_key = f"chapter_{i}"
        title = chapter.get('title', f'第{i}章')
        status = "已完成" if chapter_key in summary_data.get('summaries', {}) else "未完成"
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
    if chapter_key in summary_data.get('summaries', {}):
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
    
    llm = configure_llm()
    if not llm:
        return
    
    # 读取相关信息
    context_info = get_context_info()
    
    print(f"\n正在生成第{chapter_num}章概要...")
    summary = generate_chapter_summary_content(
        llm, chapter, chapter_num, len(chapters), context_info, user_prompt
    )
    
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
            if 'summaries' not in summary_data:
                summary_data['summaries'] = {}
            summary_data['summaries'][chapter_key] = {
                "title": chapter.get('title', f'第{chapter_num}章'),
                "summary": summary
            }
            save_summary_data(summary_data, chapter_summary_path)
            print(f"第{chapter_num}章概要已保存。\n")
        elif action.startswith("2."):
            # 修改后保存
            edited_summary = questionary.text(
                "请修改章节概要:",
                default=summary,
                multiline=True
            ).ask()

            if edited_summary and edited_summary.strip():
                if 'summaries' not in summary_data:
                    summary_data['summaries'] = {}
                summary_data['summaries'][chapter_key] = {
                    "title": chapter.get('title', f'第{chapter_num}章'),
                    "summary": edited_summary
                }
                save_summary_data(summary_data, chapter_summary_path)
                print(f"第{chapter_num}章概要已保存。\n")
            else:
                print("操作已取消或内容为空，未保存。\n")
    else:
        print(f"第{chapter_num}章概要生成失败。\n")


def generate_chapter_summary_content(llm, chapter, chapter_num, total_chapters, context_info, user_prompt):
    """Generate summary content for a single chapter."""
    # 构建提示词
    base_prompt = f"""请基于以下信息为第{chapter_num}章创建详细的章节概要：

{context_info}

当前章节信息：
章节标题：{chapter.get('title', f'第{chapter_num}章')}
章节大纲：{chapter.get('outline', '无大纲')}

请创建一个详细的章节概要，包含：
1. 场景设定（时间、地点、环境）
2. 主要人物及其行动
3. 关键情节发展
4. 对话要点
5. 情感氛围
6. 与整体故事的连接

概要应该详细具体，字数在300-500字左右，为后续的正文写作提供充分的指导。请直接输出章节概要，不要包含额外说明和标题。"""
    
    if user_prompt.strip():
        full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
    else:
        full_prompt = base_prompt
    
    try:
        completion = llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            timeout=60,
        )
        return completion.choices[0].message.content
    except APIStatusError as e:
        print(f"\n错误: 调用 API 时出错 (状态码: {e.status_code})")
        if e.status_code == 429:
             print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
        else:
            print(f"详细信息: {e.response.text}")
        return None
    except Exception as e:
        print(f"\n调用 AI 时出错: {e}")
        if "Timeout" in str(e) or "timed out" in str(e):
             print("\n错误：请求超时。")
             print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
        return None


def get_context_info():
    """Get context information for chapter summary generation."""
    context_parts = []
    
    # 读取主题信息
    try:
        with (META_DIR / "theme_one_line.json").open('r', encoding='utf-8') as f:
            theme = json.load(f).get("theme", "")
            if theme:
                context_parts.append(f"主题：{theme}")
    except:
        pass
    
    # 读取角色信息
    try:
        with (META_DIR / "characters.json").open('r', encoding='utf-8') as f:
            characters_data = json.load(f)
            if characters_data:
                context_parts.append("主要角色：")
                for char_name, char_data in characters_data.items():
                    context_parts.append(f"- {char_name}: {char_data.get('description', '无描述')}")
    except:
        pass
    
    # 读取场景信息
    try:
        with (META_DIR / "locations.json").open('r', encoding='utf-8') as f:
            locations_data = json.load(f)
            if locations_data:
                context_parts.append("重要场景：")
                for loc_name, loc_data in locations_data.items():
                    context_parts.append(f"- {loc_name}: {loc_data.get('description', '无描述')}")
    except:
        pass
    
    # 读取道具信息
    try:
        with (META_DIR / "items.json").open('r', encoding='utf-8') as f:
            items_data = json.load(f)
            if items_data:
                context_parts.append("重要道具：")
                for item_name, item_data in items_data.items():
                    context_parts.append(f"- {item_name}: {item_data.get('description', '无描述')}")
    except:
        pass
    
    # 读取故事大纲
    try:
        with (META_DIR / "story_outline.json").open('r', encoding='utf-8') as f:
            outline = json.load(f).get("outline", "")
            if outline:
                context_parts.append(f"故事大纲：{outline}")
    except:
        pass
    
    return "\n".join(context_parts)


def view_chapter_summary(chapters, summary_data):
    """View chapter summary details."""
    summaries = summary_data.get('summaries', {})
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


def edit_chapter_summary(chapters, summary_data, chapter_summary_path):
    """Edit chapter summary."""
    summaries = summary_data.get('summaries', {})
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
        summaries[chapter_key]['summary'] = edited_summary
        save_summary_data(summary_data, chapter_summary_path)
        print(f"第{chapter_num}章概要已更新。\n")
    elif edited_summary is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def delete_chapter_summary(chapters, summary_data, chapter_summary_path):
    """Delete chapter summary."""
    summaries = summary_data.get('summaries', {})
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
        del summaries[chapter_key]
        save_summary_data(summary_data, chapter_summary_path)
        print(f"第{chapter_num}章概要已删除。\n")
    else:
        print("操作已取消。\n")


def save_summary_data(summary_data, chapter_summary_path):
    """Save summary data to file."""
    with chapter_summary_path.open('w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=4)


def handle_novel_generation():
    """Handles novel text generation with full management operations."""
    ensure_meta_dir()
    novel_text_path = META_DIR / "novel_text.json"
    
    # 检查前置条件
    chapter_summary_path = META_DIR / "chapter_summary.json"
    
    if not chapter_summary_path.exists():
        print("\n请先完成步骤6: 编辑章节概要\n")
        return
    
    # 读取章节概要
    try:
        with chapter_summary_path.open('r', encoding='utf-8') as f:
            summary_data = json.load(f)
            summaries = summary_data.get('summaries', {})
    except (json.JSONDecodeError, IOError):
        print("\n无法读取章节概要文件，请检查步骤6是否正确完成。\n")
        return
    
    if not summaries:
        print("\n章节概要为空，请先完成步骤6。\n")
        return
    
    # 读取分章细纲以获取章节顺序
    try:
        with (META_DIR / "chapter_outline.json").open('r', encoding='utf-8') as f:
            chapter_outline_data = json.load(f)
            chapters = chapter_outline_data.get('chapters', [])
    except:
        chapters = []
    
    while True:
        # 每次循环都重新读取数据
        novel_data = {}
        if novel_text_path.exists():
            try:
                with novel_text_path.open('r', encoding='utf-8') as f:
                    novel_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                novel_data = {}
        
        # 显示当前小说正文状态
        print(f"\n--- 小说正文状态 (共{len(summaries)}章) ---")
        novel_chapters = novel_data.get('chapters', {})
        
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
            generate_all_novel_chapters(chapters, summaries, novel_text_path)
        elif action.startswith("2."):
            # 生成单个章节正文
            generate_single_novel_chapter(chapters, summaries, novel_data, novel_text_path)
        elif action.startswith("3."):
            # 查看章节正文
            view_novel_chapter(chapters, novel_data)
        elif action.startswith("4."):
            # 修改章节正文
            edit_novel_chapter(chapters, novel_data, novel_text_path)
        elif action.startswith("5."):
            # 删除章节正文
            delete_novel_chapter(chapters, novel_data, novel_text_path)
        elif action.startswith("6."):
            # 导出完整小说
            export_complete_novel(chapters, novel_data)


def generate_all_novel_chapters(chapters, summaries, novel_text_path):
    """Generate novel text for all chapters."""
    print(f"准备为所有 {len(summaries)} 个章节生成正文...")
    
    confirm = questionary.confirm("这将为所有章节生成正文，可能需要很长时间。确定继续吗？").ask()
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
    
    llm = configure_llm()
    if not llm:
        return
    
    # 读取相关信息
    context_info = get_context_info()
    
    novel_chapters = {}
    failed_chapters = []
    
    for i in range(1, len(chapters) + 1):
        chapter_key = f"chapter_{i}"
        if chapter_key not in summaries:
            continue
            
        print(f"\n正在生成第{i}章正文...")
        
        chapter_content = generate_novel_chapter_content(
            llm, chapters[i-1], summaries[chapter_key], i, len(chapters), context_info, user_prompt
        )
        
        if chapter_content:
            novel_chapters[chapter_key] = {
                "title": chapters[i-1].get('title', f'第{i}章'),
                "content": chapter_content,
                "word_count": len(chapter_content)
            }
            print(f"第{i}章正文生成完成 ({len(chapter_content)}字)。")
        else:
            failed_chapters.append(i)
            print(f"第{i}章正文生成失败。")
    
    # 保存结果
    if novel_chapters:
        novel_data = {"chapters": novel_chapters}
        save_novel_data(novel_data, novel_text_path)
        total_words = sum(ch.get('word_count', 0) for ch in novel_chapters.values())
        print(f"\n成功生成 {len(novel_chapters)} 个章节正文，总计 {total_words} 字。")
        
        if failed_chapters:
            print(f"失败的章节: {', '.join(map(str, failed_chapters))}")
            print("您可以稍后单独重新生成失败的章节。")
    else:
        print("\n所有章节正文生成均失败。")


def generate_single_novel_chapter(chapters, summaries, novel_data, novel_text_path):
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
    
    llm = configure_llm()
    if not llm:
        return
    
    # 读取相关信息
    context_info = get_context_info()
    
    print(f"\n正在生成第{chapter_num}章正文...")
    chapter_content = generate_novel_chapter_content(
        llm, chapter, summaries[chapter_key], chapter_num, len(chapters), context_info, user_prompt
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
            if 'chapters' not in novel_data:
                novel_data['chapters'] = {}
            novel_data['chapters'][chapter_key] = {
                "title": chapter.get('title', f'第{chapter_num}章'),
                "content": chapter_content,
                "word_count": len(chapter_content)
            }
            save_novel_data(novel_data, novel_text_path)
            print(f"第{chapter_num}章正文已保存 ({len(chapter_content)}字)。\n")
        elif action.startswith("2."):
            # 修改后保存
            edited_content = questionary.text(
                "请修改章节正文:",
                default=chapter_content,
                multiline=True
            ).ask()

            if edited_content and edited_content.strip():
                if 'chapters' not in novel_data:
                    novel_data['chapters'] = {}
                novel_data['chapters'][chapter_key] = {
                    "title": chapter.get('title', f'第{chapter_num}章'),
                    "content": edited_content,
                    "word_count": len(edited_content)
                }
                save_novel_data(novel_data, novel_text_path)
                print(f"第{chapter_num}章正文已保存 ({len(edited_content)}字)。\n")
            else:
                print("操作已取消或内容为空，未保存。\n")
    else:
        print(f"第{chapter_num}章正文生成失败。\n")


def generate_novel_chapter_content(llm, chapter, summary_info, chapter_num, total_chapters, context_info, user_prompt):
    """Generate novel content for a single chapter."""
    # 构建提示词
    base_prompt = f"""请基于以下信息为第{chapter_num}章创建完整的小说正文：

{context_info}

当前章节信息：
章节标题：{chapter.get('title', f'第{chapter_num}章')}
章节大纲：{chapter.get('outline', '无大纲')}

章节概要：
{summary_info.get('summary', '无概要')}

请创建完整的小说正文，要求：
1. 生动的场景描写和环境渲染
2. 丰富的人物对话和内心独白
3. 细腻的情感表达和心理描写
4. 流畅的情节推进和节奏控制
5. 符合小说文学风格的语言表达
6. 与前后章节的自然衔接

正文应该详细完整，字数在2000-4000字左右。请直接输出小说正文，不要包含章节标题和额外说明。"""
    
    if user_prompt.strip():
        full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
    else:
        full_prompt = base_prompt
    
    try:
        completion = llm.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": full_prompt,
                }
            ],
            timeout=120,  # 增加超时时间，因为生成正文需要更长时间
        )
        return completion.choices[0].message.content
    except APIStatusError as e:
        print(f"\n错误: 调用 API 时出错 (状态码: {e.status_code})")
        if e.status_code == 429:
             print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
        else:
            print(f"详细信息: {e.response.text}")
        return None
    except Exception as e:
        print(f"\n调用 AI 时出错: {e}")
        if "Timeout" in str(e) or "timed out" in str(e):
             print("\n错误：请求超时。")
             print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
        return None


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


def edit_novel_chapter(chapters, novel_data, novel_text_path):
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
        novel_chapters[chapter_key]['content'] = edited_content
        novel_chapters[chapter_key]['word_count'] = len(edited_content)
        save_novel_data(novel_data, novel_text_path)
        print(f"第{chapter_num}章正文已更新 ({len(edited_content)}字)。\n")
    elif edited_content is None:
        print("操作已取消。\n")
    else:
        print("内容未更改。\n")


def delete_novel_chapter(chapters, novel_data, novel_text_path):
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
        del novel_chapters[chapter_key]
        save_novel_data(novel_data, novel_text_path)
        print(f"第{chapter_num}章正文已删除。\n")
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
        with (META_DIR / "theme_one_line.json").open('r', encoding='utf-8') as f:
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


def save_novel_data(novel_data, novel_text_path):
    """Save novel data to file."""
    with novel_text_path.open('w', encoding='utf-8') as f:
        json.dump(novel_data, f, ensure_ascii=False, indent=4)


def main():
    """
    Main function to display the interactive menu.
    """
    while True:
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
                "8. 退出"
            ],
            use_indicator=True
        ).ask()

        if choice is None or choice.endswith("退出"):
            print("再见！")
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
        else:
            print(f"您选择了: {choice} (功能开发中...)\n")


if __name__ == "__main__":
    main()
