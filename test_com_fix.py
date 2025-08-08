#!/usr/bin/env python3
"""
测试COM初始化修复是否有效
"""

def test_parallel_position_with_com_fix():
    """测试并行位置获取的COM修复"""
    try:
        print("=" * 60)
        print("🔍 测试并行位置获取COM修复")
        print("=" * 60)
        
        # 导入必要的模块
        from src.stk_interface.stk_manager import STKManager
        from src.meta_task.parallel_position_manager import ParallelPositionManager, PositionRequest
        from src.utils.config_manager import get_config_manager
        
        # 获取配置并连接STK
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()
        stk_manager = STKManager(stk_config)
        
        if not stk_manager.connect():
            print("❌ STK连接失败")
            return False
        
        print("✅ STK连接成功")
        
        # 初始化并行位置管理器
        parallel_manager = ParallelPositionManager(stk_manager)
        
        print("✅ 并行位置管理器初始化成功")
        
        # 创建测试请求
        from datetime import datetime, timedelta
        test_requests = []
        satellite_ids = ["Satellite01", "Satellite02", "Satellite03"]
        time_offsets = [0, 300, 600]  # 0秒, 5分钟, 10分钟

        base_time = datetime.now()

        for satellite_id in satellite_ids:
            for time_offset in time_offsets:
                sample_time = base_time + timedelta(seconds=time_offset)
                request = PositionRequest(
                    satellite_id=satellite_id,
                    time_offset=time_offset,
                    sample_time=sample_time
                )
                test_requests.append(request)
        
        print(f"📊 创建了 {len(test_requests)} 个测试请求")
        
        # 测试并行获取
        print(f"\n🚀 开始并行位置获取测试...")
        results = parallel_manager.get_positions_parallel(test_requests)
        
        # 分析结果
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        print(f"\n📊 测试结果:")
        print(f"   总请求数: {len(results)}")
        print(f"   成功数: {len(successful_results)}")
        print(f"   失败数: {len(failed_results)}")
        print(f"   成功率: {len(successful_results)/len(results)*100:.1f}%")
        
        # 显示成功的结果示例
        if successful_results:
            print(f"\n✅ 成功示例:")
            for i, result in enumerate(successful_results[:3]):  # 显示前3个
                pos_data = result.position_data
                if pos_data:
                    print(f"   {i+1}. {result.request.satellite_id} @ {result.request.time_offset}s:")
                    if 'x' in pos_data:
                        print(f"      坐标: ({pos_data['x']:.2f}, {pos_data['y']:.2f}, {pos_data['z']:.2f}) km")
                    elif 'latitude' in pos_data:
                        print(f"      位置: ({pos_data['latitude']:.6f}°, {pos_data['longitude']:.6f}°, {pos_data['altitude']:.2f}km)")
                    print(f"      处理时间: {result.processing_time:.3f}s")
        
        # 显示失败的原因
        if failed_results:
            print(f"\n❌ 失败示例:")
            error_counts = {}
            for result in failed_results:
                error = result.error or "未知错误"
                error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in error_counts.items():
                print(f"   {error}: {count}次")
        
        # 判断修复是否成功
        success_rate = len(successful_results) / len(results)
        if success_rate > 0.5:  # 成功率超过50%认为修复有效
            print(f"\n🎉 COM修复有效！成功率: {success_rate*100:.1f}%")
            return True
        else:
            print(f"\n⚠️ COM修复可能仍有问题，成功率较低: {success_rate*100:.1f}%")
            return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 开始COM修复测试...")
    
    success = test_parallel_position_with_com_fix()
    
    if success:
        print(f"\n🎉 COM修复测试通过！")
    else:
        print(f"\n⚠️ COM修复测试失败，需要进一步调试。")
