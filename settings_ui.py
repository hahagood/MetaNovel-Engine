from ui_utils import ui
from config import get_llm_model, set_llm_model, LLM_MODELS, add_llm_model, get_retry_config, set_retry_config, reset_retry_config, get_export_path_info, set_custom_export_path, clear_custom_export_path
from prompts_ui import handle_prompts_management


def handle_system_settings():
    """主设置菜单"""
    try:
        while True:
            # 动态获取当前模型名称用于菜单显示
            model_id_to_name = {v: k for k, v in LLM_MODELS.items()}
            current_model_id = get_llm_model()
            current_model_name = model_id_to_name.get(current_model_id, current_model_id)

            menu_options = [
                f"AI模型管理 (当前: {current_model_name})",
                "Prompts模板管理",
                "智能重试配置",
                "导出路径配置",
                "返回主菜单"
            ]
            choice = ui.display_menu("系统设置", menu_options)

            if choice == '1':
                handle_llm_model_settings()
            elif choice == '2':
                handle_prompts_management()
            elif choice == '3':
                handle_retry_settings()
            elif choice == '4':
                handle_export_settings()
            elif choice == '0':
                break
    
    except KeyboardInterrupt:
        # 重新抛出 KeyboardInterrupt 让上层处理
        raise

def handle_llm_model_settings():
    """AI模型管理子菜单"""
    try:
        while True:
            menu_options = [
                "切换AI模型",
                "添加新模型",
                "返回"
            ]
            choice = ui.display_menu("AI模型管理", menu_options)

            if choice == '1':
                switch_llm_model_ui()
            elif choice == '2':
                add_new_llm_model_ui()
            elif choice == '0':
                break
    
    except KeyboardInterrupt:
        # 重新抛出，由上层处理
        raise

def switch_llm_model_ui():
    """切换语言模型的UI交互"""
    model_id_to_name = {v: k for k, v in LLM_MODELS.items()}
    
    current_model_id = get_llm_model()
    current_model_name = model_id_to_name.get(current_model_id, current_model_id)
    ui.print_info(f"当前模型: {current_model_name}")
    
    model_options = list(LLM_MODELS.keys())
    model_options.append("返回")
    
    choice_str = ui.display_menu("请选择新的AI模型:", model_options)
    
    if choice_str.isdigit():
        choice = int(choice_str)
        if 1 <= choice <= len(LLM_MODELS):
            new_model_name = list(LLM_MODELS.keys())[choice - 1]
            new_model_id = LLM_MODELS[new_model_name]
            
            if set_llm_model(new_model_id):
                ui.print_success(f"AI模型已成功切换为: {new_model_name}")
            else:
                ui.print_error("模型切换失败，请检查配置或.env文件权限。")

        elif choice == 0:
             return
    ui.pause()

def add_new_llm_model_ui():
    """添加新模型的UI交互"""
    ui.print_info("添加新的AI模型")
    
    model_name = ui.prompt("请输入模型显示名称 (例如 'My New Model'):")
    if not model_name:
        ui.print_warning("操作已取消。")
        ui.pause()
        return

    model_id = ui.prompt(f"请输入 '{model_name}' 的模型ID (例如 'vendor/model-name'):")
    if not model_id:
        ui.print_warning("操作已取消。")
        ui.pause()
        return

    if add_llm_model(model_name, model_id):
        ui.print_success(f"模型 '{model_name}' 添加成功！")
    else:
        ui.print_error("添加模型失败，可能是名称或ID已存在，或文件写入权限不足。")
    
    ui.pause()


def handle_retry_settings():
    """处理重试配置的子菜单"""
    try:
        while True:
            menu_options = [
                "查看当前配置",
                "修改配置",
                "恢复默认配置",
                "返回"
            ]
            choice = ui.display_menu("智能重试配置", menu_options)

            if choice == '1':
                show_retry_config()
            elif choice == '2':
                modify_retry_config()
            elif choice == '3':
                reset_retry_config_ui()
            elif choice == '0':
                break
    
    except KeyboardInterrupt:
        # 重新抛出 KeyboardInterrupt 让上层处理
        raise

def show_retry_config():
    """显示当前的重试配置"""
    config = get_retry_config()
    ui.print_info("当前的智能重试配置:")
    ui.print_json(config)
    ui.pause()

def modify_retry_config():
    """修改重试配置"""
    current_config = get_retry_config()
    ui.print_info("当前配置:")
    ui.print_json(current_config)

    try:
        retries_str = ui.prompt("请输入最大重试次数:", default=str(current_config.get('retries', 3)))
        delay_str = ui.prompt("请输入重试延迟(秒):", default=str(current_config.get('delay', 2)))
        backoff_str = ui.prompt("请输入延迟递增因子:", default=str(current_config.get('backoff', 2)))
        
        if retries_str and delay_str and backoff_str:
            new_config = {
                'retries': int(retries_str),
                'delay': float(delay_str),
                'backoff': float(backoff_str)
            }
            set_retry_config(new_config)
            ui.print_success("重试配置已更新。")
        else:
            ui.print_warning("操作已取消。")
    except ValueError:
        ui.print_error("输入无效，请输入数字。")
    ui.pause()

def reset_retry_config_ui():
    """UI for resetting retry config."""
    if ui.confirm("确定要重置为默认的重试配置吗?"):
        reset_retry_config()
        ui.print_success("重试配置已恢复为默认值。")
    else:
        ui.print_warning("操作已取消。")
    ui.pause()

def handle_export_settings():
    """处理导出路径的子菜单"""
    try:
        while True:
            menu_options = [
                "查看当前配置",
                "修改导出路径",
                "恢复默认路径",
                "返回"
            ]
            choice = ui.display_menu("导出路径配置", menu_options)

            if choice == '1':
                show_export_config()
            elif choice == '2':
                modify_export_config()
            elif choice == '3':
                clear_custom_export_path_ui()
            elif choice == '0':
                break
    
    except KeyboardInterrupt:
        # 重新抛出 KeyboardInterrupt 让上层处理
        raise


def show_export_config():
    """显示导出路径配置"""
    info = get_export_path_info()
    ui.print_info("--- 导出路径配置 ---")
    ui.print_info(f"当前导出路径: {info['current_path']}")
    ui.print_info(f"用户文档目录: {info['documents_dir']}")
    ui.print_info(f"默认导出路径: {info['default_path']}")
    
    if info['is_custom']:
        ui.print_info(f"自定义路径: {info['custom_path']}")
    else:
        ui.print_info("自定义路径: (未设置)")
    ui.pause()

def modify_export_config():
    """修改导出路径"""
    info = get_export_path_info()
    new_path = ui.prompt("请输入新的自定义导出路径:", default=info.get('custom_path', ''))
    if new_path and new_path.strip():
        set_custom_export_path(new_path.strip())
        ui.print_success("导出路径已更新。")
    else:
        ui.print_warning("操作已取消或路径为空。")
    ui.pause()
    
def clear_custom_export_path_ui():
    """UI for clearing custom export path"""
    if ui.confirm("确定要恢复为默认导出路径吗?"):
        clear_custom_export_path()
        ui.print_success("已恢复为默认导出路径。")
    else:
        ui.print_warning("操作已取消。")
    ui.pause()
