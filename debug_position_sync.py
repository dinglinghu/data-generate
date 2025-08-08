#!/usr/bin/env python3
"""
调试位置同步问题
"""

import json
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_position_sync():
    """调试位置同步问题"""
    try:
        print("=" * 60)
        print("🔍 调试位置同步问题")
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
        if not json_dir.exists():
            print("❌ JSON数据目录不存在")
            return False
        
        original_files = list(json_dir.glob("*_original.json"))
        if not original_files:
            print("❌ 没有找到原始数据文件")
            return False
        
        # 加载最新的原始数据
        latest_original_file = max(original_files, key=lambda x: x.stat().st_mtime)
        print(f"📄 分析文件: {latest_original_file.name}")
        
        with open(latest_original_file, 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        print(f"\n📊 原始数据概览:")
        print(f"   数据类型: {original_data.get('collection_info', {}).get('data_type', 'unknown')}")
        print(f"   采集时间: {original_data.get('collection_info', {}).get('collection_time', 'unknown')}")
        
        # 分析可见元任务数据
        visible_meta_tasks = original_data.get('visible_meta_tasks', {})
        constellation_sets = visible_meta_tasks.get('constellation_visible_task_sets', {})
        
        print(f"\n🛰️ 可见元任务分析:")
        print(f"   卫星数量: {len(constellation_sets)}")
        
        total_visible_tasks = 0
        tasks_with_position_sync = 0
        tasks_with_position_samples = 0
        
        # 详细分析每个卫星的任务
        for satellite_id, satellite_data in constellation_sets.items():
            missile_tasks = satellite_data.get('missile_tasks', {})
            satellite_visible_count = 0
            satellite_position_sync_count = 0
            satellite_position_samples_count = 0
            
            for missile_id, missile_data in missile_tasks.items():
                visible_tasks = missile_data.get('visible_tasks', [])
                satellite_visible_count += len(visible_tasks)
                
                for task in visible_tasks:
                    total_visible_tasks += 1
                    
                    # 检查位置同步信息
                    position_sync = task.get('satellite_position_sync')
                    if position_sync:
                        tasks_with_position_sync += 1
                        satellite_position_sync_count += 1
                        
                        # 检查位置样本
                        position_samples = position_sync.get('position_samples', [])
                        if position_samples:
                            tasks_with_position_samples += 1
                            satellite_position_samples_count += 1
                            
                            # 显示第一个任务的详细信息
                            if tasks_with_position_samples == 1:
                                print(f"\n📍 第一个有位置数据的任务详情:")
                                print(f"   任务ID: {task.get('task_id')}")
                                print(f"   卫星ID: {satellite_id}")
                                print(f"   导弹ID: {missile_id}")
                                print(f"   开始时间: {task.get('start_time')}")
                                print(f"   结束时间: {task.get('end_time')}")
                                print(f"   位置样本数: {len(position_samples)}")
                                
                                # 显示位置样本
                                for i, sample in enumerate(position_samples[:2]):  # 只显示前2个
                                    print(f"   样本 {i+1}:")
                                    print(f"     时间: {sample.get('sample_time')}")
                                    position = sample.get('position', {})
                                    if 'x' in position:
                                        print(f"     坐标: ({position.get('x', 0):.2f}, {position.get('y', 0):.2f}, {position.get('z', 0):.2f}) km")
                                    elif 'latitude' in position:
                                        print(f"     位置: ({position.get('latitude', 0):.6f}°, {position.get('longitude', 0):.6f}°, {position.get('altitude', 0):.2f}km)")
                        else:
                            # 显示没有位置样本的任务
                            if satellite_position_sync_count == 1 and satellite_position_samples_count == 0:
                                print(f"\n⚠️ 有位置同步但无位置样本的任务:")
                                print(f"   任务ID: {task.get('task_id')}")
                                print(f"   卫星ID: {satellite_id}")
                                print(f"   导弹ID: {missile_id}")
                                print(f"   位置同步数据: {position_sync}")
                    else:
                        # 显示没有位置同步的任务
                        if total_visible_tasks == 1:
                            print(f"\n❌ 第一个没有位置同步的任务:")
                            print(f"   任务ID: {task.get('task_id')}")
                            print(f"   卫星ID: {satellite_id}")
                            print(f"   导弹ID: {missile_id}")
                            print(f"   任务数据键: {list(task.keys())}")
            
            if satellite_visible_count > 0:
                print(f"   {satellite_id}: {satellite_visible_count}个可见任务, {satellite_position_sync_count}个有位置同步, {satellite_position_samples_count}个有位置样本")
        
        print(f"\n📈 位置同步统计:")
        print(f"   总可见任务: {total_visible_tasks}")
        print(f"   有位置同步: {tasks_with_position_sync}")
        print(f"   有位置样本: {tasks_with_position_samples}")
        print(f"   位置同步率: {tasks_with_position_sync/max(1, total_visible_tasks)*100:.1f}%")
        print(f"   位置样本率: {tasks_with_position_samples/max(1, total_visible_tasks)*100:.1f}%")
        
        # 检查位置同步元数据
        position_sync_metadata = visible_meta_tasks.get('position_sync_metadata', {})
        if position_sync_metadata:
            print(f"\n🔧 位置同步元数据:")
            print(f"   同步时间: {position_sync_metadata.get('sync_time')}")
            print(f"   处理任务数: {position_sync_metadata.get('total_tasks_processed', 0)}")
            print(f"   采集位置数: {position_sync_metadata.get('total_positions_collected', 0)}")
            print(f"   处理时间: {position_sync_metadata.get('processing_time_seconds', 0):.2f}秒")
            print(f"   同步状态: {position_sync_metadata.get('sync_status')}")
        else:
            print(f"\n❌ 没有找到位置同步元数据")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始位置同步调试...")
    
    success = debug_position_sync()
    
    if success:
        print(f"\n🎉 位置同步调试完成！")
    else:
        print(f"\n⚠️ 位置同步调试失败。")
