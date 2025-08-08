#!/usr/bin/env python3
"""
全面分析系统中的卫星位置获取机制
"""

import json
import sys
import os
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def comprehensive_position_system_analysis():
    """全面分析系统中的卫星位置获取机制"""
    try:
        print("=" * 80)
        print("🔍 全面分析系统中的卫星位置获取机制")
        print("=" * 80)
        
        # 1. 分析最新的数据采集结果
        print(f"\n📊 1. 分析最新数据采集结果:")
        
        unified_dir = Path("output/unified_collections")
        latest_session = max([d for d in unified_dir.iterdir() if d.is_dir() and d.name.startswith("session_")], 
                           key=lambda x: x.stat().st_mtime)
        
        json_dir = latest_session / "json_data"
        original_files = list(json_dir.glob("*_original.json"))
        timeline_files = list(json_dir.glob("*_timeline.json"))
        
        latest_original_file = max(original_files, key=lambda x: x.stat().st_mtime)
        latest_timeline_file = max(timeline_files, key=lambda x: x.stat().st_mtime)
        
        print(f"   📄 原始数据: {latest_original_file.name}")
        print(f"   📄 时间轴数据: {latest_timeline_file.name}")
        
        # 加载数据
        with open(latest_original_file, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        with open(latest_timeline_file, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)
        
        # 2. 分析位置获取路径
        print(f"\n🛰️ 2. 位置获取路径分析:")
        
        # 2.1 位置同步器路径
        print(f"\n   2.1 位置同步器 (satellite_position_synchronizer.py):")
        visible_meta_tasks = original_data.get('visible_meta_tasks', {})
        position_sync_metadata = visible_meta_tasks.get('position_sync_metadata', {})
        
        if position_sync_metadata:
            print(f"     ✅ 位置同步元数据存在")
            print(f"     同步时间: {position_sync_metadata.get('sync_time')}")
            print(f"     处理任务数: {position_sync_metadata.get('total_tasks_processed', 0)}")
            print(f"     采集位置数: {position_sync_metadata.get('total_positions_collected', 0)}")
            print(f"     采样间隔: {position_sync_metadata.get('sample_interval_seconds', 0)}秒")
            print(f"     处理时间: {position_sync_metadata.get('processing_time_seconds', 0):.2f}秒")
            print(f"     并发启用: {position_sync_metadata.get('concurrent_enabled', False)}")
            print(f"     同步状态: {position_sync_metadata.get('sync_status', 'unknown')}")
        else:
            print(f"     ❌ 位置同步元数据不存在")
        
        # 2.2 分析原始数据中的位置信息
        print(f"\n   2.2 原始数据中的位置信息:")
        constellation_sets = visible_meta_tasks.get('constellation_visible_task_sets', {})
        
        total_visible_tasks = 0
        tasks_with_position_sync = 0
        position_sync_details = []
        
        for satellite_id, satellite_data in constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])
                
                for task in visible_tasks:
                    total_visible_tasks += 1
                    
                    if 'satellite_position_sync' in task:
                        position_sync = task['satellite_position_sync']
                        position_samples = position_sync.get('position_samples', [])
                        
                        if position_samples:
                            tasks_with_position_sync += 1
                            position_sync_details.append({
                                'task_id': task.get('task_id'),
                                'satellite_id': satellite_id,
                                'missile_id': missile_id,
                                'sample_count': len(position_samples),
                                'sync_time': position_sync.get('sync_time'),
                                'sample_interval': position_sync.get('sample_interval_seconds'),
                                'first_sample_time': position_samples[0].get('sample_time') if position_samples else None,
                                'last_sample_time': position_samples[-1].get('sample_time') if position_samples else None
                            })
        
        print(f"     总可见任务: {total_visible_tasks}")
        print(f"     含位置同步: {tasks_with_position_sync}")
        print(f"     位置同步成功率: {tasks_with_position_sync/max(1, total_visible_tasks)*100:.1f}%")
        
        # 显示位置同步详情
        if position_sync_details:
            print(f"\n     位置同步详情 (前5个):")
            for i, detail in enumerate(position_sync_details[:5]):
                print(f"       {i+1}. {detail['satellite_id']} → {detail['missile_id']}")
                print(f"          任务ID: {detail['task_id']}")
                print(f"          样本数: {detail['sample_count']}")
                print(f"          采样间隔: {detail['sample_interval']}秒")
                print(f"          时间范围: {detail['first_sample_time']} - {detail['last_sample_time']}")
        
        # 2.3 分析时间轴数据中的位置信息
        print(f"\n   2.3 时间轴数据中的位置信息:")
        visible_meta_task_timeline = timeline_data.get('visible_meta_task_timeline', {})
        timeline_tasks = visible_meta_task_timeline.get('tasks', [])
        
        timeline_visible_tasks = [t for t in timeline_tasks if t.get('type') == 'visible_meta_task']
        timeline_tasks_with_position = [t for t in timeline_visible_tasks 
                                      if t.get('satellite_position_sync', {}).get('has_position_data', False)]
        
        print(f"     时间轴可见任务: {len(timeline_visible_tasks)}")
        print(f"     含位置数据: {len(timeline_tasks_with_position)}")
        print(f"     位置覆盖率: {len(timeline_tasks_with_position)/max(1, len(timeline_visible_tasks))*100:.1f}%")
        
        # 检查位置数据传递的一致性
        print(f"\n   2.4 位置数据传递一致性检查:")
        print(f"     原始数据 → 时间轴数据:")
        print(f"     可见任务: {total_visible_tasks} → {len(timeline_visible_tasks)}")
        print(f"     含位置: {tasks_with_position_sync} → {len(timeline_tasks_with_position)}")
        
        if tasks_with_position_sync == len(timeline_tasks_with_position):
            print(f"     ✅ 位置数据传递一致")
        else:
            print(f"     ❌ 位置数据传递不一致")
            
            # 详细分析不一致的原因
            print(f"\n     不一致分析:")
            
            # 检查原始数据中有位置但时间轴中没有的任务
            original_task_ids_with_position = {detail['task_id'] for detail in position_sync_details}
            timeline_task_ids_with_position = {t.get('task_id') for t in timeline_tasks_with_position}
            
            missing_in_timeline = original_task_ids_with_position - timeline_task_ids_with_position
            extra_in_timeline = timeline_task_ids_with_position - original_task_ids_with_position
            
            if missing_in_timeline:
                print(f"       原始有位置但时间轴缺失: {missing_in_timeline}")
            if extra_in_timeline:
                print(f"       时间轴有位置但原始缺失: {extra_in_timeline}")
        
        # 3. 分析位置数据质量
        print(f"\n🔍 3. 位置数据质量分析:")
        
        if position_sync_details:
            sample_counts = [detail['sample_count'] for detail in position_sync_details]
            sample_intervals = [detail['sample_interval'] for detail in position_sync_details if detail['sample_interval']]
            
            print(f"   样本数统计:")
            print(f"     最小样本数: {min(sample_counts)}")
            print(f"     最大样本数: {max(sample_counts)}")
            print(f"     平均样本数: {sum(sample_counts)/len(sample_counts):.1f}")
            
            if sample_intervals:
                print(f"   采样间隔统计:")
                print(f"     采样间隔: {set(sample_intervals)} 秒")
            
            # 验证优化效果
            if all(count == 2 for count in sample_counts):
                print(f"   ✅ 优化验证: 所有任务都只有2个样本 (开始+结束)")
            elif all(count <= 3 for count in sample_counts):
                print(f"   ⚠️ 优化部分生效: 样本数在2-3之间")
            else:
                print(f"   ❌ 优化未生效: 仍有任务超过3个样本")
        
        # 4. 检查其他位置获取路径
        print(f"\n🔧 4. 其他位置获取路径检查:")
        
        # 4.1 检查是否有旧的位置数据字段
        print(f"\n   4.1 检查旧位置数据字段:")
        old_position_count = 0
        
        for satellite_id, satellite_data in constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])
                
                for task in visible_tasks:
                    if 'satellite_position' in task:  # 旧字段
                        old_position_count += 1
        
        print(f"     含旧位置字段的任务: {old_position_count}")
        
        # 4.2 检查元任务数据收集器的位置增强
        print(f"\n   4.2 元任务数据收集器位置增强:")
        meta_task_data = original_data.get('meta_task_data', {})
        enhancement_info = meta_task_data.get('enhancement_info', {})
        
        if enhancement_info:
            print(f"     ✅ 位置增强信息存在")
            print(f"     匹配卫星: {enhancement_info.get('matched_satellites', 0)}")
            print(f"     增强任务: {enhancement_info.get('enhanced_tasks', 0)}")
            print(f"     几何分析: {enhancement_info.get('geometry_analysis_count', 0)}")
            print(f"     增强版本: {enhancement_info.get('enhancement_version', 'unknown')}")
        else:
            print(f"     ❌ 位置增强信息不存在")
        
        # 5. 性能统计
        print(f"\n📈 5. 性能统计:")
        
        if position_sync_metadata:
            total_tasks = position_sync_metadata.get('total_tasks_processed', 0)
            total_positions = position_sync_metadata.get('total_positions_collected', 0)
            processing_time = position_sync_metadata.get('processing_time_seconds', 0)
            
            if total_tasks > 0 and processing_time > 0:
                print(f"   平均每任务处理时间: {processing_time/total_tasks:.2f}秒")
                print(f"   平均每位置获取时间: {processing_time/max(1, total_positions):.2f}秒")
                print(f"   位置获取速率: {total_positions/processing_time:.1f} 位置/秒")
        
        # 6. 建议和总结
        print(f"\n💡 6. 建议和总结:")
        
        if tasks_with_position_sync == 0:
            print(f"   ❌ 严重问题: 没有任何任务获取到位置数据")
            print(f"   建议: 检查STK连接和卫星存在性")
        elif tasks_with_position_sync < total_visible_tasks * 0.5:
            print(f"   ⚠️ 位置获取成功率较低 ({tasks_with_position_sync/total_visible_tasks*100:.1f}%)")
            print(f"   建议: 检查STK场景时间范围和卫星传播器状态")
        else:
            print(f"   ✅ 位置获取成功率良好 ({tasks_with_position_sync/total_visible_tasks*100:.1f}%)")
        
        if position_sync_details and all(detail['sample_count'] == 2 for detail in position_sync_details):
            print(f"   ✅ 位置采集优化完全生效")
        else:
            print(f"   ⚠️ 位置采集优化可能未完全生效")
        
        if tasks_with_position_sync == len(timeline_tasks_with_position):
            print(f"   ✅ 位置数据同步到时间轴正确")
        else:
            print(f"   ❌ 位置数据同步到时间轴存在问题")
        
        return True
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始全面位置系统分析...")
    
    success = comprehensive_position_system_analysis()
    
    if success:
        print(f"\n🎉 全面位置系统分析完成！")
    else:
        print(f"\n⚠️ 全面位置系统分析失败。")
