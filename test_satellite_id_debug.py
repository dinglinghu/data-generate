#!/usr/bin/env python3
"""
测试卫星ID问题的调试脚本
"""

def test_satellite_creation_and_lookup():
    """测试卫星创建和查找"""
    try:
        print("=" * 60)
        print("🔍 测试卫星创建和查找")
        print("=" * 60)
        
        # 导入必要的模块
        from src.constellation.constellation_manager import ConstellationManager
        from src.stk_interface.stk_manager import STKManager
        from src.utils.config_manager import get_config_manager
        
        # 获取配置
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()
        
        print("1️⃣ 初始化STK管理器...")
        stk_manager = STKManager(stk_config)
        
        # 连接STK
        if not stk_manager.connect():
            print("❌ STK连接失败")
            return False
        
        print("✅ STK连接成功")
        
        print("\n2️⃣ 初始化星座管理器...")
        constellation_manager = ConstellationManager(stk_manager, config_manager)
        
        print("\n3️⃣ 创建Walker星座...")
        success = constellation_manager.create_walker_constellation()
        if not success:
            print("❌ 星座创建失败")
            return False

        print("✅ 星座创建成功")
        
        print("\n4️⃣ 获取卫星列表...")
        satellite_list = constellation_manager.get_satellite_list()
        print(f"卫星列表: {satellite_list}")
        
        print("\n5️⃣ 测试卫星查找...")
        if satellite_list:
            test_satellite_id = satellite_list[0]
            print(f"测试卫星ID: {test_satellite_id}")
            
            # 直接调用 _find_satellite 方法
            satellite_obj = stk_manager._find_satellite(test_satellite_id)
            if satellite_obj:
                print(f"✅ 成功找到卫星: {test_satellite_id}")
                print(f"   类名: {getattr(satellite_obj, 'ClassName', 'Unknown')}")
                print(f"   实例名: {getattr(satellite_obj, 'InstanceName', 'Unknown')}")
            else:
                print(f"❌ 未找到卫星: {test_satellite_id}")
        
        print("\n6️⃣ 测试位置获取...")
        if satellite_list:
            test_satellite_id = satellite_list[0]
            print(f"测试获取卫星 {test_satellite_id} 的位置...")
            
            # 测试时间偏移 0 秒（场景开始时间）
            position_data = stk_manager.get_satellite_position(test_satellite_id, "0", 30)
            if position_data:
                print(f"✅ 成功获取位置数据:")
                print(f"   时间: {position_data.get('time')}")
                if 'x' in position_data:
                    print(f"   坐标: ({position_data['x']:.2f}, {position_data['y']:.2f}, {position_data['z']:.2f})")
                elif 'latitude' in position_data:
                    print(f"   位置: ({position_data['latitude']:.6f}°, {position_data['longitude']:.6f}°, {position_data['altitude']:.2f}km)")
            else:
                print(f"❌ 未能获取位置数据")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始卫星ID调试测试...")
    
    success = test_satellite_creation_and_lookup()
    
    if success:
        print(f"\n🎉 测试完成！")
    else:
        print(f"\n⚠️ 测试失败，需要进一步调试。")
