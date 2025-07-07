import json
from ui_utils import ui, console
from rich.panel import Panel

PROMPTS_FILE = 'prompts.json'
DEFAULT_PROMPTS_FILE = 'prompts.default.json' # 假设我们有一个默认备份文件

def get_prompts():
    """加载prompts"""
    try:
        with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_prompts(prompts):
    """保存prompts"""
    with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)

def handle_prompts_management():
    """处理prompts管理的UI"""
    while True:
        menu_options = [
            "查看所有Prompts",
            "编辑一个Prompt",
            "恢复默认Prompts",
            "返回"
        ]
        choice = ui.display_menu("🔧 Prompts模板管理", menu_options)

        if choice == '1':
            view_all_prompts()
        elif choice == '2':
            edit_prompt()
        elif choice == '3':
            reset_prompts()
        elif choice == '0':
            break

def view_all_prompts():
    """显示所有prompts"""
    prompts = get_prompts()
    if not prompts:
        ui.print_warning("没有找到任何Prompts。")
        ui.pause()
        return
        
    for key, value in prompts.items():
        console.print(Panel(f"[bold cyan]{key}[/bold cyan]\n\n{value.get('base_prompt', '')}", title=f"Prompt: {key}", border_style="green"))
    ui.pause()

def edit_prompt():
    """编辑一个prompt"""
    prompts = get_prompts()
    if not prompts:
        ui.print_warning("没有可编辑的Prompts。")
        ui.pause()
        return

    prompt_keys = list(prompts.keys())
    prompt_keys.append("返回")
    
    choice_str = ui.display_menu("请选择要编辑的Prompt:", prompt_keys)
    
    if choice_str.isdigit():
        choice = int(choice_str)
        if 1 <= choice <= len(prompts):
            key_to_edit = list(prompts.keys())[choice - 1]
            
            current_prompt_text = prompts[key_to_edit].get('base_prompt', '')
            ui.print_info(f"--- 正在编辑: {key_to_edit} ---")
            ui.print_info("当前内容:")
            console.print(Panel(current_prompt_text, border_style="yellow"))
            
            new_text = ui.prompt("请输入新的Prompt内容 (多行输入)", multiline=True, default=current_prompt_text)
            
            if new_text is not None and new_text != current_prompt_text:
                prompts[key_to_edit]['base_prompt'] = new_text
                save_prompts(prompts)
                ui.print_success(f"Prompt '{key_to_edit}' 已更新。")
            else:
                ui.print_warning("操作已取消或内容未更改。")
        elif choice == 0:
            return

    ui.pause()


def reset_prompts():
    """恢复默认prompts"""
    if not ui.confirm("确定要将所有Prompts恢复到默认设置吗？此操作无法撤销。"):
        ui.print_warning("操作已取消。")
        ui.pause()
        return

    try:
        with open(DEFAULT_PROMPTS_FILE, 'r', encoding='utf-8') as f:
            default_prompts = json.load(f)
        
        save_prompts(default_prompts)
        ui.print_success("所有Prompts已成功恢复为默认设置。")
    except FileNotFoundError:
        ui.print_error(f"错误：未找到默认配置文件 '{DEFAULT_PROMPTS_FILE}'。")
    except Exception as e:
        ui.print_error(f"恢复默认设置时发生错误: {e}")
    
    ui.pause()
