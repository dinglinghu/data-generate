#!/usr/bin/env python3
"""
重新创建卫星星座
"""

import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def recreate_constellation():
    """重新创建卫星星座"""
    try:
        print("=" * 60)
        print("🌟 重新创建卫星星座")
        print("=" * 60)
        
        from src.stk_interface.stk_manager import STKManager
        from src.constellation.constellation_manager import ConstellationManager
        from src.utils.config_manager import get_config_manager
        
        # 获取配置并连接STK
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()
        stk_manager = STKManager(stk_config)
        
        if not stk_manager.connect():
            print("❌ STK连接失败")
            return False
        
        print("✅ STK连接成功")
        
        # 检查当前场景中的卫星
        scenario = stk_manager.scenario
        current_satellites = []
        
        print(f"\n🔍 检查当前场景中的对象:")
        for i in range(scenario.Children.Count):
            child = scenario.Children.Item(i)
            class_name = getattr(child, 'ClassName', 'Unknown')
            instance_name = getattr(child, 'InstanceName', 'Unknown')
            
            print(f"   {class_name}: {instance_name}")
            
            if class_name == 'Satellite':
                current_satellites.append(instance_name)
        
        print(f"\n📊 当前场景统计:")
        print(f"   总对象数: {scenario.Children.Count}")
        print(f"   卫星数量: {len(current_satellites)}")
        
        if current_satellites:
            print(f"   现有卫星: {', '.join(current_satellites[:10])}")  # 只显示前10个
            if len(current_satellites) > 10:
                print(f"   ... 还有 {len(current_satellites) - 10} 颗卫星")
        
        # 如果没有卫星，创建星座
        if len(current_satellites) == 0:
            print(f"\n🌟 场景中没有卫星，开始创建星座...")
            
            # 创建星座管理器
            constellation_manager = ConstellationManager(stk_manager, config_manager)
            
            # 强制创建星座（跳过现有项目检测）
            print(f"🚀 开始创建Walker星座...")
            
            # 获取星座配置
            constellation_config = config_manager.get_constellation_config()
            planes = constellation_config.get("planes", 3)
            sats_per_plane = constellation_config.get("satellites_per_plane", 8)
            total_satellites = planes * sats_per_plane
            
            print(f"📊 星座配置:")
            print(f"   轨道面数: {planes}")
            print(f"   每面卫星数: {sats_per_plane}")
            print(f"   总卫星数: {total_satellites}")
            
            # 直接调用创建方法
            success = constellation_manager._create_walker_satellites(planes, sats_per_plane)
            
            if success:
                print(f"✅ 星座创建成功！")
                
                # 重新检查卫星数量
                new_satellites = []
                for i in range(scenario.Children.Count):
                    child = scenario.Children.Item(i)
                    if getattr(child, 'ClassName', '') == 'Satellite':
                        new_satellites.append(getattr(child, 'InstanceName', ''))
                
                print(f"📊 创建后统计:")
                print(f"   新卫星数量: {len(new_satellites)}")
                if new_satellites:
                    print(f"   卫星列表: {', '.join(new_satellites[:10])}")
                    if len(new_satellites) > 10:
                        print(f"   ... 还有 {len(new_satellites) - 10} 颗卫星")
                
            else:
                print(f"❌ 星座创建失败")
                return False
        
        else:
            print(f"\n✅ 场景中已有 {len(current_satellites)} 颗卫星，无需重新创建")
        
        # 测试几颗卫星的位置获取
        print(f"\n🧪 测试卫星位置获取:")
        
        # 获取最新的卫星列表
        test_satellites = []
        for i in range(scenario.Children.Count):
            child = scenario.Children.Item(i)
            if getattr(child, 'ClassName', '') == 'Satellite':
                test_satellites.append(getattr(child, 'InstanceName', ''))
        
        # 测试前5颗卫星
        test_count = min(5, len(test_satellites))
        success_count = 0
        
        for i in range(test_count):
            satellite_id = test_satellites[i]
            try:
                position_data = stk_manager.get_satellite_position(satellite_id, "0", timeout=10)
                if position_data:
                    print(f"   ✅ {satellite_id}: 位置获取成功")
                    success_count += 1
                else:
                    print(f"   ❌ {satellite_id}: 位置获取失败 (返回None)")
            except Exception as e:
                print(f"   ❌ {satellite_id}: 位置获取异常 - {e}")
        
        print(f"\n📊 位置测试结果:")
        print(f"   测试卫星数: {test_count}")
        print(f"   成功数: {success_count}")
        print(f"   成功率: {success_count/max(1, test_count)*100:.1f}%")
        
        if success_count > 0:
            print(f"✅ 卫星星座工作正常！")
            return True
        else:
            print(f"⚠️ 卫星位置获取存在问题")
            return False
        
    except Exception as e:
        print(f"❌ 重新创建星座失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始重新创建卫星星座...")
    
    success = recreate_constellation()
    
    if success:
        print(f"\n🎉 卫星星座重新创建完成！")
    else:
        print(f"\n⚠️ 卫星星座重新创建失败。")
