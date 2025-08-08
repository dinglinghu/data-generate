#!/usr/bin/env python3
"""
测试 max_scenario_duration 配置是否生效
"""

def test_max_scenario_duration():
    """测试最大场景持续时间配置"""
    try:
        from src.utils.config_manager import get_config_manager
        
        print("=" * 60)
        print("🔍 测试 max_scenario_duration 配置")
        print("=" * 60)
        
        config_manager = get_config_manager()
        
        # 方法1：直接从顶级配置读取（新方式）
        print("\n1️⃣ 从顶级 data_collection 读取：")
        top_data_config = config_manager.config.get("data_collection", {})
        rolling_config = top_data_config.get("rolling_collection", {})
        max_duration = rolling_config.get("max_scenario_duration", "未找到")
        
        print(f"   max_scenario_duration: {max_duration}")
        if max_duration != "未找到":
            print(f"   转换为小时: {max_duration/3600:.1f}小时")
            print(f"   转换为天: {max_duration/86400:.1f}天")
        
        # 方法2：模拟 RollingDataCollector 的读取方式
        print("\n2️⃣ 模拟 RollingDataCollector 读取：")
        config = config_manager.config.get("data_collection", {})
        rolling_config_sim = config.get("rolling_collection", {})
        max_duration_sim = rolling_config_sim.get("max_scenario_duration", 604800)
        
        print(f"   读取到的值: {max_duration_sim}")
        print(f"   转换为小时: {max_duration_sim/3600:.1f}小时")
        print(f"   转换为天: {max_duration_sim/86400:.1f}天")
        
        # 检查是否匹配
        print(f"\n3️⃣ 配置一致性检查：")
        if max_duration == max_duration_sim:
            print("   ✅ 配置读取一致")
        else:
            print("   ❌ 配置读取不一致")
            print(f"      方法1: {max_duration}")
            print(f"      方法2: {max_duration_sim}")
        
        return max_duration_sim
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None

if __name__ == "__main__":
    result = test_max_scenario_duration()
    if result:
        print(f"\n🎉 max_scenario_duration 配置生效: {result}秒")
    else:
        print("\n⚠️ max_scenario_duration 配置可能有问题")
