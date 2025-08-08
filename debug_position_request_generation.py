#!/usr/bin/env python3
"""
调试位置请求生成问题
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def debug_position_request_generation():
    """调试位置请求生成"""
    
    # 读取原始数据
    original_file = Path("output/unified_collections/session_conflict_resolution_20250808_201710_20250808_201710/json_data/collection_001_original.json")
    
    if not original_file.exists():
        print(f"❌ 原始数据文件不存在: {original_file}")
        return
    
    with open(original_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print("🔍 调试位置请求生成...")
    
    # 获取可见元任务数据
    visible_meta_tasks = data.get('visible_meta_tasks', {})
    constellation_sets = visible_meta_tasks.get('constellation_visible_task_sets', {})
    
    print(f"\n📊 星座可见任务集分析:")
    print(f"   卫星数量: {len(constellation_sets)}")
    
    total_visible_tasks = 0
    successful_requests = 0
    failed_requests = 0
    
    for satellite_id, satellite_data in constellation_sets.items():
        print(f"\n🛰️ 卫星 {satellite_id}:")
        
        missile_tasks = satellite_data.get('missile_tasks', {})
        satellite_visible_count = 0
        satellite_request_count = 0
        
        for missile_id, missile_data in missile_tasks.items():
            visible_tasks = missile_data.get('visible_tasks', [])
            missile_visible_count = len(visible_tasks)
            satellite_visible_count += missile_visible_count
            
            if missile_visible_count > 0:
                print(f"   导弹 {missile_id}: {missile_visible_count} 个可见任务")
                
                for i, task in enumerate(visible_tasks, 1):
                    task_id = task.get('task_id')
                    start_time_str = task.get("start_time_iso") or task.get("start_time")
                    end_time_str = task.get("end_time_iso") or task.get("end_time")
                    
                    print(f"     任务 {i}: {task_id}")
                    print(f"       开始时间: {start_time_str}")
                    print(f"       结束时间: {end_time_str}")
                    
                    # 模拟位置请求生成逻辑
                    try:
                        if not start_time_str or not end_time_str:
                            print(f"       ❌ 时间范围无效")
                            failed_requests += 1
                            continue
                        
                        # 转换时间格式
                        try:
                            # 首先尝试ISO格式
                            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                        except ValueError:
                            # 如果ISO格式失败，尝试标准格式
                            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                            end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                        
                        # 计算采样时间点（模拟）
                        duration = (end_time - start_time).total_seconds()
                        sample_count = 2  # 开始和结束时刻
                        
                        print(f"       ✅ 时间解析成功，持续时间: {duration}秒")
                        print(f"       📍 生成 {sample_count} 个位置请求")
                        
                        satellite_request_count += sample_count
                        successful_requests += 1
                        
                    except Exception as e:
                        print(f"       ❌ 位置请求生成失败: {e}")
                        failed_requests += 1
        
        total_visible_tasks += satellite_visible_count
        print(f"   小计: {satellite_visible_count} 个可见任务, {satellite_request_count} 个位置请求")
    
    print(f"\n📊 总体统计:")
    print(f"   总可见任务数: {total_visible_tasks}")
    print(f"   成功生成请求的任务: {successful_requests}")
    print(f"   失败的任务: {failed_requests}")
    print(f"   成功率: {successful_requests/max(1, total_visible_tasks)*100:.1f}%")
    
    # 检查实际的卫星位置同步数据
    print(f"\n🔍 检查实际的卫星位置同步数据:")
    
    tasks_with_sync = []
    for satellite_id, satellite_data in constellation_sets.items():
        missile_tasks = satellite_data.get('missile_tasks', {})
        
        for missile_id, missile_data in missile_tasks.items():
            visible_tasks = missile_data.get('visible_tasks', [])
            
            for task in visible_tasks:
                task_id = task.get('task_id')
                has_sync = 'satellite_position_sync' in task
                
                if has_sync:
                    sync_data = task['satellite_position_sync']
                    sample_count = len(sync_data.get('position_samples', []))
                    tasks_with_sync.append({
                        'satellite_id': satellite_id,
                        'missile_id': missile_id,
                        'task_id': task_id,
                        'sample_count': sample_count
                    })
                    print(f"   ✅ {satellite_id} - {missile_id} - {task_id}: {sample_count} 个位置样本")
    
    print(f"\n🤔 分析差异:")
    print(f"   理论上应该处理: {total_visible_tasks} 个任务")
    print(f"   实际处理了: {len(tasks_with_sync)} 个任务")
    print(f"   差异: {total_visible_tasks - len(tasks_with_sync)} 个任务")
    
    if total_visible_tasks != len(tasks_with_sync):
        print(f"\n❌ 发现问题：卫星位置同步器没有处理所有可见任务！")
        
        # 找出未处理的任务
        processed_task_keys = {f"{task['satellite_id']}-{task['missile_id']}-{task['task_id']}" for task in tasks_with_sync}

        print(f"\n📋 未处理的任务:")
        unprocessed_count = 0
        for satellite_id, satellite_data in constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})

            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])

                for task in visible_tasks:
                    task_id = task.get('task_id')
                    task_key = f"{satellite_id}-{missile_id}-{task_id}"
                    if task_key not in processed_task_keys:
                        unprocessed_count += 1
                        print(f"   {unprocessed_count}. {satellite_id} - {missile_id} - {task_id}")
                        print(f"      开始时间: {task.get('start_time_iso') or task.get('start_time')}")
                        print(f"      结束时间: {task.get('end_time_iso') or task.get('end_time')}")

        if unprocessed_count == 0:
            print(f"   (无未处理任务，但统计数字不匹配)")
    else:
        print(f"\n✅ 所有可见任务都被正确处理了")

if __name__ == "__main__":
    debug_position_request_generation()
