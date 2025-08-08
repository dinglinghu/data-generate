#!/usr/bin/env python3
"""
详细测试卫星位置获取，检查高度为0的问题
"""

def test_satellite_position_methods():
    """测试不同的位置获取方法"""
    try:
        print("=" * 60)
        print("🔍 详细测试卫星位置获取")
        print("=" * 60)
        
        # 导入必要的模块
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
        
        # 测试卫星ID
        test_satellite_id = "Satellite01"
        
        print(f"\n🛰️ 测试卫星: {test_satellite_id}")
        
        # 查找卫星
        satellite = stk_manager._find_satellite(test_satellite_id)
        if not satellite:
            print(f"❌ 未找到卫星: {test_satellite_id}")
            return False
        
        print(f"✅ 找到卫星: {test_satellite_id}")
        
        # 获取场景时间
        scenario_time = stk_manager.scenario.StartTime
        print(f"📅 场景时间: {scenario_time}")
        
        # 测试方法1: Cartesian Position
        print(f"\n1️⃣ 测试 Cartesian Position:")
        try:
            dp = satellite.DataProviders.Item("Cartesian Position")
            result = dp.Exec(scenario_time, scenario_time)
            
            if result and result.DataSets.Count > 0:
                dataset = result.DataSets.Item(0)
                if dataset.RowCount > 0:
                    x = float(dataset.GetValue(0, 1))
                    y = float(dataset.GetValue(0, 2))
                    z = float(dataset.GetValue(0, 3))
                    
                    # 计算距离地心的距离
                    distance = (x**2 + y**2 + z**2)**0.5
                    altitude = distance - 6371.0  # 地球半径
                    
                    print(f"   坐标: ({x:.2f}, {y:.2f}, {z:.2f}) km")
                    print(f"   距地心: {distance:.2f} km")
                    print(f"   高度: {altitude:.2f} km")
                else:
                    print("   ❌ 无数据行")
            else:
                print("   ❌ 无数据集")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        
        # 测试方法2: LLA Position
        print(f"\n2️⃣ 测试 LLA Position:")
        try:
            dp = satellite.DataProviders.Item("LLA Position")
            result = dp.Exec(scenario_time, scenario_time)
            
            if result and result.DataSets.Count > 0:
                dataset = result.DataSets.Item(0)
                if dataset.RowCount > 0:
                    lat = float(dataset.GetValue(0, 1))
                    lon = float(dataset.GetValue(0, 2))
                    alt = float(dataset.GetValue(0, 3))
                    
                    print(f"   纬度: {lat:.6f}°")
                    print(f"   经度: {lon:.6f}°")
                    print(f"   高度: {alt:.2f} km")
                else:
                    print("   ❌ 无数据行")
            else:
                print("   ❌ 无数据集")
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        
        # 测试方法3: 检查轨道参数
        print(f"\n3️⃣ 检查轨道参数:")
        try:
            # 获取当前轨道状态
            propagator = satellite.Propagator
            initial_state = propagator.InitialState
            representation = initial_state.Representation
            
            print(f"   传播器类型: {propagator.PropagatorName}")
            print(f"   表示类型: {representation.Name}")
            
            # 尝试获取Keplerian元素
            try:
                keplerian = representation.ConvertTo(1)  # Keplerian
                semi_major_axis = keplerian.SizeShape.SemiMajorAxis
                eccentricity = keplerian.SizeShape.Eccentricity
                inclination = keplerian.Orientation.Inclination
                
                altitude = semi_major_axis - 6371.0
                
                print(f"   半长轴: {semi_major_axis:.2f} km")
                print(f"   偏心率: {eccentricity:.6f}")
                print(f"   倾角: {inclination:.2f}°")
                print(f"   轨道高度: {altitude:.2f} km")
            except Exception as ke:
                print(f"   ❌ 无法获取Keplerian元素: {ke}")
                
        except Exception as e:
            print(f"   ❌ 失败: {e}")
        
        # 测试方法4: 传播到不同时间
        print(f"\n4️⃣ 测试不同时间点的位置:")
        try:
            from datetime import datetime, timedelta
            from src.utils.time_manager import get_time_manager
            
            time_manager = get_time_manager()
            
            # 测试几个不同的时间点
            test_offsets = [0, 1800, 3600]  # 0分钟, 30分钟, 1小时
            
            for offset in test_offsets:
                target_time = time_manager.start_time + timedelta(seconds=offset)
                stk_time = target_time.strftime("%d %b %Y %H:%M:%S.000")
                
                print(f"\n   时间偏移 {offset}秒 ({offset/60:.0f}分钟):")
                print(f"   STK时间: {stk_time}")
                
                # 使用LLA Position测试
                try:
                    dp = satellite.DataProviders.Item("LLA Position")
                    result = dp.Exec(stk_time, stk_time)
                    
                    if result and result.DataSets.Count > 0:
                        dataset = result.DataSets.Item(0)
                        if dataset.RowCount > 0:
                            lat = float(dataset.GetValue(0, 1))
                            lon = float(dataset.GetValue(0, 2))
                            alt = float(dataset.GetValue(0, 3))
                            
                            print(f"     位置: ({lat:.3f}°, {lon:.3f}°, {alt:.1f}km)")
                        else:
                            print("     ❌ 无数据")
                    else:
                        print("     ❌ 无结果")
                except Exception as te:
                    print(f"     ❌ 时间测试失败: {te}")
        
        except Exception as e:
            print(f"   ❌ 时间测试失败: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始详细位置测试...")
    
    success = test_satellite_position_methods()
    
    if success:
        print(f"\n🎉 详细测试完成！")
    else:
        print(f"\n⚠️ 测试失败。")
