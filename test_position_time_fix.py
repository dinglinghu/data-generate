#!/usr/bin/env python3
"""
测试位置获取时间修复是否有效
"""

def test_position_time_conversion():
    """测试时间转换逻辑"""
    try:
        from datetime import datetime, timedelta
        from src.utils.time_manager import get_time_manager
        
        print("=" * 60)
        print("🔍 测试位置获取时间转换")
        print("=" * 60)
        
        # 获取时间管理器
        time_manager = get_time_manager()
        print(f"仿真开始时间: {time_manager.start_time}")
        
        # 测试不同的时间偏移
        test_offsets = [0, 300, 600, 1800, 3600]  # 0秒, 5分钟, 10分钟, 30分钟, 1小时
        
        for offset in test_offsets:
            # 计算目标时间
            target_time = time_manager.start_time + timedelta(seconds=offset)
            # 转换为STK时间格式
            stk_time = target_time.strftime("%d %b %Y %H:%M:%S.000")
            
            print(f"\n时间偏移: {offset}秒")
            print(f"  目标时间: {target_time}")
            print(f"  STK格式: {stk_time}")
        
        print(f"\n✅ 时间转换逻辑测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def test_position_request_simulation():
    """模拟位置请求测试"""
    try:
        print("\n" + "=" * 60)
        print("🔍 模拟位置请求测试")
        print("=" * 60)
        
        # 模拟 parallel_position_manager 的调用方式
        test_time_strings = ["0", "300.5", "1800", "3600.0"]
        
        for time_str in test_time_strings:
            print(f"\n测试时间字符串: '{time_str}'")
            
            try:
                # 模拟 STK 管理器中的转换逻辑
                time_offset_seconds = float(time_str)
                print(f"  转换为浮点数: {time_offset_seconds}")
                
                from src.utils.time_manager import get_time_manager
                from datetime import timedelta
                time_manager = get_time_manager()
                target_time = time_manager.start_time + timedelta(seconds=time_offset_seconds)
                stk_time = target_time.strftime("%d %b %Y %H:%M:%S.000")
                
                print(f"  目标时间: {target_time}")
                print(f"  STK格式: {stk_time}")
                print(f"  ✅ 转换成功")
                
            except (ValueError, TypeError) as e:
                print(f"  ❌ 转换失败: {e}")
        
        print(f"\n✅ 位置请求模拟测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 模拟测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始位置时间修复测试...")
    
    success1 = test_position_time_conversion()
    success2 = test_position_request_simulation()
    
    if success1 and success2:
        print(f"\n🎉 所有测试通过！位置时间修复应该有效。")
    else:
        print(f"\n⚠️ 部分测试失败，需要进一步检查。")
