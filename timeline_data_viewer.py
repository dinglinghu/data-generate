#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间轴数据查看器
用于查看和验证转换后的元任务时间轴数据
"""

import json
import os
import glob
from datetime import datetime
from typing import Dict, List, Any


def load_timeline_data(file_path: str) -> Dict:
    """加载时间轴数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def print_collection_summary(collection_name: str, collection_data: Dict):
    """打印单次采集的摘要信息"""
    print(f"\n📊 {collection_name}")
    print("="*60)
    
    # 基本信息
    planning_period = collection_data.get('planning_period', {})
    print(f"⏰ 规划周期: {planning_period.get('start_time')} → {planning_period.get('end_time')}")
    print(f"⏱️ 持续时间: {planning_period.get('duration_hours', 0):.2f} 小时")
    
    # 元任务统计
    meta_timeline = collection_data.get('meta_task_timeline', {})
    print(f"🎯 元任务总数: {meta_timeline.get('total_count', 0)}")
    print(f"   真实任务: {meta_timeline.get('real_task_count', 0)}")
    print(f"   虚拟任务: {meta_timeline.get('virtual_task_count', 0)}")
    
    # 可见元任务统计
    visible_timeline = collection_data.get('visible_meta_task_timeline', {})
    print(f"👁️ 可见任务总数: {visible_timeline.get('total_count', 0)}")
    print(f"   可见元任务: {visible_timeline.get('visible_task_count', 0)}")
    print(f"   虚拟原子任务: {visible_timeline.get('virtual_atomic_task_count', 0)}")
    
    # 统计信息
    stats = collection_data.get('statistics', {})
    print(f"🚀 导弹数量: {stats.get('missile_count', 0)}")
    print(f"🛰️ 卫星数量: {stats.get('satellite_count', 0)}")
    print(f"📈 可见率: {stats.get('visibility_ratio', 0):.2%}")


def print_task_details(collection_name: str, collection_data: Dict, task_type: str = 'meta', limit: int = 5):
    """打印任务详细信息"""
    print(f"\n🔍 {collection_name} - {task_type.upper()}任务详情 (前{limit}个)")
    print("-"*80)
    
    if task_type == 'meta':
        tasks = collection_data.get('meta_task_timeline', {}).get('tasks', [])
    else:
        tasks = collection_data.get('visible_meta_task_timeline', {}).get('tasks', [])
    
    for i, task in enumerate(tasks[:limit]):
        print(f"📋 任务 {i+1}:")
        print(f"   类型: {task.get('type', 'N/A')}")
        if task_type == 'meta':
            print(f"   导弹: {task.get('missile_id', 'N/A')}")
        else:
            print(f"   卫星: {task.get('satellite_id', 'N/A')} → 导弹: {task.get('missile_id', 'N/A')}")
        print(f"   时间: {task.get('start_time', 'N/A')} → {task.get('end_time', 'N/A')}")
        print(f"   持续: {task.get('duration_seconds', 0):.0f}秒")
        if task_type == 'meta':
            print(f"   真实: {task.get('is_real_task', False)}, 虚拟: {task.get('is_virtual_task', False)}")
        print()


def print_global_statistics(data: Dict):
    """打印全局统计信息"""
    print("\n" + "="*80)
    print("🌍 全局统计信息")
    print("="*80)
    
    conversion_info = data.get('conversion_info', {})
    print(f"🔄 转换时间: {conversion_info.get('conversion_time', 'N/A')}")
    print(f"📁 总采集次数: {conversion_info.get('total_collections', 0)}")
    print(f"✅ 成功转换: {conversion_info.get('successful_conversions', 0)}")
    
    global_stats = data.get('global_statistics', {})
    print(f"\n📊 数据统计:")
    print(f"   总元任务数: {global_stats.get('total_meta_tasks', 0)}")
    print(f"   总可见任务数: {global_stats.get('total_visible_tasks', 0)}")
    print(f"   总虚拟原子任务数: {global_stats.get('total_virtual_atomic_tasks', 0)}")
    print(f"   唯一导弹数: {global_stats.get('unique_missiles', 0)}")
    print(f"   唯一卫星数: {global_stats.get('unique_satellites', 0)}")
    print(f"   平均可见率: {global_stats.get('average_visibility_ratio', 0):.2%}")


def analyze_timeline_data(file_path: str):
    """分析时间轴数据"""
    print("🔍 加载时间轴数据...")
    data = load_timeline_data(file_path)
    
    # 打印全局统计
    print_global_statistics(data)
    
    # 打印每次采集的摘要
    collections = data.get('collections', {})
    collection_names = sorted(collections.keys())
    
    print(f"\n📋 采集摘要 (共{len(collection_names)}次):")
    for collection_name in collection_names:
        collection_data = collections[collection_name]
        print_collection_summary(collection_name, collection_data)
    
    # 打印最后一次采集的详细信息
    if collection_names:
        last_collection = collection_names[-1]
        last_data = collections[last_collection]
        
        print(f"\n🔍 最后一次采集详细信息: {last_collection}")
        print_task_details(last_collection, last_data, 'meta', 3)
        print_task_details(last_collection, last_data, 'visible', 5)


def main():
    """主函数"""
    # 查找最新的时间轴数据文件
    # data_dir = 'output/data'
    data_files = glob.glob('output/rolling_collections/*/data/meta_task_data.json')
    
    if not timeline_files:
        print("❌ 未找到时间轴数据文件")
        return
    
    # 使用最新的文件
    latest_file = sorted(timeline_files)[-1]
    file_path = os.path.join(data_dir, latest_file)
    
    print(f"📁 使用数据文件: {latest_file}")
    analyze_timeline_data(file_path)


if __name__ == "__main__":
    main()
