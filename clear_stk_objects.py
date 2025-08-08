#!/usr/bin/env python3
"""
清理STK中的对象
"""

def clear_stk_objects():
    """清理STK中的卫星和导弹"""
    try:
        from src.stk_interface.stk_manager import STKManager
        from src.utils.config_manager import get_config_manager
        
        print("=" * 60)
        print("🧹 清理STK对象")
        print("=" * 60)
        
        # 获取配置并连接STK
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()
        stk_manager = STKManager(stk_config)
        
        if not stk_manager.connect():
            print("❌ STK连接失败")
            return False
        
        print("✅ STK连接成功")
        
        # 获取场景
        scenario = stk_manager.scenario
        
        # 清理卫星
        satellites_removed = 0
        missiles_removed = 0
        
        print("\n🛰️ 清理卫星...")
        for i in range(scenario.Children.Count - 1, -1, -1):  # 倒序遍历避免索引问题
            child = scenario.Children.Item(i)
            if getattr(child, 'ClassName', None) == 'Satellite':
                satellite_name = getattr(child, 'InstanceName', 'Unknown')
                try:
                    scenario.Children.Unload(satellite_name)
                    satellites_removed += 1
                    print(f"   ✅ 删除卫星: {satellite_name}")
                except Exception as e:
                    print(f"   ❌ 删除卫星失败 {satellite_name}: {e}")
        
        print(f"\n🚀 清理导弹...")
        for i in range(scenario.Children.Count - 1, -1, -1):  # 倒序遍历避免索引问题
            child = scenario.Children.Item(i)
            if getattr(child, 'ClassName', None) == 'Missile':
                missile_name = getattr(child, 'InstanceName', 'Unknown')
                try:
                    scenario.Children.Unload(missile_name)
                    missiles_removed += 1
                    print(f"   ✅ 删除导弹: {missile_name}")
                except Exception as e:
                    print(f"   ❌ 删除导弹失败 {missile_name}: {e}")
        
        print(f"\n📊 清理完成:")
        print(f"   删除卫星: {satellites_removed} 个")
        print(f"   删除导弹: {missiles_removed} 个")
        
        # 检查剩余对象
        remaining_objects = []
        for i in range(scenario.Children.Count):
            child = scenario.Children.Item(i)
            class_name = getattr(child, 'ClassName', 'Unknown')
            instance_name = getattr(child, 'InstanceName', 'Unknown')
            remaining_objects.append(f"{class_name}: {instance_name}")
        
        if remaining_objects:
            print(f"\n📋 剩余对象:")
            for obj in remaining_objects:
                print(f"   {obj}")
        else:
            print(f"\n✅ 场景已清空")
        
        return True
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始清理STK对象...")
    
    success = clear_stk_objects()
    
    if success:
        print(f"\n🎉 STK对象清理完成！")
    else:
        print(f"\n⚠️ STK对象清理失败。")
