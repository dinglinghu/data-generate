#!/usr/bin/env python3
"""
测试失败卫星的STK状态
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_failed_satellites():
    """测试失败卫星的STK状态"""
    try:
        print("=" * 80)
        print("🔍 测试失败卫星的STK状态")
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
        
        # 失败的卫星列表
        failed_satellites = ['Satellite01', 'Satellite05', 'Satellite17', 'Satellite11', 
                           'Satellite14', 'Satellite09', 'Satellite10', 'Satellite06', 
                           'Satellite12', 'Satellite08', 'Satellite13']
        
        # 成功的卫星列表
        successful_satellites = ['Satellite19', 'Satellite20', 'Satellite21', 'Satellite23']
        
        print(f"\n🧪 测试失败卫星 ({len(failed_satellites)}个):")
        
        failed_test_results = {}
        
        for satellite_id in failed_satellites:
            print(f"\n   🛰️ 测试 {satellite_id}:")
            
            # 1. 检查卫星是否存在
            try:
                satellite = stk_manager._find_satellite(satellite_id)
                if satellite:
                    print(f"     ✅ 卫星对象存在")
                    
                    # 2. 检查传播器
                    try:
                        propagator = satellite.Propagator
                        print(f"     ✅ 传播器: {propagator.PropagatorName}")
                        
                        # 3. 尝试传播
                        try:
                            propagator.Propagate()
                            print(f"     ✅ 传播成功")
                        except Exception as prop_e:
                            print(f"     ❌ 传播失败: {prop_e}")
                            
                    except Exception as prop_e:
                        print(f"     ❌ 传播器访问失败: {prop_e}")
                    
                    # 4. 测试位置获取
                    try:
                        # 测试几个不同的时间偏移
                        test_offsets = [360, 660, 960, 1260]  # 对应成功任务的时间
                        
                        for offset in test_offsets:
                            position_data = stk_manager.get_satellite_position(satellite_id, str(offset), timeout=10)
                            if position_data:
                                print(f"     ✅ 位置获取成功 (偏移{offset}s)")
                                print(f"        坐标: x={position_data.get('x', 0):.2f}, y={position_data.get('y', 0):.2f}, z={position_data.get('z', 0):.2f}")
                                break
                            else:
                                print(f"     ❌ 位置获取失败 (偏移{offset}s)")
                        else:
                            print(f"     ❌ 所有时间偏移的位置获取都失败")
                            
                    except Exception as pos_e:
                        print(f"     ❌ 位置获取异常: {pos_e}")
                
                else:
                    print(f"     ❌ 卫星对象不存在")
                    
            except Exception as e:
                print(f"     ❌ 卫星检查失败: {e}")
        
        print(f"\n✅ 测试成功卫星 ({len(successful_satellites)}个):")
        
        for satellite_id in successful_satellites:
            print(f"\n   🛰️ 测试 {satellite_id}:")
            
            try:
                satellite = stk_manager._find_satellite(satellite_id)
                if satellite:
                    print(f"     ✅ 卫星对象存在")
                    
                    # 测试位置获取
                    position_data = stk_manager.get_satellite_position(satellite_id, "1260", timeout=10)
                    if position_data:
                        print(f"     ✅ 位置获取成功")
                        print(f"        坐标: x={position_data.get('x', 0):.2f}, y={position_data.get('y', 0):.2f}, z={position_data.get('z', 0):.2f}")
                    else:
                        print(f"     ❌ 位置获取失败")
                else:
                    print(f"     ❌ 卫星对象不存在")
                    
            except Exception as e:
                print(f"     ❌ 卫星检查失败: {e}")
        
        # 检查所有卫星
        print(f"\n📊 STK场景中的所有卫星:")
        scenario = stk_manager.scenario
        all_satellites = []
        
        for i in range(scenario.Children.Count):
            child = scenario.Children.Item(i)
            if getattr(child, 'ClassName', '') == 'Satellite':
                sat_name = getattr(child, 'InstanceName', '')
                all_satellites.append(sat_name)
        
        print(f"   总卫星数: {len(all_satellites)}")
        print(f"   卫星列表: {sorted(all_satellites)}")
        
        # 检查缺失的卫星
        expected_satellites = set(failed_satellites + successful_satellites)
        existing_satellites = set(all_satellites)
        
        missing_satellites = expected_satellites - existing_satellites
        extra_satellites = existing_satellites - expected_satellites
        
        if missing_satellites:
            print(f"   ❌ 缺失的卫星: {sorted(missing_satellites)}")
        
        if extra_satellites:
            print(f"   ➕ 额外的卫星: {sorted(extra_satellites)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始失败卫星测试...")
    
    success = test_failed_satellites()
    
    if success:
        print(f"\n🎉 失败卫星测试完成！")
    else:
        print(f"\n⚠️ 失败卫星测试失败。")
