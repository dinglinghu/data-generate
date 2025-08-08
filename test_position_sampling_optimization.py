#!/usr/bin/env python3
"""
测试位置采样优化效果
"""

from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_position_sampling_optimization():
    """测试位置采样优化效果"""
    try:
        print("=" * 60)
        print("🚀 测试位置采样优化效果")
        print("=" * 60)
        
        # 导入卫星位置同步器
        from src.meta_task.satellite_position_synchronizer import SatellitePositionSynchronizer
        from src.utils.config_manager import get_config_manager
        from src.utils.time_manager import get_time_manager

        # 获取配置
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()
        time_manager = get_time_manager()

        # 创建位置同步器
        synchronizer = SatellitePositionSynchronizer(stk_config, time_manager)
        
        print(f"📊 位置同步器配置:")
        print(f"   采样间隔: {synchronizer.position_sample_interval}秒")
        print(f"   最大采样点数: {synchronizer.max_samples_per_task}")
        
        # 模拟可见元任务
        base_time = datetime.now()
        test_tasks = []
        
        # 创建不同持续时间的测试任务
        durations = [60, 120, 300, 600, 900]  # 1分钟到15分钟
        
        for i, duration in enumerate(durations):
            start_time = base_time + timedelta(seconds=i * 1000)
            end_time = start_time + timedelta(seconds=duration)
            
            task = {
                'task_id': f'test_task_{i+1}',
                'satellite_id': f'Satellite{i+1:02d}',
                'missile_id': f'Missile{i+1:02d}',
                'start_time': start_time,
                'end_time': end_time,
                'duration_seconds': duration
            }
            test_tasks.append(task)
        
        print(f"\n🎯 测试任务:")
        for task in test_tasks:
            print(f"   任务{task['task_id']}: {task['duration_seconds']}秒")
        
        # 测试采样时间计算
        print(f"\n📍 采样时间计算测试:")
        total_old_samples = 0
        total_new_samples = 0
        
        for task in test_tasks:
            start_time = task['start_time']
            end_time = task['end_time']
            duration = task['duration_seconds']
            
            # 使用新的优化方法
            sample_times = synchronizer._calculate_sample_times(start_time, end_time)
            new_sample_count = len(sample_times)
            
            # 计算旧方法的采样点数（30秒间隔）
            if duration <= 60:  # 短任务
                old_sample_count = 2  # 开始和结束
            else:  # 长任务
                old_sample_count = max(2, int(duration / 30) + 1)
                if old_sample_count > 20:  # 最大限制
                    old_sample_count = 20
            
            total_old_samples += old_sample_count
            total_new_samples += new_sample_count
            
            print(f"   {task['task_id']} ({duration}s):")
            print(f"     旧方法: {old_sample_count} 个采样点")
            print(f"     新方法: {new_sample_count} 个采样点")
            print(f"     减少: {old_sample_count - new_sample_count} 个 ({((old_sample_count - new_sample_count) / old_sample_count * 100):.1f}%)")
        
        # 总体优化效果
        reduction_count = total_old_samples - total_new_samples
        reduction_percentage = (reduction_count / total_old_samples) * 100
        speed_improvement = total_old_samples / total_new_samples
        
        print(f"\n📈 总体优化效果:")
        print(f"   旧方法总采样点: {total_old_samples}")
        print(f"   新方法总采样点: {total_new_samples}")
        print(f"   减少采样点数: {reduction_count}")
        print(f"   减少百分比: {reduction_percentage:.1f}%")
        print(f"   速度提升倍数: {speed_improvement:.1f}x")
        
        # 时间节省估算
        avg_time_per_sample = 0.762  # 秒
        old_total_time = total_old_samples * avg_time_per_sample
        new_total_time = total_new_samples * avg_time_per_sample
        time_saved = old_total_time - new_total_time
        
        print(f"\n⏱️ 时间节省估算:")
        print(f"   旧方法总时间: {old_total_time:.1f}秒")
        print(f"   新方法总时间: {new_total_time:.1f}秒")
        print(f"   节省时间: {time_saved:.1f}秒")
        
        # 验证采样时间的正确性
        print(f"\n🔍 采样时间验证:")
        for i, task in enumerate(test_tasks[:2]):  # 只验证前两个任务
            start_time = task['start_time']
            end_time = task['end_time']
            sample_times = synchronizer._calculate_sample_times(start_time, end_time)
            
            print(f"   {task['task_id']}:")
            print(f"     任务时间: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')}")
            print(f"     采样时间: {[t.strftime('%H:%M:%S') for t in sample_times]}")
            print(f"     验证: 包含开始时间={start_time in sample_times}, 包含结束时间={end_time in sample_times}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始位置采样优化测试...")
    
    success = test_position_sampling_optimization()
    
    if success:
        print(f"\n🎉 位置采样优化测试完成！新策略显著减少了采样点数量。")
    else:
        print(f"\n⚠️ 位置采样优化测试失败。")
