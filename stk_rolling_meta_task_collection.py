#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STK滚动元任务数据采集主程序
实现滚动数据采集，动态添加导弹，只采集中段飞行的导弹目标
"""

import sys
import os
import logging
import asyncio
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """设置日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('rolling_meta_task_collection.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

async def main():
    """主函数"""
    try:
        # 设置日志
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("🔄 启动STK滚动元任务数据采集系统")
        logger.info("=" * 80)
        
        # 导入系统
        from src.meta_task_main import MetaTaskDataCollectionSystem
        
        # 创建系统实例
        system = MetaTaskDataCollectionSystem()
        
        # 显示配置信息
        logger.info("📋 滚动采集配置:")
        rolling_config = system.rolling_data_collector.rolling_config
        logger.info(f"   总采集次数: {system.rolling_data_collector.total_collections}")
        logger.info(f"   采集间隔: {system.rolling_data_collector.interval_range[0]}-{system.rolling_data_collector.interval_range[1]}秒")
        logger.info(f"   最大并发导弹: {system.rolling_data_collector.max_concurrent_missiles}")
        logger.info(f"   每次添加导弹数: {system.rolling_data_collector.add_per_collection}")
        
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
                
                # 统计每次采集的导弹数
                for i, result in enumerate(results, 1):
                    rolling_info = result.get("rolling_collection_info", {})
                    midcourse_missiles = rolling_info.get("midcourse_missiles", [])
                    logger.info(f"   第{i}次采集: {len(midcourse_missiles)}个中段飞行导弹")
            
        else:
            logger.error("❌ 滚动元任务数据采集系统运行失败")
            
    except KeyboardInterrupt:
        logger.info("⚠️ 用户中断程序")
    except Exception as e:
        logger.error(f"❌ 主程序运行失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")

def show_help():
    """显示帮助信息"""
    print("""
🔄 STK滚动元任务数据采集系统

功能特点:
1. 🔄 滚动数据采集 - 多次采集，每次间隔随机时间
2. 🚀 动态导弹添加 - 每次采集时添加新导弹，发射时间为当前采集时刻
3. 🎯 中段飞行筛选 - 只采集当前时刻正在中段飞行的导弹
4. ⚖️ 并发数量控制 - 通过配置文件限制同时飞行的导弹数量

配置文件: config/config.yaml
- missile.max_concurrent_missiles: 最大并发导弹数
- data_collection.rolling_collection: 滚动采集配置

使用方法:
python stk_rolling_meta_task_collection.py

输出文件:
- output/data/rolling_meta_task_data_YYYYMMDD_HHMMSS.json (汇总数据)
- output/data/meta_task_data_YYYYMMDD_HHMMSS.json (每次采集数据)
- rolling_meta_task_collection.log (运行日志)
""")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help', 'help']:
        show_help()
    else:
        asyncio.run(main())
