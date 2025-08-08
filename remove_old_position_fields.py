#!/usr/bin/env python3
"""
移除旧的satellite_position字段并分析位置信息丢失原因
"""

import json
import sys
import os
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def remove_old_position_fields():
    """移除旧的satellite_position字段并分析位置信息丢失原因"""
    try:
        print("=" * 80)
        print("🔧 移除旧的satellite_position字段并分析位置信息丢失原因")
        print("=" * 80)
        
        # 查找最新的采集数据
        unified_dir = Path("output/unified_collections")
        latest_session = max([d for d in unified_dir.iterdir() if d.is_dir() and d.name.startswith("session_")], 
                           key=lambda x: x.stat().st_mtime)
        
        json_dir = latest_session / "json_data"
        original_files = list(json_dir.glob("*_original.json"))
        timeline_files = list(json_dir.glob("*_timeline.json"))
        
        latest_original_file = max(original_files, key=lambda x: x.stat().st_mtime)
        latest_timeline_file = max(timeline_files, key=lambda x: x.stat().st_mtime)
        
        print(f"📄 处理文件:")
        print(f"   原始数据: {latest_original_file.name}")
        print(f"   时间轴数据: {latest_timeline_file.name}")
        
        # 1. 分析原始数据中的位置字段
        print(f"\n📊 1. 分析原始数据中的位置字段:")
        
        with open(latest_original_file, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        visible_meta_tasks = original_data.get('visible_meta_tasks', {})
        constellation_sets = visible_meta_tasks.get('constellation_visible_task_sets', {})
        
        total_tasks = 0
        tasks_with_old_position = 0
        tasks_with_new_position_sync = 0
        tasks_with_both = 0
        tasks_with_neither = 0
        
        old_position_details = []
        new_position_details = []
        
        for satellite_id, satellite_data in constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])
                
                for task in visible_tasks:
                    total_tasks += 1
                    
                    has_old_position = 'satellite_position' in task
                    has_new_position_sync = 'satellite_position_sync' in task
                    
                    # 检查新位置同步是否有有效数据
                    has_valid_new_position = False
                    if has_new_position_sync:
                        position_sync = task['satellite_position_sync']
                        position_samples = position_sync.get('position_samples', [])
                        has_valid_new_position = len(position_samples) > 0
                    
                    if has_old_position:
                        tasks_with_old_position += 1
                        old_position_details.append({
                            'task_id': task.get('task_id'),
                            'satellite_id': satellite_id,
                            'missile_id': missile_id,
                            'old_position_data': task['satellite_position']
                        })
                    
                    if has_valid_new_position:
                        tasks_with_new_position_sync += 1
                        new_position_details.append({
                            'task_id': task.get('task_id'),
                            'satellite_id': satellite_id,
                            'missile_id': missile_id,
                            'sample_count': len(position_samples)
                        })
                    
                    if has_old_position and has_valid_new_position:
                        tasks_with_both += 1
                    elif not has_old_position and not has_valid_new_position:
                        tasks_with_neither += 1
        
        print(f"   总任务数: {total_tasks}")
        print(f"   含旧位置数据: {tasks_with_old_position}")
        print(f"   含新位置同步（有效）: {tasks_with_new_position_sync}")
        print(f"   同时含有两种位置数据: {tasks_with_both}")
        print(f"   两种位置数据都没有: {tasks_with_neither}")
        
        # 2. 分析位置信息丢失的可能原因
        print(f"\n🔍 2. 分析位置信息丢失的可能原因:")
        
        # 检查是否存在同时要求新旧字段的逻辑
        only_old_position = tasks_with_old_position - tasks_with_both
        only_new_position = tasks_with_new_position_sync - tasks_with_both
        
        print(f"   只有旧位置数据的任务: {only_old_position}")
        print(f"   只有新位置数据的任务: {only_new_position}")
        
        if only_old_position > 0:
            print(f"   ⚠️ 发现 {only_old_position} 个任务只有旧位置数据，可能存在位置信息丢失")
        
        if tasks_with_neither > 0:
            print(f"   ❌ 发现 {tasks_with_neither} 个任务没有任何位置数据")
        
        # 3. 检查时间轴转换器的逻辑
        print(f"\n🔧 3. 检查时间轴转换器的逻辑:")
        
        # 检查时间轴转换器是否只使用新字段
        with open(latest_timeline_file, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)
        
        timeline_tasks = timeline_data.get('visible_meta_task_timeline', {}).get('tasks', [])
        timeline_visible_tasks = [t for t in timeline_tasks if t.get('type') == 'visible_meta_task']
        timeline_tasks_with_position = [t for t in timeline_visible_tasks 
                                      if t.get('satellite_position_sync', {}).get('has_position_data', False)]
        
        print(f"   时间轴可见任务: {len(timeline_visible_tasks)}")
        print(f"   时间轴含位置数据: {len(timeline_tasks_with_position)}")
        
        # 检查是否有任务在转换过程中丢失位置数据
        original_task_ids_with_new_position = {detail['task_id'] for detail in new_position_details}
        timeline_task_ids_with_position = {t.get('task_id') for t in timeline_tasks_with_position}
        
        lost_in_conversion = original_task_ids_with_new_position - timeline_task_ids_with_position
        
        if lost_in_conversion:
            print(f"   ❌ 在时间轴转换中丢失位置数据的任务: {lost_in_conversion}")
        else:
            print(f"   ✅ 时间轴转换中没有丢失位置数据")
        
        # 4. 创建清理后的数据
        print(f"\n🧹 4. 创建清理后的数据:")
        
        cleaned_data = original_data.copy()
        cleaned_constellation_sets = cleaned_data['visible_meta_tasks']['constellation_visible_task_sets']
        
        removed_count = 0
        
        for satellite_id, satellite_data in cleaned_constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])
                
                for task in visible_tasks:
                    if 'satellite_position' in task:
                        del task['satellite_position']
                        removed_count += 1
        
        print(f"   移除了 {removed_count} 个旧位置字段")
        
        # 5. 保存清理后的数据
        cleaned_file = latest_original_file.parent / f"collection_001_original_cleaned.json"
        
        with open(cleaned_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)
        
        print(f"   清理后的数据已保存: {cleaned_file.name}")
        
        # 6. 重新生成时间轴数据
        print(f"\n🔄 6. 重新生成时间轴数据:")
        
        from src.utils.timeline_converter import TimelineConverter

        converter = TimelineConverter()
        new_timeline_data = converter.convert_collection_data(cleaned_data)
        
        # 保存新的时间轴数据
        new_timeline_file = latest_timeline_file.parent / f"collection_001_timeline_cleaned.json"
        
        with open(new_timeline_file, 'w', encoding='utf-8') as f:
            json.dump(new_timeline_data, f, indent=2, ensure_ascii=False)
        
        print(f"   新时间轴数据已保存: {new_timeline_file.name}")
        
        # 7. 对比分析
        print(f"\n📊 7. 对比分析:")
        
        new_timeline_tasks = new_timeline_data.get('visible_meta_task_timeline', {}).get('tasks', [])
        new_timeline_visible_tasks = [t for t in new_timeline_tasks if t.get('type') == 'visible_meta_task']
        new_timeline_tasks_with_position = [t for t in new_timeline_visible_tasks 
                                          if t.get('satellite_position_sync', {}).get('has_position_data', False)]
        
        print(f"   清理前时间轴含位置数据: {len(timeline_tasks_with_position)}")
        print(f"   清理后时间轴含位置数据: {len(new_timeline_tasks_with_position)}")
        
        if len(new_timeline_tasks_with_position) == len(timeline_tasks_with_position):
            print(f"   ✅ 清理旧字段后位置数据没有丢失")
        elif len(new_timeline_tasks_with_position) > len(timeline_tasks_with_position):
            print(f"   🎉 清理旧字段后位置数据增加了 {len(new_timeline_tasks_with_position) - len(timeline_tasks_with_position)} 个")
        else:
            print(f"   ❌ 清理旧字段后位置数据减少了 {len(timeline_tasks_with_position) - len(new_timeline_tasks_with_position)} 个")
        
        # 8. 分析结论
        print(f"\n💡 8. 分析结论:")
        
        if tasks_with_both == tasks_with_new_position_sync:
            print(f"   ✅ 所有有新位置数据的任务都同时有旧位置数据")
            print(f"   ✅ 不存在同时要求新旧字段的逻辑问题")
        else:
            print(f"   ⚠️ 存在只有新位置数据而没有旧位置数据的任务")
        
        if only_old_position > 0:
            print(f"   ⚠️ 存在只有旧位置数据的任务，可能需要检查位置同步逻辑")
        
        if tasks_with_neither > 0:
            print(f"   ❌ 存在没有任何位置数据的任务，需要检查位置获取流程")
        
        print(f"\n🎯 建议:")
        print(f"   1. 可以安全移除旧的satellite_position字段")
        print(f"   2. 专注于提升新位置同步机制的覆盖率")
        print(f"   3. 检查为什么只有 {tasks_with_new_position_sync}/{total_tasks} 个任务获取到位置数据")
        
        return True
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始移除旧位置字段分析...")
    
    success = remove_old_position_fields()
    
    if success:
        print(f"\n🎉 移除旧位置字段分析完成！")
    else:
        print(f"\n⚠️ 移除旧位置字段分析失败。")
