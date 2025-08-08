#!/usr/bin/env python3
"""
调试位置数据来源
"""

import json
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_position_data_sources():
    """调试位置数据来源"""
    try:
        print("=" * 60)
        print("🔍 调试位置数据来源")
        print("=" * 60)
        
        # 查找最新的采集数据
        unified_dir = Path("output/unified_collections")
        
        if not unified_dir.exists():
            print("❌ 统一输出目录不存在")
            return False
        
        # 找到最新的会话目录
        session_dirs = [d for d in unified_dir.iterdir() if d.is_dir() and d.name.startswith("session_")]
        if not session_dirs:
            print("❌ 没有找到会话目录")
            return False
        
        latest_session = max(session_dirs, key=lambda x: x.stat().st_mtime)
        print(f"📁 使用会话目录: {latest_session.name}")
        
        # 查找原始数据文件
        json_dir = latest_session / "json_data"
        original_files = list(json_dir.glob("*_original.json"))
        latest_original_file = max(original_files, key=lambda x: x.stat().st_mtime)
        
        with open(latest_original_file, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        # 分析位置数据来源
        visible_meta_tasks = original_data.get('visible_meta_tasks', {})
        constellation_sets = visible_meta_tasks.get('constellation_visible_task_sets', {})
        
        print(f"\n📊 位置数据来源分析:")
        
        total_tasks = 0
        tasks_with_old_position = 0
        tasks_with_new_position_sync = 0
        tasks_with_both = 0
        
        # 详细分析前几个任务
        sample_tasks = []
        
        for satellite_id, satellite_data in constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])
                
                for task in visible_tasks:
                    total_tasks += 1
                    
                    has_old_position = 'satellite_position' in task
                    has_new_position_sync = 'satellite_position_sync' in task
                    
                    if has_old_position:
                        tasks_with_old_position += 1
                    if has_new_position_sync:
                        tasks_with_new_position_sync += 1
                    if has_old_position and has_new_position_sync:
                        tasks_with_both += 1
                    
                    # 收集前几个任务作为样本
                    if len(sample_tasks) < 5:
                        sample_tasks.append({
                            'task_id': task.get('task_id'),
                            'satellite_id': satellite_id,
                            'missile_id': missile_id,
                            'has_old_position': has_old_position,
                            'has_new_position_sync': has_new_position_sync,
                            'task_keys': list(task.keys())
                        })
        
        print(f"   总任务数: {total_tasks}")
        print(f"   含旧位置数据 (satellite_position): {tasks_with_old_position}")
        print(f"   含新位置同步 (satellite_position_sync): {tasks_with_new_position_sync}")
        print(f"   同时含有两种位置数据: {tasks_with_both}")
        
        print(f"\n📋 样本任务分析:")
        for i, task_info in enumerate(sample_tasks):
            print(f"   任务 {i+1}: {task_info['task_id']}")
            print(f"     卫星: {task_info['satellite_id']}, 导弹: {task_info['missile_id']}")
            print(f"     旧位置数据: {'✅' if task_info['has_old_position'] else '❌'}")
            print(f"     新位置同步: {'✅' if task_info['has_new_position_sync'] else '❌'}")
            print(f"     任务字段: {task_info['task_keys']}")
            print()
        
        # 详细分析一个有新位置同步的任务
        print(f"\n🔍 详细分析有新位置同步的任务:")
        for satellite_id, satellite_data in constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])
                
                for task in visible_tasks:
                    if 'satellite_position_sync' in task:
                        position_sync = task['satellite_position_sync']
                        position_samples = position_sync.get('position_samples', [])
                        
                        print(f"   任务ID: {task.get('task_id')}")
                        print(f"   卫星ID: {satellite_id}")
                        print(f"   开始时间: {task.get('start_time')}")
                        print(f"   结束时间: {task.get('end_time')}")
                        print(f"   位置样本数: {len(position_samples)}")
                        print(f"   采样间隔: {position_sync.get('sample_interval_seconds')}秒")
                        
                        if position_samples:
                            print(f"   样本时间:")
                            for i, sample in enumerate(position_samples[:5]):  # 只显示前5个
                                print(f"     {i+1}. {sample.get('sample_time')}")
                            if len(position_samples) > 5:
                                print(f"     ... 还有 {len(position_samples) - 5} 个样本")
                        
                        # 只分析第一个找到的任务
                        return True
        
        print(f"   ❌ 没有找到含有新位置同步的任务")
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始位置数据来源调试...")
    
    success = debug_position_data_sources()
    
    if success:
        print(f"\n🎉 位置数据来源调试完成！")
    else:
        print(f"\n⚠️ 位置数据来源调试失败。")
