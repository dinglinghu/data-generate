#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STK星座预警冲突消解数据采集统一运行脚本
整合所有数据采集功能，提供一键式数据采集体验
"""

import sys
import argparse
import asyncio
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """设置日志配置"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 设置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 文件处理器（如果指定）
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

def print_banner():
    """打印系统横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    STK星座预警冲突消解数据采集系统                            ║
║                         Unified Data Collection System                       ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🎯 功能特性:                                                                ║
║     ✅ 虚拟元任务填充的完整时间轴                                            ║
║     ✅ 真实任务的位置信息增强                                                ║
║     ✅ 统一数据管理和分类保存                                                ║
║     ✅ JSON和甘特图分文件夹保存                                              ║
║     ✅ 冲突消解数据生成                                                      ║
║     ✅ 会话级别的数据汇总                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

def print_collection_summary(results: list, session_dir: Path, total_time: float):
    """打印采集汇总信息"""
    print("\n" + "="*80)
    print("📊 数据采集汇总报告")
    print("="*80)
    
    successful_collections = len([r for r in results if r.get('success', False)])
    total_collections = len(results)
    
    print(f"🎯 采集统计:")
    print(f"   总采集次数: {total_collections}")
    print(f"   成功采集: {successful_collections}")
    print(f"   失败采集: {total_collections - successful_collections}")
    print(f"   成功率: {successful_collections/total_collections*100:.1f}%")
    print(f"   总耗时: {total_time:.1f} 秒")
    print(f"   平均每次采集耗时: {total_time/total_collections:.1f} 秒")
    
    # 统计数据
    total_meta_tasks = 0
    total_visible_tasks = 0
    total_missiles = 0
    
    for result in results:
        if result.get('success', False):
            collection_data = result.get('collection_data', {})
            
            # 统计元任务
            meta_tasks = collection_data.get("meta_tasks", {}).get("meta_tasks", {})
            total_missiles += len(meta_tasks)
            for missile_data in meta_tasks.values():
                total_meta_tasks += len(missile_data.get("atomic_tasks", []))
            
            # 统计可见任务
            visible_meta_tasks = collection_data.get("visible_meta_tasks", {})
            constellation_sets = visible_meta_tasks.get("constellation_visible_task_sets", {})
            for satellite_data in constellation_sets.values():
                for missile_id in satellite_data.get("missile_tasks", {}):
                    missile_tasks = satellite_data["missile_tasks"][missile_id]
                    total_visible_tasks += len(missile_tasks.get("visible_tasks", []))
    
    print(f"\n📈 数据统计:")
    print(f"   总导弹数: {total_missiles}")
    print(f"   总元任务数: {total_meta_tasks}")
    print(f"   总可见任务数: {total_visible_tasks}")
    if total_missiles > 0:
        print(f"   平均每导弹元任务数: {total_meta_tasks/total_missiles:.1f}")
    
    print(f"\n📁 输出目录:")
    print(f"   会话目录: {session_dir}")
    
    # 查找统一数据目录
    unified_dir = Path("output/unified_collections")
    if unified_dir.exists():
        session_dirs = [d for d in unified_dir.iterdir() if d.is_dir()]
        if session_dirs:
            latest_session = max(session_dirs, key=lambda x: x.stat().st_mtime)
            print(f"   统一数据目录: {latest_session}")
            
            # 统计文件
            json_dir = latest_session / "json_data"
            charts_dir = latest_session / "charts"
            
            if json_dir.exists():
                json_files = list(json_dir.glob("*.json"))
                print(f"   JSON文件数: {len(json_files)}")
            
            if charts_dir.exists():
                chart_files = list(charts_dir.glob("*.png"))
                print(f"   图表文件数: {len(chart_files)}")

def print_usage_tips():
    """打印使用提示"""
    print("\n" + "="*80)
    print("💡 使用提示")
    print("="*80)
    print("📖 查看数据:")
    print("   python demo_conflict_resolution_system.py")
    print("\n🧪 运行测试:")
    print("   python test_conflict_resolution_system.py")
    print("\n📊 数据分析:")
    print("   查看 output/unified_collections/ 目录下的统一数据")
    print("   JSON数据在 json_data/ 子目录")
    print("   甘特图在 charts/ 子目录")
    print("\n📋 文件说明:")
    print("   • collection_XXX_original.json: 原始采集数据")
    print("   • collection_XXX_timeline.json: 时间轴数据")
    print("   • collection_XXX_summary.json: 采集摘要")
    print("   • collection_XXX_conflict_resolution.json: 冲突消解数据")
    print("   • session_summary.*: 会话汇总")

async def run_data_collection(collections: int, enable_gantt: bool, log_level: str, 
                            session_name: Optional[str] = None) -> Dict[str, Any]:
    """运行数据采集"""
    try:
        # 导入必要的模块
        from src.stk_interface.stk_manager import STKManager
        from src.meta_task.rolling_data_collector import RollingDataCollector
        from src.utils.config_manager import get_config_manager
        
        print(f"🚀 开始数据采集...")
        print(f"   采集次数: {collections}")
        print(f"   生成甘特图: {'是' if enable_gantt else '否'}")
        print(f"   日志级别: {log_level}")
        if session_name:
            print(f"   会话名称: {session_name}")
        
        start_time = time.time()
        
        # 初始化系统
        print(f"\n🔧 初始化系统组件...")
        config_manager = get_config_manager()

        # 创建滚动数据采集器
        rolling_data_collector = RollingDataCollector(config_manager)
        
        # 设置输出目录
        output_config = config_manager.get_output_config()
        base_directory = output_config.get("base_directory", "output")
        
        # 创建会话目录
        if session_name:
            session_dir_name = f"session_{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        else:
            session_dir_name = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session_dir = Path(base_directory) / "rolling_collections" / session_dir_name
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置滚动数据采集器
        rolling_data_collector.output_base_dir = str(session_dir)
        rolling_data_collector.enable_gantt = enable_gantt
        
        print(f"✅ 系统初始化完成")
        print(f"   会话目录: {session_dir}")
        
        # 执行滚动数据采集
        print(f"\n📊 开始滚动数据采集...")
        results = []
        
        for i in range(collections):
            print(f"\n{'='*60}")
            print(f"📈 第 {i+1}/{collections} 次数据采集")
            print(f"{'='*60}")
            
            try:
                collection_start = time.time()
                
                # 执行单次采集
                collection_result = await rolling_data_collector.collect_rolling_data()
                
                collection_time = time.time() - collection_start
                
                if collection_result:
                    results.append({
                        'index': i + 1,
                        'success': True,
                        'collection_data': collection_result,
                        'collection_time': collection_time,
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"✅ 第 {i+1} 次采集成功 (耗时: {collection_time:.1f}s)")
                else:
                    results.append({
                        'index': i + 1,
                        'success': False,
                        'error': 'Collection returned None',
                        'collection_time': collection_time,
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"❌ 第 {i+1} 次采集失败")
                
                # 短暂延迟，避免系统过载
                if i < collections - 1:
                    await asyncio.sleep(1)
                    
            except Exception as e:
                collection_time = time.time() - collection_start
                results.append({
                    'index': i + 1,
                    'success': False,
                    'error': str(e),
                    'collection_time': collection_time,
                    'timestamp': datetime.now().isoformat()
                })
                print(f"❌ 第 {i+1} 次采集异常: {e}")
        
        # 结束统一数据管理会话
        print(f"\n📋 生成会话汇总...")
        await rolling_data_collector.finalize_session()

        # 生成传统会话汇总
        try:
            from stk_rolling_meta_task_collection import generate_session_summary
            # 创建一个模拟的system对象用于兼容性
            class MockSystem:
                def __init__(self, rdc):
                    self.rolling_data_collector = rdc

            mock_system = MockSystem(rolling_data_collector)
            await generate_session_summary(session_dir, results, mock_system, enable_gantt)
        except Exception as e:
            print(f"⚠️ 传统会话汇总生成失败: {e}")

        total_time = time.time() - start_time
        
        return {
            'success': True,
            'results': results,
            'session_dir': session_dir,
            'total_time': total_time,
            'collections': collections,
            'enable_gantt': enable_gantt
        }
        
    except Exception as e:
        print(f"❌ 数据采集系统异常: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e),
            'results': [],
            'total_time': time.time() - start_time if 'start_time' in locals() else 0
        }

def load_preset_config(preset_name: str) -> Dict[str, Any]:
    """加载预设配置"""
    try:
        import yaml
        config_file = Path("collection_presets.yaml")

        if not config_file.exists():
            print(f"⚠️ 配置文件不存在: {config_file}")
            return {}

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        presets = config.get('presets', {})
        if preset_name not in presets:
            print(f"⚠️ 预设配置不存在: {preset_name}")
            print(f"可用预设: {', '.join(presets.keys())}")
            return {}

        return presets[preset_name]

    except ImportError:
        print("⚠️ 需要安装 PyYAML: pip install PyYAML")
        return {}
    except Exception as e:
        print(f"⚠️ 加载配置失败: {e}")
        return {}

def list_presets():
    """列出所有可用的预设配置"""
    try:
        import yaml
        config_file = Path("collection_presets.yaml")

        if not config_file.exists():
            print("⚠️ 配置文件不存在")
            return

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        presets = config.get('presets', {})

        print("\n📋 可用的预设配置:")
        print("=" * 60)
        for name, preset in presets.items():
            print(f"🎯 {name}:")
            print(f"   描述: {preset.get('description', '无描述')}")
            print(f"   采集次数: {preset.get('collections', 'N/A')}")
            print(f"   甘特图: {'是' if preset.get('enable_gantt', False) else '否'}")
            print(f"   预计时间: {preset.get('estimated_time', '未知')}")
            print()

    except Exception as e:
        print(f"⚠️ 列出预设失败: {e}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="STK星座预警冲突消解数据采集统一运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s --collections 3                    # 采集3次数据，生成甘特图
  %(prog)s --collections 5 --no-gantt        # 采集5次数据，不生成甘特图
  %(prog)s --collections 2 --session test    # 采集2次数据，会话名为test
  %(prog)s --collections 1 --log-level DEBUG # 采集1次数据，详细日志
  %(prog)s --preset standard                  # 使用标准预设配置
  %(prog)s --list-presets                     # 列出所有预设配置
        """
    )
    
    parser.add_argument(
        '--preset', '-p',
        type=str,
        help='使用预设配置 (如: standard, quick_test, batch)'
    )

    parser.add_argument(
        '--list-presets',
        action='store_true',
        help='列出所有可用的预设配置'
    )

    parser.add_argument(
        '--collections', '-c',
        type=int,
        default=3,
        help='数据采集次数 (默认: 3)'
    )
    
    parser.add_argument(
        '--no-gantt',
        action='store_true',
        help='禁用甘特图生成 (默认: 生成甘特图)'
    )
    
    parser.add_argument(
        '--session', '-s',
        type=str,
        help='会话名称 (可选)'
    )
    
    parser.add_argument(
        '--log-level', '-l',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日志级别 (默认: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='日志文件路径 (可选)'
    )
    
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='静默模式，只显示关键信息'
    )
    
    args = parser.parse_args()

    # 处理列出预设的请求
    if args.list_presets:
        list_presets()
        return 0

    # 处理预设配置
    if args.preset:
        preset_config = load_preset_config(args.preset)
        if not preset_config:
            return 1

        # 使用预设配置覆盖默认值
        if not hasattr(args, 'collections') or args.collections == 3:  # 默认值
            args.collections = preset_config.get('collections', args.collections)

        if not args.no_gantt:  # 如果用户没有明确指定
            args.no_gantt = not preset_config.get('enable_gantt', True)

        if args.log_level == 'INFO':  # 默认值
            args.log_level = preset_config.get('log_level', args.log_level)

        print(f"🎯 使用预设配置: {args.preset}")
        print(f"   {preset_config.get('description', '无描述')}")
        print(f"   预计时间: {preset_config.get('estimated_time', '未知')}")

    # 设置日志
    if args.quiet:
        log_level = 'WARNING'
    else:
        log_level = args.log_level

    setup_logging(log_level, args.log_file)

    # 显示横幅
    if not args.quiet:
        print_banner()
    
    # 运行数据采集
    try:
        result = asyncio.run(run_data_collection(
            collections=args.collections,
            enable_gantt=not args.no_gantt,
            log_level=log_level,
            session_name=args.session
        ))
        
        if result['success']:
            if not args.quiet:
                print_collection_summary(
                    result['results'], 
                    result['session_dir'], 
                    result['total_time']
                )
                print_usage_tips()
            
            print(f"\n🎉 数据采集完成！")
            print(f"   成功采集: {len([r for r in result['results'] if r.get('success', False)])}/{result['collections']}")
            print(f"   总耗时: {result['total_time']:.1f} 秒")
            
            return 0
        else:
            print(f"\n❌ 数据采集失败: {result.get('error', '未知错误')}")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断操作")
        return 130
    except Exception as e:
        print(f"\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
