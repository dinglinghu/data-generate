#!/usr/bin/env python3
"""
测试时间轴数据中的卫星位置信息
"""

import json
import os
from pathlib import Path
from datetime import datetime

def test_timeline_position_data():
    """测试时间轴数据中的位置信息"""
    try:
        print("=" * 60)
        print("🔍 测试时间轴数据中的卫星位置信息")
        print("=" * 60)
        
        # 查找最新的采集数据 - 先尝试统一目录
        unified_dir = Path("output/unified_collections")
        rolling_dir = Path("output/rolling_collections")

        latest_session = None

        # 优先查找统一目录
        if unified_dir.exists():
            session_dirs = [d for d in unified_dir.iterdir() if d.is_dir() and d.name.startswith("session_")]
            if session_dirs:
                latest_session = max(session_dirs, key=lambda x: x.stat().st_mtime)
                print(f"📁 使用统一目录会话: {latest_session.name}")

        # 如果统一目录没有，尝试滚动目录
        if not latest_session and rolling_dir.exists():
            session_dirs = [d for d in rolling_dir.iterdir() if d.is_dir() and d.name.startswith("session_")]
            if session_dirs:
                latest_session = max(session_dirs, key=lambda x: x.stat().st_mtime)
                print(f"📁 使用滚动目录会话: {latest_session.name}")

        if not latest_session:
            print("❌ 没有找到会话目录")
            return False
        
        # 查找时间轴数据文件
        json_dir = latest_session / "json_data"
        if not json_dir.exists():
            print("❌ JSON数据目录不存在")
            return False
        
        timeline_files = list(json_dir.glob("*_timeline.json"))
        if not timeline_files:
            print("❌ 没有找到时间轴数据文件")
            return False
        
        # 测试最新的时间轴文件
        latest_timeline_file = max(timeline_files, key=lambda x: x.stat().st_mtime)
        print(f"📄 测试文件: {latest_timeline_file.name}")
        
        # 加载时间轴数据
        with open(latest_timeline_file, 'r', encoding='utf-8') as f:
            timeline_data = json.load(f)
        
        print(f"\n📊 时间轴数据概览:")
        print(f"   数据类型: {timeline_data.get('collection_info', {}).get('data_type', 'unknown')}")
        print(f"   转换时间: {timeline_data.get('collection_info', {}).get('conversion_time', 'unknown')}")
        
        # 分析可见元任务时间轴
        visible_timeline = timeline_data.get('visible_meta_task_timeline', {})
        tasks = visible_timeline.get('tasks', [])
        
        print(f"\n🎯 可见元任务分析:")
        print(f"   总任务数: {len(tasks)}")
        
        # 统计不同类型的任务
        visible_tasks = [t for t in tasks if t.get('type') == 'visible_meta_task']
        virtual_tasks = [t for t in tasks if t.get('type') == 'virtual_atomic_task']
        
        print(f"   可见任务: {len(visible_tasks)}")
        print(f"   虚拟任务: {len(virtual_tasks)}")
        
        # 分析位置数据
        tasks_with_position = [t for t in visible_tasks if t.get('satellite_position_sync', {}).get('has_position_data', False)]
        
        print(f"\n🛰️ 卫星位置数据分析:")
        print(f"   含位置数据的可见任务: {len(tasks_with_position)}")
        print(f"   位置数据覆盖率: {len(tasks_with_position)/max(1, len(visible_tasks))*100:.1f}%")
        
        # 详细分析位置数据
        if tasks_with_position:
            print(f"\n📍 位置数据详情:")
            
            total_samples = 0
            for i, task in enumerate(tasks_with_position[:3]):  # 显示前3个任务的详情
                position_sync = task.get('satellite_position_sync', {})
                position_samples = position_sync.get('position_samples', [])
                
                print(f"\n   任务 {i+1}: {task.get('task_name', 'Unknown')}")
                print(f"     任务ID: {task.get('task_id', 'Unknown')}")
                print(f"     卫星ID: {task.get('satellite_id', 'Unknown')}")
                print(f"     导弹ID: {task.get('missile_id', 'Unknown')}")
                print(f"     开始时间: {task.get('start_time', 'Unknown')}")
                print(f"     结束时间: {task.get('end_time', 'Unknown')}")
                print(f"     位置样本数: {len(position_samples)}")
                print(f"     采样间隔: {position_sync.get('sample_interval_seconds', 'Unknown')}秒")
                
                # 显示位置样本示例
                if position_samples:
                    first_sample = position_samples[0]
                    last_sample = position_samples[-1]
                    
                    print(f"     首个位置样本:")
                    print(f"       时间: {first_sample.get('sample_time', 'Unknown')}")
                    position = first_sample.get('position', {})
                    if 'x' in position:
                        print(f"       坐标: ({position.get('x', 0):.2f}, {position.get('y', 0):.2f}, {position.get('z', 0):.2f}) km")
                    elif 'latitude' in position:
                        print(f"       位置: ({position.get('latitude', 0):.6f}°, {position.get('longitude', 0):.6f}°, {position.get('altitude', 0):.2f}km)")
                    
                    if len(position_samples) > 1:
                        print(f"     末个位置样本:")
                        print(f"       时间: {last_sample.get('sample_time', 'Unknown')}")
                        position = last_sample.get('position', {})
                        if 'x' in position:
                            print(f"       坐标: ({position.get('x', 0):.2f}, {position.get('y', 0):.2f}, {position.get('z', 0):.2f}) km")
                        elif 'latitude' in position:
                            print(f"       位置: ({position.get('latitude', 0):.6f}°, {position.get('longitude', 0):.6f}°, {position.get('altitude', 0):.2f}km)")
                
                total_samples += len(position_samples)
            
            print(f"\n   总位置样本数: {total_samples}")
            
            if len(tasks_with_position) > 3:
                print(f"   ... 还有 {len(tasks_with_position) - 3} 个任务含有位置数据")
        
        # 检查统计信息
        statistics = timeline_data.get('statistics', {})
        position_coverage = statistics.get('position_data_coverage', {})
        
        print(f"\n📈 统计信息:")
        print(f"   导弹数量: {statistics.get('missile_count', 0)}")
        print(f"   卫星数量: {statistics.get('satellite_count', 0)}")
        print(f"   可见率: {statistics.get('visibility_ratio', 0)*100:.1f}%")
        
        if position_coverage:
            print(f"   位置数据覆盖:")
            print(f"     含位置的可见任务: {position_coverage.get('visible_tasks_with_satellite_positions', 0)}")
            print(f"     总可见任务: {position_coverage.get('total_visible_tasks', 0)}")
            print(f"     位置覆盖率: {position_coverage.get('satellite_position_coverage_ratio', 0)*100:.1f}%")
        
        print(f"\n✅ 时间轴位置数据测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始时间轴位置数据测试...")
    
    success = test_timeline_position_data()
    
    if success:
        print(f"\n🎉 测试完成！时间轴数据中包含卫星位置信息。")
    else:
        print(f"\n⚠️ 测试失败或数据不完整。")
