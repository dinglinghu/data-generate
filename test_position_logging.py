#!/usr/bin/env python3
"""
测试位置获取和日志功能
"""

import sys
import os
import logging

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置日志级别为INFO以查看详细日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def test_position_logging():
    """测试位置获取和日志功能"""
    try:
        print("=" * 80)
        print("🔍 测试位置获取和日志功能")
        print("=" * 80)
        
        from src.stk_interface.stk_manager import STKManager
        from src.utils.config_manager import get_config_manager
        
        # 获取配置并连接STK
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()
        stk_manager = STKManager(stk_config)
        
        if not stk_manager.connect():
            print("❌ STK连接失败")
            return False
        
        print("✅ STK连接成功")
        
        # 检查场景中的卫星
        print(f"\n📊 检查STK场景中的卫星:")
        scenario = stk_manager.scenario
        satellites = []
        
        for i in range(scenario.Children.Count):
            child = scenario.Children.Item(i)
            if getattr(child, 'ClassName', '') == 'Satellite':
                sat_name = getattr(child, 'InstanceName', '')
                satellites.append(sat_name)
        
        print(f"   总卫星数: {len(satellites)}")
        print(f"   卫星列表: {sorted(satellites)}")
        
        if not satellites:
            print("❌ 场景中没有卫星，需要先创建卫星星座")
            
            # 尝试创建卫星星座
            print(f"\n🚀 尝试创建卫星星座...")
            from src.constellation.constellation_manager import ConstellationManager

            constellation_manager = ConstellationManager(stk_manager, config_manager)
            
            if constellation_manager.create_walker_constellation():
                print("✅ 卫星星座创建成功")
                
                # 重新检查卫星
                satellites = []
                for i in range(scenario.Children.Count):
                    child = scenario.Children.Item(i)
                    if getattr(child, 'ClassName', '') == 'Satellite':
                        sat_name = getattr(child, 'InstanceName', '')
                        satellites.append(sat_name)
                
                print(f"   新的卫星数量: {len(satellites)}")
                print(f"   新的卫星列表: {sorted(satellites)}")
            else:
                print("❌ 卫星星座创建失败")
                return False
        
        # 测试位置获取
        if satellites:
            print(f"\n🧪 测试位置获取功能:")
            
            # 选择前3个卫星进行测试
            test_satellites = satellites[:3]
            test_time_offsets = [360, 660, 960]  # 6分钟、11分钟、16分钟
            
            for satellite_id in test_satellites:
                print(f"\n🛰️ 测试卫星: {satellite_id}")
                
                for time_offset in test_time_offsets:
                    print(f"\n   ⏰ 测试时间偏移: {time_offset}秒")
                    
                    # 调用位置获取方法（会产生详细日志）
                    position_data = stk_manager.get_satellite_position(
                        satellite_id, 
                        str(time_offset), 
                        timeout=10
                    )
                    
                    if position_data:
                        print(f"   ✅ 位置获取成功")
                        if 'x' in position_data:
                            print(f"      坐标: x={position_data['x']:.2f}, y={position_data['y']:.2f}, z={position_data['z']:.2f}")
                        elif 'latitude' in position_data:
                            print(f"      位置: lat={position_data['latitude']:.6f}°, lon={position_data['longitude']:.6f}°, alt={position_data['altitude']:.2f}km")
                    else:
                        print(f"   ❌ 位置获取失败")
                    
                    print(f"   " + "-" * 50)
        
        # 测试并行位置管理器
        print(f"\n🔧 测试并行位置管理器:")
        
        from src.meta_task.parallel_position_manager import ParallelPositionManager, PositionRequest
        from datetime import datetime, timedelta
        from src.utils.time_manager import get_time_manager
        
        time_manager = get_time_manager()
        
        # 创建位置请求
        requests = []
        if satellites:
            for i, satellite_id in enumerate(satellites[:2]):  # 只测试前2个卫星
                for j, offset in enumerate([360, 660]):  # 2个时间点
                    sample_time = time_manager.start_time + timedelta(seconds=offset)
                    request = PositionRequest(
                        satellite_id=satellite_id,
                        time_offset=offset,
                        sample_time=sample_time,
                        task_id=f"test_task_{i}_{j}",
                        priority=1
                    )
                    requests.append(request)
        
        if requests:
            print(f"   创建了 {len(requests)} 个位置请求")
            
            # 创建并行位置管理器
            position_manager = ParallelPositionManager(stk_manager)
            
            # 获取位置
            results = position_manager.get_positions_parallel(requests)
            
            print(f"   处理结果:")
            success_count = 0
            for i, result in enumerate(results):
                if result.success:
                    success_count += 1
                    print(f"     {i+1}. ✅ {result.request.satellite_id} @ {result.request.time_offset}s - 成功")
                else:
                    print(f"     {i+1}. ❌ {result.request.satellite_id} @ {result.request.time_offset}s - 失败")
            
            print(f"   成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.1f}%)")
            
            # 显示统计信息
            stats = position_manager.get_stats()
            print(f"   统计信息:")
            print(f"     总请求数: {stats.get('total_requests', 0)}")
            print(f"     成功请求数: {stats.get('successful_requests', 0)}")
            print(f"     失败请求数: {stats.get('failed_requests', 0)}")
            print(f"     缓存命中数: {stats.get('cache_hits', 0)}")
            print(f"     缓存命中率: {stats.get('cache_hit_rate', 0):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始位置获取和日志功能测试...")
    
    success = test_position_logging()
    
    if success:
        print(f"\n🎉 位置获取和日志功能测试完成！")
    else:
        print(f"\n⚠️ 位置获取和日志功能测试失败。")
