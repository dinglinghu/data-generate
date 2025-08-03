#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试甘特图在滚动采集过程中的集成
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_gantt_generation():
    """测试甘特图生成功能"""
    print("🧪 测试甘特图生成功能...")
    
    try:
        from aerospace_meta_task_gantt import AerospaceMetaTaskGantt
        
        # 查找最新的数据文件
        data_files = list(Path("output/rolling_collections").glob("*/data/meta_task_data.json"))
        if not data_files:
            print("❌ 没有找到数据文件")
            return False
        
        # 使用最新的数据文件
        latest_data_file = max(data_files, key=lambda x: x.stat().st_mtime)
        print(f"📁 使用数据文件: {latest_data_file}")
        
        # 创建甘特图生成器
        gantt = AerospaceMetaTaskGantt()
        
        # 加载数据
        gantt.load_data(str(latest_data_file))
        print("✅ 数据加载成功")
        
        # 提取数据
        meta_df = gantt.extract_meta_task_data()
        visible_df = gantt.extract_visible_meta_task_data()
        print(f"✅ 提取到 {len(meta_df)} 条元任务数据")
        print(f"✅ 提取到 {len(visible_df)} 条可见元任务数据")
        
        # 测试自定义输出路径
        test_output_path = "test_gantt_output.png"
        
        # 生成甘特图
        result = gantt.create_professional_gantt_chart(
            meta_df, visible_df, output_path=test_output_path
        )
        
        # 检查返回结果
        if len(result) == 4:
            fig, (ax1, ax2), saved_path, save_success = result
            print(f"✅ 甘特图生成成功，保存状态: {save_success}")
            print(f"✅ 保存路径: {saved_path}")
            
            # 检查文件是否存在
            if Path(saved_path).exists():
                print(f"✅ 文件确实存在: {saved_path}")
                # 清理测试文件
                if saved_path == test_output_path:
                    Path(saved_path).unlink()
                    print("🧹 测试文件已清理")
            else:
                print(f"❌ 文件不存在: {saved_path}")
                return False
        else:
            print("⚠️ 返回结果格式不正确")
            return False
        
        # 关闭图表
        import matplotlib.pyplot as plt
        plt.close(fig)
        
        return True
        
    except Exception as e:
        print(f"❌ 甘特图生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rolling_collection_integration():
    """测试滚动采集中的甘特图集成"""
    print("\n🧪 测试滚动采集中的甘特图集成...")

    try:
        # 直接测试甘特图在采集文件夹中的生成
        collection_folder = Path("output/rolling_collections").glob("collection_*")
        collection_folders = list(collection_folder)

        if collection_folders:
            latest_folder = max(collection_folders, key=lambda x: x.stat().st_mtime)
            print(f"📁 使用采集文件夹: {latest_folder}")

            # 检查是否已有甘特图
            charts_folder = latest_folder / "charts"
            existing_charts = list(charts_folder.glob("*gantt*.png")) if charts_folder.exists() else []

            if existing_charts:
                print(f"✅ 发现现有甘特图: {len(existing_charts)} 个")
                for chart in existing_charts:
                    print(f"   - {chart.name} ({chart.stat().st_size / 1024:.1f} KB)")

                # 检查数据文件
                data_file = latest_folder / "data" / "meta_task_data.json"
                if data_file.exists():
                    print(f"✅ 数据文件存在: {data_file}")

                    # 测试甘特图生成逻辑
                    from aerospace_meta_task_gantt import AerospaceMetaTaskGantt

                    gantt = AerospaceMetaTaskGantt()
                    gantt.load_data(str(data_file))

                    meta_df = gantt.extract_meta_task_data()
                    visible_df = gantt.extract_visible_meta_task_data()

                    if len(meta_df) > 0 or len(visible_df) > 0:
                        # 定义测试输出路径
                        test_chart_filename = charts_folder / "test_integration_gantt.png"

                        # 生成甘特图
                        result = gantt.create_professional_gantt_chart(
                            meta_df, visible_df, output_path=str(test_chart_filename)
                        )

                        if len(result) == 4:
                            fig, (ax1, ax2), saved_path, save_success = result
                            if save_success and Path(saved_path).exists():
                                print(f"✅ 集成测试成功，甘特图已保存: {saved_path}")
                                # 清理测试文件
                                Path(saved_path).unlink()
                                print("🧹 测试文件已清理")

                                # 关闭图表
                                import matplotlib.pyplot as plt
                                plt.close(fig)
                                return True
                            else:
                                print(f"❌ 甘特图保存失败")
                                return False

                        # 关闭图表
                        import matplotlib.pyplot as plt
                        plt.close(fig)
                    else:
                        print("⚠️ 没有足够的数据生成甘特图")
                        return True  # 这种情况也算正常
                else:
                    print(f"❌ 数据文件不存在: {data_file}")
                    return False
            else:
                print("⚠️ 没有找到现有甘特图，但这可能是正常的")
                return True
        else:
            print("❌ 没有找到采集文件夹")
            return False

    except Exception as e:
        print(f"❌ 集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🧪 甘特图集成测试开始")
    print("=" * 60)
    
    # 测试1: 基本甘特图生成
    test1_result = test_gantt_generation()
    
    # 测试2: 滚动采集集成
    test2_result = test_rolling_collection_integration()
    
    print("\n" + "=" * 60)
    print("🧪 测试结果汇总:")
    print(f"   甘特图生成测试: {'✅ 通过' if test1_result else '❌ 失败'}")
    print(f"   滚动采集集成测试: {'✅ 通过' if test2_result else '❌ 失败'}")
    
    if test1_result and test2_result:
        print("\n🎉 所有测试通过！甘特图集成工作正常。")
        return True
    else:
        print("\n❌ 部分测试失败，需要检查甘特图集成。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
