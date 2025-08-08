#!/usr/bin/env python3
"""
分析可见任务的分布和卫星位置同步覆盖率问题
"""

import json
import sys
from pathlib import Path

def analyze_visible_tasks():
    """分析可见任务的分布"""
    
    # 读取原始数据
    original_file = Path("output/unified_collections/session_conflict_resolution_20250808_201710_20250808_201710/json_data/collection_001_original.json")
    
    if not original_file.exists():
        print(f"❌ 原始数据文件不存在: {original_file}")
        return
    
    with open(original_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("🔍 分析可见任务分布...")
    
    # 获取可见元任务数据
    visible_meta_tasks = data.get('visible_meta_tasks', {})
    constellation_sets = visible_meta_tasks.get('constellation_visible_task_sets', {})
    
    total_visible_tasks = 0
    tasks_with_position_sync = 0
    satellite_task_details = {}
    
    for satellite_id, satellite_data in constellation_sets.items():
        satellite_visible_count = 0
        satellite_sync_count = 0
        missile_details = {}
        
        missile_tasks = satellite_data.get('missile_tasks', {})
        
        for missile_id, missile_data in missile_tasks.items():
            visible_tasks = missile_data.get('visible_tasks', [])
            missile_visible_count = len(visible_tasks)
            missile_sync_count = 0
            
            # 检查每个可见任务是否有卫星位置同步
            for task in visible_tasks:
                total_visible_tasks += 1
                satellite_visible_count += 1
                
                # 检查是否有卫星位置同步数据
                if 'satellite_position_sync' in task:
                    tasks_with_position_sync += 1
                    satellite_sync_count += 1
                    missile_sync_count += 1
            
            if missile_visible_count > 0:
                missile_details[missile_id] = {
                    'visible_count': missile_visible_count,
                    'sync_count': missile_sync_count,
                    'coverage_ratio': missile_sync_count / missile_visible_count if missile_visible_count > 0 else 0
                }
        
        satellite_task_details[satellite_id] = {
            'visible_count': satellite_visible_count,
            'sync_count': satellite_sync_count,
            'coverage_ratio': satellite_sync_count / satellite_visible_count if satellite_visible_count > 0 else 0,
            'missiles': missile_details
        }
    
    print(f"\n📊 可见任务分析结果:")
    print(f"   总可见任务数: {total_visible_tasks}")
    print(f"   含位置同步的任务数: {tasks_with_position_sync}")
    print(f"   覆盖率: {tasks_with_position_sync/max(1, total_visible_tasks)*100:.1f}%")
    
    print(f"\n🛰️ 各卫星详细分析:")
    for satellite_id, details in satellite_task_details.items():
        if details['visible_count'] > 0:
            print(f"   {satellite_id}:")
            print(f"     可见任务: {details['visible_count']} 个")
            print(f"     含位置同步: {details['sync_count']} 个")
            print(f"     覆盖率: {details['coverage_ratio']*100:.1f}%")
            
            for missile_id, missile_details in details['missiles'].items():
                print(f"       {missile_id}: {missile_details['visible_count']} 个可见任务, {missile_details['sync_count']} 个含位置同步")
    
    # 分析卫星位置同步器的处理逻辑
    print(f"\n🔍 分析卫星位置同步器处理逻辑...")
    
    # 检查哪些任务被卫星位置同步器处理了
    processed_tasks = []
    for satellite_id, satellite_data in constellation_sets.items():
        missile_tasks = satellite_data.get('missile_tasks', {})
        for missile_id, missile_data in missile_tasks.items():
            visible_tasks = missile_data.get('visible_tasks', [])
            for task in visible_tasks:
                task_info = {
                    'satellite_id': satellite_id,
                    'missile_id': missile_id,
                    'task_id': task.get('task_id'),
                    'start_time': task.get('start_time'),
                    'start_time_iso': task.get('start_time_iso'),
                    'has_sync': 'satellite_position_sync' in task
                }
                processed_tasks.append(task_info)
    
    print(f"\n📋 所有可见任务详情:")
    for i, task in enumerate(processed_tasks, 1):
        sync_status = "✅" if task['has_sync'] else "❌"
        print(f"   {i}. {sync_status} {task['satellite_id']} - {task['missile_id']} - {task['task_id']}")
        print(f"      时间: {task['start_time']} / {task['start_time_iso']}")
    
    # 分析为什么只有部分任务有位置同步
    print(f"\n🤔 分析位置同步覆盖率问题:")
    
    # 检查时间格式问题
    time_format_issues = []
    for task in processed_tasks:
        if not task['has_sync']:
            if not task['start_time_iso'] or not task['start_time']:
                time_format_issues.append(task)
    
    if time_format_issues:
        print(f"   发现 {len(time_format_issues)} 个任务存在时间格式问题:")
        for task in time_format_issues:
            print(f"     - {task['satellite_id']} - {task['task_id']}: start_time={task['start_time']}, start_time_iso={task['start_time_iso']}")
    else:
        print(f"   ✅ 所有任务的时间格式都正常")
    
    # 检查是否存在其他模式
    sync_tasks = [task for task in processed_tasks if task['has_sync']]
    no_sync_tasks = [task for task in processed_tasks if not task['has_sync']]
    
    print(f"\n📈 同步状态分析:")
    print(f"   有同步的任务: {len(sync_tasks)} 个")
    print(f"   无同步的任务: {len(no_sync_tasks)} 个")
    
    if sync_tasks:
        print(f"   有同步的任务分布:")
        sync_satellites = {}
        for task in sync_tasks:
            if task['satellite_id'] not in sync_satellites:
                sync_satellites[task['satellite_id']] = []
            sync_satellites[task['satellite_id']].append(task)
        
        for sat_id, tasks in sync_satellites.items():
            print(f"     {sat_id}: {len(tasks)} 个任务")
    
    if no_sync_tasks:
        print(f"   无同步的任务分布:")
        no_sync_satellites = {}
        for task in no_sync_tasks:
            if task['satellite_id'] not in no_sync_satellites:
                no_sync_satellites[task['satellite_id']] = []
            no_sync_satellites[task['satellite_id']].append(task)
        
        for sat_id, tasks in no_sync_satellites.items():
            print(f"     {sat_id}: {len(tasks)} 个任务")

if __name__ == "__main__":
    analyze_visible_tasks()
