#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STK元任务数据采集脚本
使用STK场景采集包含meta_tasks和visible_meta_tasks的完整数据
用于aerospace_meta_task_gantt.py进行甘特图绘制

使用方法:
    python stk_meta_task_data_collection.py

输出:
    - 生成包含meta_tasks和visible_meta_tasks的JSON数据文件
    - 可直接用于aerospace_meta_task_gantt.py进行甘特图绘制
"""

import sys
import os
import logging
import json
import asyncio
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """设置日志"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"stk_meta_task_collection_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_filename, encoding='utf-8')
        ]
    )
    
    return log_filename

def print_banner():
    """打印横幅"""
    banner = """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                                                                              ║
    ║                🛰️ STK元任务数据采集系统                                      ║
    ║                                                                              ║
    ║   采集包含meta_tasks和visible_meta_tasks的完整数据                           ║
    ║   用于aerospace_meta_task_gantt.py进行专业甘特图绘制                        ║
    ║                                                                              ║
    ║   数据结构:                                                                  ║
    ║   • meta_tasks - 导弹元任务数据                                             ║
    ║   • visible_meta_tasks - 卫星可见元任务数据                                 ║
    ║   • constellation_data - 星座位置姿态数据                                   ║
    ║                                                                              ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

async def collect_meta_task_data():
    """采集元任务数据"""
    logger = logging.getLogger(__name__)
    
    try:
        print("🚀 启动STK元任务数据采集...")
        
        # 导入系统组件
        from src.meta_task_main import MetaTaskDataCollectionSystem
        
        # 创建元任务数据采集系统
        collection_system = MetaTaskDataCollectionSystem()
        
        # 设置采集模式为元任务模式
        collection_system.collection_mode = "meta_task"
        
        print("📡 连接STK并设置环境...")
        
        # 连接STK
        stk_connected = await collection_system._setup_stk_environment()
        if not stk_connected:
            print("❌ STK连接失败")
            return None
        
        print("✅ STK连接成功")
        
        # 设置星座
        print("🛰️ 创建Walker星座...")
        constellation_setup = await collection_system._setup_constellation()
        if not constellation_setup:
            print("❌ 星座设置失败")
            return None
        
        print("✅ Walker星座创建成功")
        
        # 设置导弹目标
        print("🚀 创建导弹目标...")
        missiles_setup = await collection_system._setup_initial_missiles()
        if not missiles_setup:
            print("❌ 导弹目标设置失败")
            return None
        
        print("✅ 导弹目标创建成功")
        
        # 执行单次元任务数据采集
        print("📊 执行元任务数据采集...")
        
        collection_time = datetime.now()
        meta_task_data = collection_system.meta_task_data_collector.collect_complete_meta_task_data(
            collection_time
        )
        
        if not meta_task_data:
            print("❌ 元任务数据采集失败")
            return None
        
        print("✅ 元任务数据采集成功")
        
        # 验证数据结构
        print("🔍 验证数据结构...")
        
        meta_tasks = meta_task_data.get('meta_tasks', {})
        visible_meta_tasks = meta_task_data.get('visible_meta_tasks', {})
        constellation_data = meta_task_data.get('constellation_data', {})
        
        # 统计信息
        missile_count = len(meta_tasks.get('meta_tasks', {}))
        satellite_count = len(visible_meta_tasks.get('constellation_visible_task_sets', {}))
        
        print(f"  📋 元任务数据: {missile_count} 个导弹")
        print(f"  👁️ 可见元任务数据: {satellite_count} 颗卫星")
        print(f"  🛰️ 星座数据: {len(constellation_data.get('satellites', []))} 颗卫星位置")
        
        # 详细统计
        total_atomic_tasks = 0
        total_visible_tasks = 0
        total_virtual_tasks = 0
        
        for missile_id, missile_data in meta_tasks.get('meta_tasks', {}).items():
            atomic_tasks = missile_data.get('atomic_tasks', [])
            total_atomic_tasks += len(atomic_tasks)
            print(f"    导弹 {missile_id}: {len(atomic_tasks)} 个元子任务")
        
        for satellite_id, satellite_data in visible_meta_tasks.get('constellation_visible_task_sets', {}).items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            sat_visible = 0
            sat_virtual = 0
            
            for missile_id, task_data in missile_tasks.items():
                visible_tasks = task_data.get('visible_tasks', [])
                virtual_tasks = task_data.get('virtual_tasks', [])
                sat_visible += len(visible_tasks)
                sat_virtual += len(virtual_tasks)
            
            total_visible_tasks += sat_visible
            total_virtual_tasks += sat_virtual
            print(f"    卫星 {satellite_id}: {sat_visible} 可见任务, {sat_virtual} 虚拟任务")
        
        print(f"\n📊 数据汇总:")
        print(f"  总元子任务: {total_atomic_tasks}")
        print(f"  总可见任务: {total_visible_tasks}")
        print(f"  总虚拟任务: {total_virtual_tasks}")
        
        # 保存数据
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"output/data/meta_task_data_{timestamp}.json"
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(meta_task_data, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 数据已保存: {output_filename}")
        
        return output_filename, meta_task_data
        
    except Exception as e:
        logger.error(f"❌ 元任务数据采集失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return None

def generate_gantt_chart(data_filename):
    """生成甘特图"""
    try:
        print(f"\n🎨 使用 {data_filename} 生成甘特图...")
        
        # 导入甘特图生成器
        from aerospace_meta_task_gantt import AerospaceMetaTaskGantt
        
        # 创建甘特图生成器
        gantt = AerospaceMetaTaskGantt()
        
        # 加载数据
        gantt.load_data(data_filename)
        
        # 提取元任务数据
        print("📊 提取元任务数据...")
        meta_df = gantt.extract_meta_task_data()
        print(f"✅ 提取到 {len(meta_df)} 条元任务数据")
        
        # 提取可见元任务数据
        print("👁️ 提取可见元任务数据...")
        visible_df = gantt.extract_visible_meta_task_data()
        print(f"✅ 提取到 {len(visible_df)} 条可见元任务数据")
        
        if len(meta_df) == 0 and len(visible_df) == 0:
            print("⚠️ 没有足够的数据生成甘特图")
            return False
        
        # 生成甘特图
        print("🎨 创建专业航天元任务甘特图...")
        result = gantt.create_professional_gantt_chart(
            meta_df, visible_df, time_window_hours=8
        )

        # 处理返回结果
        if len(result) == 4:
            fig, (ax1, ax2), saved_path, save_success = result
        else:
            fig, (ax1, ax2) = result
            save_success = True
        
        # 保存甘特图
        if len(result) == 4 and save_success:
            print(f"✅ 甘特图已保存: {saved_path}")
        else:
            # 兼容旧版本，手动保存
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            chart_filename = f"output/charts/meta_task_gantt_{timestamp}.png"

            # 确保输出目录存在
            os.makedirs(os.path.dirname(chart_filename), exist_ok=True)

            fig.savefig(chart_filename, dpi=300, bbox_inches='tight',
                       facecolor='white', edgecolor='none')

            print(f"✅ 甘特图已保存: {chart_filename}")
        
        # 显示图表
        import matplotlib.pyplot as plt
        plt.show()
        
        return True
        
    except Exception as e:
        print(f"❌ 甘特图生成失败: {e}")
        import traceback
        print(f"错误详情: {traceback.format_exc()}")
        return False

async def main():
    """主函数"""
    log_filename = setup_logging()
    logger = logging.getLogger(__name__)
    
    print_banner()
    
    print("🎯 STK元任务数据采集开始")
    print(f"📝 日志文件: {log_filename}")
    print("=" * 80)
    
    try:
        # 第1步: 采集元任务数据
        print("第1步: 采集STK元任务数据")
        result = await collect_meta_task_data()
        
        if result is None:
            print("❌ 数据采集失败，程序终止")
            return False
        
        data_filename, meta_task_data = result
        
        print("\n" + "=" * 80)
        
        # 第2步: 生成甘特图
        print("第2步: 生成航天元任务甘特图")
        gantt_success = generate_gantt_chart(data_filename)
        
        print("\n" + "=" * 80)
        
        # 总结
        if gantt_success:
            print("🎉 STK元任务数据采集和甘特图生成成功！")
            print("\n✅ 完成的任务:")
            print("  1. ✅ STK场景连接和设置")
            print("  2. ✅ Walker星座创建")
            print("  3. ✅ 导弹目标创建")
            print("  4. ✅ 元任务数据生成")
            print("  5. ✅ 可见元任务计算")
            print("  6. ✅ 数据结构验证")
            print("  7. ✅ 专业甘特图生成")
            
            print(f"\n📁 输出文件:")
            print(f"  📊 数据文件: {data_filename}")
            print(f"  📝 日志文件: {log_filename}")
            print(f"  🎨 甘特图: output/charts/meta_task_gantt_*.png")
        else:
            print("⚠️ 数据采集成功，但甘特图生成失败")
            print(f"📊 数据文件已保存: {data_filename}")
        
        return gantt_success
        
    except Exception as e:
        logger.error(f"❌ 主程序执行失败: {e}")
        import traceback
        logger.error(f"错误详情: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    
    if success:
        print("\n🎊 任务完成！STK元任务数据采集和甘特图生成成功。")
        print("\n💡 使用说明:")
        print("  • 生成的数据文件可重复用于甘特图生成")
        print("  • 修改aerospace_meta_task_gantt.py中的data_file路径")
        print("  • 运行aerospace_meta_task_gantt.py生成新的甘特图")
    else:
        print("\n❌ 任务未完全成功，请检查日志文件获取详细信息。")
    
    input("\n按回车键退出...")
