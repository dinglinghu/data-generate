#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STK滚动元任务数据采集主程序
实现滚动数据采集，动态添加导弹，只采集中段飞行的导弹目标

优化功能:
1. 可选择是否保存甘特图
2. 运行一次仿真相同类型的数据放在一个文件夹下
"""

import sys
import os
import logging
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging(session_id: str):
    """设置日志配置"""
    # 从配置获取日志目录
    try:
        from src.utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        output_config = config_manager.get_output_config()
        log_directory = output_config.get("log_directory", "logs")
        log_prefix = output_config.get("file_naming", {}).get("log_prefix", "rolling_collection_")
    except:
        log_directory = "logs"
        log_prefix = "rolling_collection_"

    log_dir = Path(log_directory)
    log_dir.mkdir(exist_ok=True)

    # 创建自定义的StreamHandler来处理编码问题
    import sys

    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                msg = self.format(record)
                # 尝试安全地输出消息
                try:
                    print(msg)
                except UnicodeEncodeError:
                    # 如果有编码问题，移除特殊字符
                    safe_msg = msg.encode('ascii', 'ignore').decode('ascii')
                    print(safe_msg)
            except Exception:
                self.handleError(record)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / f'{log_prefix}{session_id}.log', encoding='utf-8'),
            SafeStreamHandler()
        ]
    )

def safe_log_info(logger, message):
    """安全的日志输出函数"""
    try:
        logger.info(message)
    except UnicodeEncodeError:
        # 移除emoji字符，保留基本信息
        safe_message = message.encode('ascii', 'ignore').decode('ascii')
        logger.info(safe_message)

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="STK滚动元任务数据采集系统")

    # 甘特图生成控制 - 使用互斥组确保逻辑清晰
    gantt_group = parser.add_mutually_exclusive_group()
    gantt_group.add_argument("--no-gantt", action="store_true",
                           help="禁用甘特图生成（提升性能）")
    gantt_group.add_argument("--enable-gantt", action="store_true",
                           help="明确启用甘特图生成（默认已启用）")
    parser.add_argument("--session-name", type=str,
                       help="自定义会话名称（用于文件夹命名）")
    parser.add_argument("--collections", "-n", type=int,
                       help="总采集次数")
    parser.add_argument("--interval", "-i", type=str,
                       help="采集间隔范围，格式: min,max (秒)")
    parser.add_argument("--missiles", "-m", type=int,
                       help="最大并发导弹数")
    parser.add_argument("--output-dir", type=str, default="output/unified_collections",
                       help="输出目录（默认: output/unified_collections）")

    return parser.parse_args()

def create_session_directory(output_dir: str, session_name: str = None) -> Path:
    """创建会话目录"""
    base_dir = Path(output_dir)

    if session_name:
        # 使用自定义会话名称
        session_dir = base_dir / f"session_{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        # 使用默认时间戳命名
        session_dir = base_dir / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 创建目录结构
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / "data").mkdir(exist_ok=True)
    (session_dir / "charts").mkdir(exist_ok=True)
    (session_dir / "logs").mkdir(exist_ok=True)
    (session_dir / "collections").mkdir(exist_ok=True)

    return session_dir

async def main():
    """主函数"""
    try:
        # 解析命令行参数
        args = parse_arguments()

        # 生成会话ID
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 设置日志
        setup_logging(session_id)
        logger = logging.getLogger(__name__)

        safe_log_info(logger, "启动STK滚动元任务数据采集系统")
        logger.info("=" * 80)

        # 创建会话目录
        session_dir = create_session_directory(args.output_dir, args.session_name)
        safe_log_info(logger, f"会话目录: {session_dir}")

        # 确定甘特图生成设置 - 修复逻辑
        enable_gantt = True  # 默认启用
        if args.no_gantt:
            enable_gantt = False
            safe_log_info(logger, "甘特图生成: 禁用 (--no-gantt)")
        elif args.enable_gantt:
            enable_gantt = True
            safe_log_info(logger, "甘特图生成: 启用 (--enable-gantt)")
        else:
            safe_log_info(logger, "甘特图生成: 启用 (默认)")

        # 导入系统
        from src.meta_task_main import MetaTaskDataCollectionSystem

        # 创建系统实例
        system = MetaTaskDataCollectionSystem()

        # 应用命令行参数配置
        if args.collections:
            system.rolling_data_collector.total_collections = args.collections
            safe_log_info(logger, f"设置总采集次数: {args.collections}")

        if args.interval:
            try:
                min_interval, max_interval = map(int, args.interval.split(','))
                system.rolling_data_collector.interval_range = [min_interval, max_interval]
                safe_log_info(logger, f"设置采集间隔: {min_interval}-{max_interval}秒")
            except ValueError:
                logger.warning(f"采集间隔格式错误: {args.interval}，使用默认值")

        if args.missiles:
            system.rolling_data_collector.max_concurrent_missiles = args.missiles
            safe_log_info(logger, f"设置最大并发导弹数: {args.missiles}")

        # 配置输出目录和甘特图设置
        system.rolling_data_collector.output_base_dir = session_dir
        system.rolling_data_collector.enable_gantt = enable_gantt

        # 显示配置信息
        logger.info("📋 滚动采集配置:")
        logger.info(f"   总采集次数: {system.rolling_data_collector.total_collections}")
        logger.info(f"   采集间隔: {system.rolling_data_collector.interval_range[0]}-{system.rolling_data_collector.interval_range[1]}秒")
        logger.info(f"   最大并发导弹: {system.rolling_data_collector.max_concurrent_missiles}")
        logger.info(f"   导弹数量范围: {system.rolling_data_collector.missile_count_range}")
        logger.info(f"   清理现有导弹: {system.rolling_data_collector.clear_existing_missiles}")
        logger.info(f"   输出目录: {session_dir}")

        # 运行滚动数据采集系统
        logger.info("\n🚀 开始滚动数据采集...")
        success = await system.run_rolling_collection_system()

        if success:
            logger.info("\n" + "=" * 80)
            logger.info("🎉 滚动元任务数据采集系统运行成功！")

            # 显示结果统计
            results = system.rolling_data_collector.collection_results
            if results:
                logger.info(f"📊 采集结果统计:")
                logger.info(f"   成功采集次数: {len(results)}")
                logger.info(f"   总导弹数: {len(system.rolling_data_collector.all_missiles)}")
                logger.info(f"   会话目录: {session_dir}")

                # 统计每次采集的导弹数
                for i, result in enumerate(results, 1):
                    rolling_info = result.get("rolling_collection_info", {})
                    midcourse_missiles = rolling_info.get("midcourse_missiles", [])
                    logger.info(f"   第{i}次采集: {len(midcourse_missiles)}个中段飞行导弹")

                # 结束统一数据管理会话
                await system.rolling_data_collector.finalize_session()

                # 生成会话汇总报告
                await generate_session_summary(session_dir, results, system, enable_gantt)

        else:
            logger.error("❌ 滚动元任务数据采集系统运行失败")

    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断程序")
    except Exception as e:
        logger.error(f"❌ 主程序运行失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")

async def generate_session_summary(session_dir: Path, results: list, system, enable_gantt: bool):
    """生成会话汇总报告"""
    try:
        logger = logging.getLogger(__name__)
        logger.info("📋 生成会话汇总报告...")

        import json

        # 准备汇总数据
        summary_data = {
            "session_info": {
                "session_id": session_dir.name,
                "start_time": datetime.now().isoformat(),
                "total_collections": len(results),
                "enable_gantt": enable_gantt,
                "output_directory": str(session_dir)
            },
            "configuration": {
                "total_collections": system.rolling_data_collector.total_collections,
                "interval_range": system.rolling_data_collector.interval_range,
                "max_concurrent_missiles": system.rolling_data_collector.max_concurrent_missiles,
                "missile_count_range": system.rolling_data_collector.missile_count_range,
                "clear_existing_missiles": system.rolling_data_collector.clear_existing_missiles
            },
            "statistics": {
                "successful_collections": len(results),
                "total_missiles_created": len(system.rolling_data_collector.all_missiles),
                "unique_missiles": len(set().union(*[result.get("rolling_collection_info", {}).get("midcourse_missiles", [])
                                                   for result in results])) if results else 0
            },
            "collection_details": []
        }

        # 添加每次采集的详细信息
        for i, result in enumerate(results, 1):
            rolling_info = result.get("rolling_collection_info", {})
            midcourse_missiles = rolling_info.get("midcourse_missiles", [])

            collection_detail = {
                "collection_number": i,
                "collection_time": rolling_info.get("collection_time"),
                "midcourse_missiles_count": len(midcourse_missiles),
                "midcourse_missiles": midcourse_missiles,
                "data_file": f"collections/collection_{i:03d}/data/meta_task_data.json"
            }

            if enable_gantt:
                collection_detail["gantt_chart"] = f"collections/collection_{i:03d}/charts/collection_{i:02d}_aerospace_meta_task_gantt.png"

            summary_data["collection_details"].append(collection_detail)

        # 保存汇总报告
        summary_file = session_dir / "session_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False, default=str)

        # 生成可读的文本报告
        text_summary_file = session_dir / "session_summary.txt"
        with open(text_summary_file, 'w', encoding='utf-8') as f:
            f.write("STK滚动元任务数据采集会话汇总报告\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"会话ID: {summary_data['session_info']['session_id']}\n")
            f.write(f"开始时间: {summary_data['session_info']['start_time']}\n")
            f.write(f"总采集次数: {summary_data['session_info']['total_collections']}\n")
            f.write(f"甘特图生成: {'启用' if enable_gantt else '禁用'}\n\n")

            f.write("配置信息:\n")
            f.write(f"  计划采集次数: {summary_data['configuration']['total_collections']}\n")
            f.write(f"  采集间隔: {summary_data['configuration']['interval_range']}秒\n")
            f.write(f"  最大并发导弹: {summary_data['configuration']['max_concurrent_missiles']}\n")
            f.write(f"  导弹数量范围: {summary_data['configuration']['missile_count_range']}\n")
            f.write(f"  清理现有导弹: {summary_data['configuration']['clear_existing_missiles']}\n\n")

            f.write("统计信息:\n")
            f.write(f"  成功采集次数: {summary_data['statistics']['successful_collections']}\n")
            f.write(f"  创建导弹总数: {summary_data['statistics']['total_missiles_created']}\n")
            f.write(f"  唯一导弹数: {summary_data['statistics']['unique_missiles']}\n\n")

            f.write("采集详情:\n")
            for detail in summary_data["collection_details"]:
                f.write(f"  第{detail['collection_number']}次采集:\n")
                f.write(f"    时间: {detail['collection_time']}\n")
                f.write(f"    中段飞行导弹数: {detail['midcourse_missiles_count']}\n")
                f.write(f"    数据文件: {detail['data_file']}\n")
                if enable_gantt:
                    f.write(f"    甘特图: {detail['gantt_chart']}\n")
                f.write("\n")

        logger.info(f"📋 会话汇总报告已保存:")
        logger.info(f"   JSON格式: {summary_file}")
        logger.info(f"   文本格式: {text_summary_file}")

    except Exception as e:
        logger.error(f"❌ 生成会话汇总报告失败: {e}")

def show_help():
    """显示帮助信息"""
    help_text = """
