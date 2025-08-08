#!/usr/bin/env python3
"""
调试采样过程
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_sampling_process():
    """调试采样过程"""
    try:
        print("=" * 60)
        print("🔍 调试采样过程")
        print("=" * 60)
        
        # 导入位置同步器
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
        print(f"   并行优化: {synchronizer.enable_parallel_optimization}")
        
        # 模拟一个5分钟的任务（类似调试结果中的任务）
        base_time = datetime(2025, 8, 6, 0, 42, 0)  # 从调试结果中的时间
        start_time = base_time
        end_time = base_time + timedelta(minutes=5)  # 5分钟任务
        
        print(f"\n🎯 测试任务:")
        print(f"   开始时间: {start_time}")
        print(f"   结束时间: {end_time}")
        print(f"   持续时间: {(end_time - start_time).total_seconds()}秒")
        
        # 测试采样时间计算
        print(f"\n📍 采样时间计算:")
        sample_times = synchronizer._calculate_sample_times(start_time, end_time)
        
        print(f"   采样点数: {len(sample_times)}")
        print(f"   采样时间:")
        for i, sample_time in enumerate(sample_times):
            print(f"     {i+1}. {sample_time}")
        
        # 验证优化是否生效
        expected_optimized_count = 2  # 开始和结束
        actual_count = len(sample_times)
        
        print(f"\n✅ 优化验证:")
        print(f"   预期采样点数 (优化后): {expected_optimized_count}")
        print(f"   实际采样点数: {actual_count}")
        print(f"   优化是否生效: {'✅ 是' if actual_count == expected_optimized_count else '❌ 否'}")
        
        if actual_count != expected_optimized_count:
            print(f"   ⚠️ 优化未生效！可能的原因:")
            print(f"     - _calculate_sample_times 方法被其他逻辑覆盖")
            print(f"     - 存在其他采样路径")
            print(f"     - 配置参数影响了采样逻辑")
        
        # 测试不同持续时间的任务
        print(f"\n📊 不同持续时间任务的采样测试:")
        test_durations = [60, 120, 300, 600, 900]  # 1分钟到15分钟
        
        for duration in test_durations:
            test_start = base_time
            test_end = base_time + timedelta(seconds=duration)
            test_samples = synchronizer._calculate_sample_times(test_start, test_end)
            
            print(f"   {duration}秒任务: {len(test_samples)}个采样点")
        
        # 检查是否有其他采样相关的配置
        print(f"\n🔧 相关配置检查:")
        print(f"   STK COM超时: {synchronizer.stk_com_timeout}秒")
        print(f"   启用统计计算: {synchronizer.enable_statistics}")
        print(f"   启用并发处理: {synchronizer.enable_concurrent}")
        print(f"   最大工作线程: {synchronizer.max_workers}")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始采样过程调试...")
    
    success = debug_sampling_process()
    
    if success:
        print(f"\n🎉 采样过程调试完成！")
    else:
        print(f"\n⚠️ 采样过程调试失败。")
