#!/usr/bin/env python3
"""
调试位置同步覆盖率问题
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_position_sync_coverage():
    """调试位置同步覆盖率问题"""
    try:
        print("=" * 80)
        print("🔍 调试位置同步覆盖率问题")
        print("=" * 80)
        
        # 查找最新的采集数据
        unified_dir = Path("output/unified_collections")
        latest_session = max([d for d in unified_dir.iterdir() if d.is_dir() and d.name.startswith("session_")], 
                           key=lambda x: x.stat().st_mtime)
        
        json_dir = latest_session / "json_data"
        original_files = list(json_dir.glob("*_original.json"))
        latest_original_file = max(original_files, key=lambda x: x.stat().st_mtime)
        
        print(f"📄 分析文件: {latest_original_file.name}")
        
        with open(latest_original_file, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        # 获取时间管理器信息
        from src.utils.time_manager import get_time_manager
        time_manager = get_time_manager()
        
        print(f"\n⏰ STK场景时间范围:")
        print(f"   开始时间: {time_manager.start_time}")
        print(f"   结束时间: {time_manager.end_time}")
        print(f"   持续时间: {(time_manager.end_time - time_manager.start_time).total_seconds()}秒")
        
        # 分析所有可见任务
        visible_meta_tasks = original_data.get('visible_meta_tasks', {})
        constellation_sets = visible_meta_tasks.get('constellation_visible_task_sets', {})
        
        all_tasks = []
        successful_tasks = []
        failed_tasks = []
        
        for satellite_id, satellite_data in constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])
                
                for task in visible_tasks:
                    task_info = {
                        'task_id': task.get('task_id'),
                        'satellite_id': satellite_id,
                        'missile_id': missile_id,
                        'start_time': task.get('start_time'),
                        'end_time': task.get('end_time'),
                        'duration_seconds': task.get('duration_seconds', 0),
                        'has_new_position_sync': 'satellite_position_sync' in task
                    }
                    
                    # 检查时间范围
                    try:
                        start_time = datetime.fromisoformat(task_info['start_time'].replace('Z', '+00:00'))
                        end_time = datetime.fromisoformat(task_info['end_time'].replace('Z', '+00:00'))
                        
                        # 检查是否在STK场景时间范围内
                        in_time_range = (start_time >= time_manager.start_time and 
                                       end_time <= time_manager.end_time)
                        
                        task_info['start_time_parsed'] = start_time
                        task_info['end_time_parsed'] = end_time
                        task_info['in_stk_time_range'] = in_time_range
                        
                        # 计算时间偏移
                        start_offset = (start_time - time_manager.start_time).total_seconds()
                        end_offset = (end_time - time_manager.start_time).total_seconds()
                        
                        task_info['start_offset'] = start_offset
                        task_info['end_offset'] = end_offset
                        
                    except Exception as e:
                        task_info['time_parse_error'] = str(e)
                        task_info['in_stk_time_range'] = False
                    
                    all_tasks.append(task_info)
                    
                    if task_info['has_new_position_sync']:
                        # 检查是否有有效的位置样本
                        position_sync = task['satellite_position_sync']
                        position_samples = position_sync.get('position_samples', [])
                        if position_samples:
                            task_info['position_sample_count'] = len(position_samples)
                            successful_tasks.append(task_info)
                        else:
                            failed_tasks.append(task_info)
                    else:
                        failed_tasks.append(task_info)
        
        print(f"\n📊 任务分析结果:")
        print(f"   总任务数: {len(all_tasks)}")
        print(f"   成功获取位置: {len(successful_tasks)}")
        print(f"   失败任务: {len(failed_tasks)}")
        print(f"   成功率: {len(successful_tasks)/len(all_tasks)*100:.1f}%")
        
        # 分析失败原因
        print(f"\n🔍 失败原因分析:")
        
        # 1. 时间范围问题
        out_of_range_tasks = [t for t in failed_tasks if not t.get('in_stk_time_range', True)]
        print(f"   超出STK时间范围: {len(out_of_range_tasks)}个")
        
        # 2. 时间解析问题
        parse_error_tasks = [t for t in failed_tasks if 'time_parse_error' in t]
        print(f"   时间解析错误: {len(parse_error_tasks)}个")
        
        # 3. 卫星分布
        failed_satellites = {}
        successful_satellites = {}
        
        for task in failed_tasks:
            sat_id = task['satellite_id']
            failed_satellites[sat_id] = failed_satellites.get(sat_id, 0) + 1
        
        for task in successful_tasks:
            sat_id = task['satellite_id']
            successful_satellites[sat_id] = successful_satellites.get(sat_id, 0) + 1
        
        print(f"\n📊 按卫星分析:")
        print(f"   成功的卫星: {list(successful_satellites.keys())}")
        print(f"   失败的卫星: {list(failed_satellites.keys())}")
        
        # 检查是否有卫星完全失败
        all_satellites = set(failed_satellites.keys()) | set(successful_satellites.keys())
        completely_failed_satellites = [sat for sat in all_satellites if sat not in successful_satellites]
        
        if completely_failed_satellites:
            print(f"   完全失败的卫星: {completely_failed_satellites}")
        
        # 4. 时间分布分析
        print(f"\n⏰ 时间分布分析:")
        
        if successful_tasks:
            successful_start_times = [t['start_time_parsed'] for t in successful_tasks if 'start_time_parsed' in t]
            failed_start_times = [t['start_time_parsed'] for t in failed_tasks if 'start_time_parsed' in t]
            
            if successful_start_times:
                print(f"   成功任务时间范围: {min(successful_start_times)} - {max(successful_start_times)}")
            
            if failed_start_times:
                print(f"   失败任务时间范围: {min(failed_start_times)} - {max(failed_start_times)}")
        
        # 5. 详细分析前几个失败任务
        print(f"\n🔍 失败任务详细分析 (前5个):")
        
        for i, task in enumerate(failed_tasks[:5]):
            print(f"   {i+1}. {task['task_id']} ({task['satellite_id']} → {task['missile_id']})")
            print(f"      时间: {task['start_time']} - {task['end_time']}")
            print(f"      持续: {task['duration_seconds']}秒")
            print(f"      在STK时间范围内: {task.get('in_stk_time_range', 'unknown')}")
            if 'start_offset' in task:
                print(f"      时间偏移: {task['start_offset']:.1f}s - {task['end_offset']:.1f}s")
            if 'time_parse_error' in task:
                print(f"      时间解析错误: {task['time_parse_error']}")
            print()
        
        # 6. 成功任务分析
        print(f"\n✅ 成功任务分析:")
        
        for i, task in enumerate(successful_tasks):
            print(f"   {i+1}. {task['task_id']} ({task['satellite_id']} → {task['missile_id']})")
            print(f"      时间: {task['start_time']} - {task['end_time']}")
            print(f"      位置样本: {task.get('position_sample_count', 0)}个")
            if 'start_offset' in task:
                print(f"      时间偏移: {task['start_offset']:.1f}s - {task['end_offset']:.1f}s")
            print()
        
        # 7. 建议
        print(f"\n💡 建议:")
        
        if out_of_range_tasks:
            print(f"   1. 扩展STK场景时间范围以覆盖所有任务时间")
        
        if completely_failed_satellites:
            print(f"   2. 检查完全失败的卫星: {completely_failed_satellites}")
            print(f"      - 验证这些卫星在STK中是否存在")
            print(f"      - 检查这些卫星的传播器状态")
        
        if len(successful_tasks) < len(all_tasks) * 0.5:
            print(f"   3. 成功率较低，建议:")
            print(f"      - 检查STK连接稳定性")
            print(f"      - 增加位置获取的重试机制")
            print(f"      - 检查卫星轨道传播器配置")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始位置同步覆盖率调试...")
    
    success = debug_position_sync_coverage()
    
    if success:
        print(f"\n🎉 位置同步覆盖率调试完成！")
    else:
        print(f"\n⚠️ 位置同步覆盖率调试失败。")
