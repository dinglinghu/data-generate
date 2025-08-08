#!/usr/bin/env python3
"""
全面分析位置数据获取问题
"""

import json
import sys
import os
from pathlib import Path
from collections import defaultdict

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def comprehensive_position_analysis():
    """全面分析位置数据获取问题"""
    try:
        print("=" * 80)
        print("🔍 全面分析位置数据获取问题")
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
        
        print(f"📄 分析文件:")
        print(f"   原始数据: {latest_original_file.name}")
        print(f"   时间轴数据: {latest_timeline_file.name}")
        
        # 加载数据
        with open(latest_original_file, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        with open(latest_timeline_file, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)
        
        # 1. 分析原始数据中的位置同步情况
        print(f"\n📊 1. 原始数据位置同步分析:")
        visible_meta_tasks = original_data.get('visible_meta_tasks', {})
        constellation_sets = visible_meta_tasks.get('constellation_visible_task_sets', {})
        
        satellite_analysis = {}
        total_visible_tasks = 0
        total_tasks_with_position = 0
        
        for satellite_id, satellite_data in constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            satellite_visible_count = 0
            satellite_position_count = 0
            satellite_task_details = []
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])
                
                for task in visible_tasks:
                    total_visible_tasks += 1
                    satellite_visible_count += 1
                    
                    has_position_sync = 'satellite_position_sync' in task
                    position_samples = []
                    if has_position_sync:
                        position_sync = task['satellite_position_sync']
                        position_samples = position_sync.get('position_samples', [])
                    
                    has_valid_position = len(position_samples) > 0
                    if has_valid_position:
                        total_tasks_with_position += 1
                        satellite_position_count += 1
                    
                    satellite_task_details.append({
                        'task_id': task.get('task_id'),
                        'missile_id': missile_id,
                        'start_time': task.get('start_time'),
                        'end_time': task.get('end_time'),
                        'has_position_sync': has_position_sync,
                        'has_valid_position': has_valid_position,
                        'sample_count': len(position_samples)
                    })
            
            satellite_analysis[satellite_id] = {
                'total_visible_tasks': satellite_visible_count,
                'tasks_with_position': satellite_position_count,
                'success_rate': (satellite_position_count / satellite_visible_count * 100) if satellite_visible_count > 0 else 0,
                'task_details': satellite_task_details
            }
        
        print(f"   总可见任务: {total_visible_tasks}")
        print(f"   有位置数据: {total_tasks_with_position}")
        print(f"   整体成功率: {total_tasks_with_position/max(1, total_visible_tasks)*100:.1f}%")
        
        # 2. 按卫星分析成功率
        print(f"\n📊 2. 各卫星位置获取成功率:")
        print(f"{'卫星ID':<15} {'可见任务':<8} {'成功':<6} {'失败':<6} {'成功率':<8}")
        print("-" * 60)
        
        successful_satellites = []
        failed_satellites = []
        partial_satellites = []
        
        for satellite_id in sorted(satellite_analysis.keys()):
            analysis = satellite_analysis[satellite_id]
            total = analysis['total_visible_tasks']
            success = analysis['tasks_with_position']
            failed = total - success
            rate = analysis['success_rate']
            
            print(f"{satellite_id:<15} {total:<8} {success:<6} {failed:<6} {rate:<7.1f}%")
            
            if rate == 100:
                successful_satellites.append(satellite_id)
            elif rate == 0:
                failed_satellites.append(satellite_id)
            else:
                partial_satellites.append(satellite_id)
        
        print(f"\n📈 卫星分类:")
        print(f"   完全成功 ({len(successful_satellites)}个): {', '.join(successful_satellites)}")
        print(f"   部分成功 ({len(partial_satellites)}个): {', '.join(partial_satellites)}")
        print(f"   完全失败 ({len(failed_satellites)}个): {', '.join(failed_satellites)}")
        
        # 3. 分析卫星ID模式
        print(f"\n📊 3. 卫星ID模式分析:")
        
        def extract_satellite_number(sat_id):
            if sat_id.startswith('Satellite'):
                try:
                    return int(sat_id.replace('Satellite', ''))
                except ValueError:
                    return None
            return None
        
        successful_ids = [extract_satellite_number(s) for s in successful_satellites if extract_satellite_number(s) is not None]
        failed_ids = [extract_satellite_number(s) for s in failed_satellites if extract_satellite_number(s) is not None]
        partial_ids = [extract_satellite_number(s) for s in partial_satellites if extract_satellite_number(s) is not None]
        
        if successful_ids:
            print(f"   成功卫星ID: {sorted(successful_ids)}")
            print(f"   成功ID范围: {min(successful_ids)} - {max(successful_ids)}")
        
        if failed_ids:
            print(f"   失败卫星ID: {sorted(failed_ids)}")
            print(f"   失败ID范围: {min(failed_ids)} - {max(failed_ids)}")
        
        if partial_ids:
            print(f"   部分成功ID: {sorted(partial_ids)}")
        
        # 4. 分析时间模式
        print(f"\n📊 4. 时间模式分析:")
        
        time_analysis = defaultdict(lambda: {'total': 0, 'success': 0})
        
        for satellite_id, analysis in satellite_analysis.items():
            for task_detail in analysis['task_details']:
                start_time = task_detail['start_time']
                if start_time:
                    # 提取小时
                    if 'T' in start_time:
                        hour = start_time.split('T')[1].split(':')[0]
                    else:
                        hour = start_time.split(' ')[1].split(':')[0] if ' ' in start_time else '00'
                    
                    time_analysis[hour]['total'] += 1
                    if task_detail['has_valid_position']:
                        time_analysis[hour]['success'] += 1
        
        print(f"   按小时统计:")
        for hour in sorted(time_analysis.keys()):
            stats = time_analysis[hour]
            total = stats['total']
            success = stats['success']
            rate = (success / total * 100) if total > 0 else 0
            print(f"     {hour}:00 - {total}个任务, {success}个成功 ({rate:.1f}%)")
        
        # 5. 详细分析失败任务
        print(f"\n📊 5. 失败任务详细分析:")
        
        failed_task_count = 0
        failed_task_samples = []
        
        for satellite_id, analysis in satellite_analysis.items():
            for task_detail in analysis['task_details']:
                if not task_detail['has_valid_position']:
                    failed_task_count += 1
                    if len(failed_task_samples) < 10:  # 只收集前10个样本
                        failed_task_samples.append({
                            'satellite_id': satellite_id,
                            **task_detail
                        })
        
        print(f"   失败任务总数: {failed_task_count}")
        print(f"   失败任务样本:")
        
        for i, task in enumerate(failed_task_samples):
            print(f"     {i+1}. {task['satellite_id']} → {task['missile_id']}")
            print(f"        任务ID: {task['task_id']}")
            print(f"        时间: {task['start_time']} - {task['end_time']}")
            print(f"        有位置同步字段: {task['has_position_sync']}")
        
        # 6. 分析成功任务的特征
        print(f"\n📊 6. 成功任务特征分析:")
        
        successful_task_samples = []
        
        for satellite_id, analysis in satellite_analysis.items():
            for task_detail in analysis['task_details']:
                if task_detail['has_valid_position']:
                    if len(successful_task_samples) < 5:  # 只收集前5个样本
                        successful_task_samples.append({
                            'satellite_id': satellite_id,
                            **task_detail
                        })
        
        print(f"   成功任务样本:")
        for i, task in enumerate(successful_task_samples):
            print(f"     {i+1}. {task['satellite_id']} → {task['missile_id']}")
            print(f"        任务ID: {task['task_id']}")
            print(f"        时间: {task['start_time']} - {task['end_time']}")
            print(f"        位置样本数: {task['sample_count']}")
        
        # 7. 检查位置同步元数据
        print(f"\n📊 7. 位置同步元数据分析:")
        position_sync_metadata = visible_meta_tasks.get('position_sync_metadata', {})
        
        if position_sync_metadata:
            print(f"   同步时间: {position_sync_metadata.get('sync_time')}")
            print(f"   处理任务数: {position_sync_metadata.get('total_tasks_processed', 0)}")
            print(f"   采集位置数: {position_sync_metadata.get('total_positions_collected', 0)}")
            print(f"   采样间隔: {position_sync_metadata.get('sample_interval_seconds', 0)}秒")
            print(f"   处理时间: {position_sync_metadata.get('processing_time_seconds', 0):.2f}秒")
            print(f"   并发启用: {position_sync_metadata.get('concurrent_enabled', False)}")
            print(f"   最大工作线程: {position_sync_metadata.get('max_workers', 0)}")
            print(f"   同步状态: {position_sync_metadata.get('sync_status', 'unknown')}")
            
            # 验证数据一致性
            metadata_tasks = position_sync_metadata.get('total_tasks_processed', 0)
            metadata_positions = position_sync_metadata.get('total_positions_collected', 0)
            expected_positions = metadata_tasks * 2  # 每个任务2个位置
            
            print(f"\n   数据一致性检查:")
            print(f"     元数据显示处理任务: {metadata_tasks}")
            print(f"     实际统计成功任务: {total_tasks_with_position}")
            print(f"     元数据显示位置数: {metadata_positions}")
            print(f"     预期位置数 (任务×2): {expected_positions}")
            print(f"     数据一致性: {'✅ 一致' if metadata_tasks == total_tasks_with_position and metadata_positions == expected_positions else '❌ 不一致'}")
        else:
            print(f"   ❌ 没有找到位置同步元数据")
        
        return True
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始全面位置分析...")
    
    success = comprehensive_position_analysis()
    
    if success:
        print(f"\n🎉 全面位置分析完成！")
    else:
        print(f"\n⚠️ 全面位置分析失败。")
