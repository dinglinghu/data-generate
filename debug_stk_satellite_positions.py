#!/usr/bin/env python3
"""
调试STK中各个卫星的位置获取情况
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_stk_satellite_positions():
    """调试STK中各个卫星的位置获取情况"""
    try:
        print("=" * 80)
        print("🔍 调试STK中各个卫星的位置获取情况")
        print("=" * 80)
        
        from src.stk_interface.stk_manager import STKManager
        from src.utils.config_manager import get_config_manager
        from src.utils.time_manager import get_time_manager
        
        # 获取配置并连接STK
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()
        stk_manager = STKManager(stk_config)
        time_manager = get_time_manager()
        
        if not stk_manager.connect():
            print("❌ STK连接失败")
            return False
        
        print("✅ STK连接成功")
        
        # 获取场景中的所有卫星
        scenario = stk_manager.scenario
        satellites_in_stk = []
        
        print(f"\n🛰️ 扫描STK场景中的卫星:")
        for i in range(scenario.Children.Count):
            child = scenario.Children.Item(i)
            class_name = getattr(child, 'ClassName', 'Unknown')
            instance_name = getattr(child, 'InstanceName', 'Unknown')
            
            if class_name == 'Satellite':
                satellites_in_stk.append(instance_name)
                print(f"   发现卫星: {instance_name}")
        
        print(f"\n📊 STK中共有 {len(satellites_in_stk)} 颗卫星")
        
        # 从失败分析中获取的卫星列表
        failed_satellites = ['Satellite01', 'Satellite02', 'Satellite03', 'Satellite06', 'Satellite07', 
                           'Satellite10', 'Satellite11', 'Satellite12', 'Satellite13', 'Satellite14', 
                           'Satellite17', 'Satellite18']
        
        successful_satellites = ['Satellite19', 'Satellite23', 'Satellite24']
        
        # 测试时间点（使用场景开始时间后的一些偏移）
        test_time_offsets = [0, 300, 600, 1200]  # 0秒、5分钟、10分钟、20分钟
        
        print(f"\n🧪 测试卫星位置获取:")
        print(f"   测试时间偏移: {test_time_offsets} 秒")
        
        position_test_results = {}
        
        # 测试所有卫星
        test_satellites = failed_satellites + successful_satellites
        
        for satellite_id in test_satellites:
            if satellite_id not in satellites_in_stk:
                print(f"   ❌ {satellite_id}: 不存在于STK场景中")
                continue
            
            print(f"\n   🛰️ 测试 {satellite_id}:")
            satellite_results = {}
            
            for time_offset in test_time_offsets:
                try:
                    # 测试位置获取
                    position_data = stk_manager.get_satellite_position(satellite_id, str(time_offset), timeout=10)
                    
                    if position_data:
                        print(f"     ✅ 时间偏移 {time_offset}s: 成功")
                        print(f"        位置: x={position_data.get('x', 0):.2f}, y={position_data.get('y', 0):.2f}, z={position_data.get('z', 0):.2f}")
                        satellite_results[time_offset] = {'success': True, 'data': position_data}
                    else:
                        print(f"     ❌ 时间偏移 {time_offset}s: 失败 (返回None)")
                        satellite_results[time_offset] = {'success': False, 'error': 'None returned'}
                        
                except Exception as e:
                    print(f"     ❌ 时间偏移 {time_offset}s: 异常 - {e}")
                    satellite_results[time_offset] = {'success': False, 'error': str(e)}
            
            position_test_results[satellite_id] = satellite_results
        
        # 分析结果
        print(f"\n📊 位置获取结果分析:")
        
        completely_successful = []
        completely_failed = []
        partially_successful = []
        
        for satellite_id, results in position_test_results.items():
            success_count = sum(1 for r in results.values() if r['success'])
            total_tests = len(results)
            success_rate = success_count / total_tests * 100 if total_tests > 0 else 0
            
            print(f"   {satellite_id}: {success_count}/{total_tests} 成功 ({success_rate:.1f}%)")
            
            if success_rate == 100:
                completely_successful.append(satellite_id)
            elif success_rate == 0:
                completely_failed.append(satellite_id)
            else:
                partially_successful.append(satellite_id)
        
        print(f"\n📈 卫星分类:")
        print(f"   完全成功: {completely_successful}")
        print(f"   部分成功: {partially_successful}")
        print(f"   完全失败: {completely_failed}")
        
        # 分析失败原因
        print(f"\n🔍 失败原因分析:")
        
        error_patterns = {}
        for satellite_id, results in position_test_results.items():
            for time_offset, result in results.items():
                if not result['success']:
                    error = result.get('error', 'Unknown')
                    if error not in error_patterns:
                        error_patterns[error] = []
                    error_patterns[error].append(f"{satellite_id}@{time_offset}s")
        
        for error, occurrences in error_patterns.items():
            print(f"   错误: {error}")
            print(f"     发生次数: {len(occurrences)}")
            print(f"     示例: {', '.join(occurrences[:5])}")  # 只显示前5个
        
        # 检查卫星传播状态
        print(f"\n🔧 检查卫星传播状态:")
        
        for satellite_id in test_satellites[:10]:  # 只检查前10个
            if satellite_id not in satellites_in_stk:
                continue
                
            try:
                satellite = stk_manager._find_satellite(satellite_id)
                if satellite:
                    # 检查传播器状态
                    try:
                        propagator = satellite.Propagator
                        print(f"   {satellite_id}: 传播器类型 = {propagator.PropagatorName}")
                        
                        # 尝试传播
                        propagator.Propagate()
                        print(f"   {satellite_id}: ✅ 传播成功")
                        
                    except Exception as prop_e:
                        print(f"   {satellite_id}: ❌ 传播失败 - {prop_e}")
                        
                else:
                    print(f"   {satellite_id}: ❌ 无法找到卫星对象")
                    
            except Exception as e:
                print(f"   {satellite_id}: ❌ 检查失败 - {e}")
        
        # 检查时间范围
        print(f"\n⏰ 检查时间范围:")
        print(f"   场景开始时间: {time_manager.start_time}")
        print(f"   场景结束时间: {time_manager.end_time}")
        print(f"   场景持续时间: {(time_manager.end_time - time_manager.start_time).total_seconds()}秒")
        
        for time_offset in test_time_offsets:
            test_time = time_manager.start_time + timedelta(seconds=time_offset)
            in_range = time_manager.start_time <= test_time <= time_manager.end_time
            print(f"   偏移 {time_offset}s ({test_time}): {'✅ 在范围内' if in_range else '❌ 超出范围'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始STK卫星位置调试...")
    
    success = debug_stk_satellite_positions()
    
    if success:
        print(f"\n🎉 STK卫星位置调试完成！")
    else:
        print(f"\n⚠️ STK卫星位置调试失败。")
