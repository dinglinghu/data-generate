#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STK星座预警冲突消解数据采集快速启动脚本
提供预设的常用采集配置，简化使用流程
"""

import sys
import subprocess
import argparse
from pathlib import Path

def print_menu():
    """显示快速启动菜单"""
    menu = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    STK星座预警数据采集快速启动菜单                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🚀 预设配置:                                                                ║
║                                                                              ║
║  1. 快速测试     - 1次采集，生成甘特图 (约2分钟)                             ║
║  2. 标准采集     - 3次采集，生成甘特图 (约6分钟)                             ║
║  3. 批量采集     - 5次采集，生成甘特图 (约10分钟)                            ║
║  4. 高速采集     - 3次采集，不生成甘特图 (约3分钟)                           ║
║  5. 大规模采集   - 10次采集，不生成甘特图 (约15分钟)                         ║
║  6. 调试模式     - 1次采集，详细日志 (约2分钟)                               ║
║  7. 自定义配置   - 手动指定参数                                              ║
║                                                                              ║
║  🔧 工具功能:                                                                ║
║                                                                              ║
║  8. 查看数据     - 展示最新采集的数据                                        ║
║  9. 运行测试     - 验证系统功能                                              ║
║  10. 清理数据    - 清理输出目录                                              ║
║                                                                              ║
║  0. 退出                                                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(menu)

def run_command(cmd: list, description: str):
    """运行命令并显示进度"""
    print(f"\n🚀 {description}")
    print(f"📝 执行命令: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        print(f"\n✅ {description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {description} 失败: {e}")
        return False
    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断操作")
        return False

def quick_test():
    """快速测试"""
    cmd = ["python", "unified_data_collection.py", "--collections", "1"]
    return run_command(cmd, "快速测试 (1次采集)")

def standard_collection():
    """标准采集"""
    cmd = ["python", "unified_data_collection.py", "--collections", "3"]
    return run_command(cmd, "标准采集 (3次采集)")

def batch_collection():
    """批量采集"""
    cmd = ["python", "unified_data_collection.py", "--collections", "5"]
    return run_command(cmd, "批量采集 (5次采集)")

def high_speed_collection():
    """高速采集"""
    cmd = ["python", "unified_data_collection.py", "--collections", "3", "--no-gantt"]
    return run_command(cmd, "高速采集 (3次采集，无甘特图)")

def large_scale_collection():
    """大规模采集"""
    cmd = ["python", "unified_data_collection.py", "--collections", "10", "--no-gantt"]
    return run_command(cmd, "大规模采集 (10次采集，无甘特图)")

def debug_mode():
    """调试模式"""
    cmd = ["python", "unified_data_collection.py", "--collections", "1", "--log-level", "DEBUG"]
    return run_command(cmd, "调试模式 (1次采集，详细日志)")

def custom_configuration():
    """自定义配置"""
    print("\n🔧 自定义配置")
    print("-" * 60)
    
    try:
        collections = input("请输入采集次数 (默认: 3): ").strip()
        if not collections:
            collections = "3"
        collections = int(collections)
        
        gantt = input("是否生成甘特图? (y/N): ").strip().lower()
        enable_gantt = gantt in ['y', 'yes', '是']
        
        session_name = input("会话名称 (可选): ").strip()
        
        log_level = input("日志级别 (INFO/DEBUG/WARNING/ERROR, 默认: INFO): ").strip().upper()
        if log_level not in ['INFO', 'DEBUG', 'WARNING', 'ERROR']:
            log_level = 'INFO'
        
        # 构建命令
        cmd = ["python", "unified_data_collection.py", "--collections", str(collections)]
        
        if not enable_gantt:
            cmd.append("--no-gantt")
        
        if session_name:
            cmd.extend(["--session", session_name])
        
        if log_level != 'INFO':
            cmd.extend(["--log-level", log_level])
        
        return run_command(cmd, f"自定义采集 ({collections}次采集)")
        
    except ValueError:
        print("❌ 输入的采集次数无效")
        return False
    except KeyboardInterrupt:
        print("\n⚠️ 用户取消操作")
        return False

def view_data():
    """查看数据"""
    cmd = ["python", "demo_conflict_resolution_system.py"]
    return run_command(cmd, "查看最新采集数据")

def run_tests():
    """运行测试"""
    cmd = ["python", "test_conflict_resolution_system.py"]
    return run_command(cmd, "系统功能测试")

def clean_data():
    """清理数据"""
    print("\n🧹 清理数据")
    print("-" * 60)
    
    output_dir = Path("output")
    if not output_dir.exists():
        print("📁 输出目录不存在，无需清理")
        return True
    
    confirm = input("⚠️ 确认要删除所有输出数据吗? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes', '是']:
        print("❌ 取消清理操作")
        return False
    
    try:
        import shutil
        shutil.rmtree(output_dir)
        print("✅ 输出目录已清理")
        return True
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="STK星座预警数据采集快速启动脚本")
    parser.add_argument('--menu-only', action='store_true', help='只显示菜单，不执行操作')
    args = parser.parse_args()
    
    if args.menu_only:
        print_menu()
        return 0
    
    while True:
        print_menu()
        
        try:
            choice = input("请选择操作 (0-10): ").strip()
            
            if choice == '0':
                print("👋 再见！")
                break
            elif choice == '1':
                quick_test()
            elif choice == '2':
                standard_collection()
            elif choice == '3':
                batch_collection()
            elif choice == '4':
                high_speed_collection()
            elif choice == '5':
                large_scale_collection()
            elif choice == '6':
                debug_mode()
            elif choice == '7':
                custom_configuration()
            elif choice == '8':
                view_data()
            elif choice == '9':
                run_tests()
            elif choice == '10':
                clean_data()
            else:
                print("❌ 无效选择，请输入 0-10")
                continue
            
            # 询问是否继续
            if choice != '0':
                continue_choice = input("\n是否继续使用? (Y/n): ").strip().lower()
                if continue_choice in ['n', 'no', '否']:
                    print("👋 再见！")
                    break
        
        except KeyboardInterrupt:
            print("\n👋 再见！")
            break
        except Exception as e:
            print(f"❌ 操作异常: {e}")
            continue
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