STK滚动元任务数据采集系统 (优化版)

功能特点:
1. 滚动数据采集 - 多次采集，每次间隔随机时间
2. 动态导弹添加 - 每次采集时添加新导弹，发射时间为当前采集时刻
3. 中段飞行筛选 - 只采集当前时刻正在中段飞行的导弹
4. 并发数量控制 - 通过配置文件限制同时飞行的导弹数量
5. 可选甘特图生成 - 可选择是否生成甘特图（提升性能）
6. 统一文件夹管理 - 一次仿真的所有数据放在同一个会话文件夹下

使用方法:
# 基本使用（默认启用甘特图）
python stk_rolling_meta_task_collection.py

# 禁用甘特图生成（提升性能）
python stk_rolling_meta_task_collection.py --no-gantt

# 明确启用甘特图生成
python stk_rolling_meta_task_collection.py --enable-gantt

# 自定义参数
python stk_rolling_meta_task_collection.py --collections 15 --interval 180,600 --missiles 8

# 自定义会话名称
python stk_rolling_meta_task_collection.py --session-name "test_scenario" --no-gantt

命令行参数:
  --no-gantt              禁用甘特图生成（提升性能，与--enable-gantt互斥）
  --enable-gantt          明确启用甘特图生成（默认已启用，与--no-gantt互斥）
  --session-name NAME     自定义会话名称
  --collections N         总采集次数
  --interval MIN,MAX      采集间隔范围（秒）
  --missiles N            最大并发导弹数
  --output-dir DIR        输出目录

输出结构:
output/unified_collections/session_YYYYMMDD_HHMMSS/
├── json_data/            # 统一的JSON数据文件
│   ├── collection_001_original.json      # 第1次采集原始数据
│   ├── collection_001_conflict_resolution.json  # 冲突消解数据
│   ├── collection_001_timeline.json      # 时间轴数据
│   ├── collection_001_summary.json       # 采集摘要
│   └── ...
├── data/                 # 会话级汇总数据
├── charts/               # 会话级图表
├── logs/                 # 日志文件
├── session_summary.json  # 会话汇总报告（JSON）
└── session_summary.txt   # 会话汇总报告（文本）

配置文件: config/config.yaml
- missile.max_concurrent_missiles: 最大并发导弹数
- data_collection.rolling_collection: 滚动采集配置

性能建议:
- 大规模采集时使用 --no-gantt 禁用甘特图生成以提升性能
- 使用 --enable-gantt 明确启用甘特图生成（默认已启用）
- 使用 --session-name 为不同测试场景命名
- 合理设置采集间隔和并发导弹数

甘特图说明:
- 默认情况下，每次采集都会生成甘特图
- 甘特图保存在 collections/collection_XXX/charts/ 目录下
- 甘特图文件名格式: collection_XX_aerospace_meta_task_gantt.png
- 使用 --no-gantt 可以禁用甘特图生成以提升性能
"""

    try:
        print(help_text)
    except UnicodeEncodeError:
        # 如果仍然有编码问题，使用ASCII版本
        ascii_help = help_text.encode('ascii', 'ignore').decode('ascii')
        print(ascii_help)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
    else:
        asyncio.run(main())
