#!/usr/bin/env python3
"""
滚动数据采集管理器
负责管理多次数据采集，动态添加导弹，只采集中段飞行的导弹
"""

import logging
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 导入时间轴转换器
from ..utils.timeline_converter import TimelineConverter

logger = logging.getLogger(__name__)

class RollingDataCollector:
    """滚动数据采集管理器"""
    
    def __init__(self, collection_system):
        """初始化滚动数据采集管理器"""
        self.collection_system = collection_system
        self.stk_manager = collection_system.stk_manager
        self.missile_manager = collection_system.missile_manager
        self.data_collector = collection_system.meta_task_data_collector

        # 初始化时间轴转换器
        self.timeline_converter = TimelineConverter()
        
        # 获取配置
        from src.utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        self.config = config_manager.get_data_collection_config()
        self.rolling_config = self.config.get("rolling_collection", {})
        self.missile_config = config_manager.get_missile_config()
        
        # 滚动采集参数
        self.enable_rolling = self.rolling_config.get("enable", True)
        self.total_collections = self.rolling_config.get("total_collections", 10)
        self.interval_range = self.rolling_config.get("interval_range", [300, 900])
        self.max_scenario_duration = self.rolling_config.get("max_scenario_duration", 86400)
        
        # 导弹动态添加参数
        self.dynamic_config = self.rolling_config.get("dynamic_missiles", {})
        self.add_per_collection = self.dynamic_config.get("add_per_collection", 1)
        self.launch_at_collection_time = self.dynamic_config.get("launch_at_collection_time", True)
        self.only_midcourse_targets = self.dynamic_config.get("only_midcourse_targets", True)
        
        # 并发控制
        self.max_concurrent_missiles = self.missile_config.get("max_concurrent_missiles", 5)
        
        # 状态跟踪
        self.current_collection = 0
        self.scenario_start_time = None
        self.all_missiles = {}  # 所有创建的导弹
        self.collection_results = []  # 所有采集结果
        
        logger.info("🔄 滚动数据采集管理器初始化完成")
        logger.info(f"   总采集次数: {self.total_collections}")
        logger.info(f"   采集间隔: {self.interval_range[0]}-{self.interval_range[1]}秒")
        logger.info(f"   最大并发导弹: {self.max_concurrent_missiles}")
    
    async def start_rolling_collection(self) -> List[Dict[str, Any]]:
        """开始滚动数据采集"""
        try:
            logger.info("🚀 开始滚动数据采集")
            logger.info("=" * 80)
            
            # 初始化场景时间
            self.scenario_start_time = self._get_scenario_start_time()
            current_time = self.scenario_start_time
            
            logger.info(f"📅 场景开始时间: {current_time}")
            logger.info(f"🎯 计划采集次数: {self.total_collections}")
            
            # 执行滚动采集
            for collection_idx in range(self.total_collections):
                self.current_collection = collection_idx + 1
                
                logger.info(f"\n🔄 第 {self.current_collection}/{self.total_collections} 次数据采集")
                logger.info(f"⏰ 当前采集时刻: {current_time}")
                
                # 1. 动态添加导弹
                await self._add_missiles_for_collection(current_time)
                
                # 2. 筛选中段飞行的导弹
                midcourse_missiles = self._get_midcourse_missiles(current_time)
                
                if not midcourse_missiles:
                    logger.warning(f"⚠️ 第 {self.current_collection} 次采集：没有中段飞行的导弹")
                    # 计算下次采集时间
                    current_time = self._calculate_next_collection_time(current_time)
                    continue
                
                logger.info(f"🎯 当前中段飞行导弹: {len(midcourse_missiles)} 个")
                for missile_id in midcourse_missiles:
                    logger.info(f"   • {missile_id}")
                
                # 3. 执行数据采集
                collection_result = await self._execute_collection(current_time, midcourse_missiles)
                
                if collection_result:
                    self.collection_results.append(collection_result)
                    logger.info(f"✅ 第 {self.current_collection} 次采集完成")
                else:
                    logger.error(f"❌ 第 {self.current_collection} 次采集失败")
                
                # 4. 计算下次采集时间
                if self.current_collection < self.total_collections:
                    current_time = self._calculate_next_collection_time(current_time)
                    
                    # 检查是否超过最大场景时间
                    if self._is_scenario_time_exceeded(current_time):
                        logger.warning("⚠️ 场景时间超过最大限制，停止采集")
                        break
            
            logger.info("\n" + "=" * 80)
            logger.info(f"🎉 滚动数据采集完成！")
            logger.info(f"   总采集次数: {len(self.collection_results)}")
            logger.info(f"   总导弹数: {len(self.all_missiles)}")
            
            return self.collection_results
            
        except Exception as e:
            logger.error(f"❌ 滚动数据采集失败: {e}")
            return []
    
    async def _add_missiles_for_collection(self, collection_time: datetime):
        """为当前采集添加导弹"""
        try:
            logger.info(f"🚀 为第 {self.current_collection} 次采集添加导弹...")
            
            # 检查当前中段飞行的导弹数量
            current_midcourse = len(self._get_midcourse_missiles(collection_time))
            
            # 计算需要添加的导弹数量
            missiles_to_add = min(
                self.add_per_collection,
                max(0, self.max_concurrent_missiles - current_midcourse)
            )
            
            if missiles_to_add <= 0:
                logger.info(f"   当前中段飞行导弹数 ({current_midcourse}) 已达到最大值 ({self.max_concurrent_missiles})")
                return
            
            logger.info(f"   计划添加导弹数: {missiles_to_add}")
            
            # 添加导弹
            for i in range(missiles_to_add):
                missile_id = f"RollingThreat_{self.current_collection:03d}_{i+1:02d}_{random.randint(1000, 9999)}"
                
                # 生成导弹配置
                missile_config = self._generate_missile_config(missile_id, collection_time)
                
                # 创建导弹
                success = await self._create_missile(missile_id, missile_config)
                
                if success:
                    self.all_missiles[missile_id] = missile_config
                    logger.info(f"   ✅ 导弹创建成功: {missile_id}")
                else:
                    logger.error(f"   ❌ 导弹创建失败: {missile_id}")
            
        except Exception as e:
            logger.error(f"❌ 添加导弹失败: {e}")
    
    def _get_midcourse_missiles(self, current_time: datetime) -> List[str]:
        """获取当前时刻正在中段飞行的导弹"""
        try:
            midcourse_missiles = []
            
            for missile_id, missile_config in self.all_missiles.items():
                if self._is_missile_in_midcourse(missile_id, missile_config, current_time):
                    midcourse_missiles.append(missile_id)
            
            return midcourse_missiles
            
        except Exception as e:
            logger.error(f"❌ 获取中段飞行导弹失败: {e}")
            return []
    
    def _is_missile_in_midcourse(self, missile_id: str, missile_config: Dict, current_time: datetime) -> bool:
        """判断导弹是否在中段飞行"""
        try:
            launch_time = missile_config.get("launch_time")
            if not isinstance(launch_time, datetime):
                return False

            # 计算中段飞行时间
            flight_duration = missile_config.get("flight_duration", 1800)  # 默认30分钟
            midcourse_start_offset = flight_duration * 0.1  # 中段开始：飞行时间的10%
            midcourse_end_offset = flight_duration * 0.9    # 中段结束：飞行时间的90%

            midcourse_start = launch_time + timedelta(seconds=midcourse_start_offset)
            midcourse_end = launch_time + timedelta(seconds=midcourse_end_offset)

            # 判断当前时间是否在中段飞行时间内
            is_in_midcourse = midcourse_start <= current_time <= midcourse_end

            if is_in_midcourse:
                logger.debug(f"✅ 导弹 {missile_id} 在中段飞行: {midcourse_start} <= {current_time} <= {midcourse_end}")
            else:
                logger.debug(f"❌ 导弹 {missile_id} 不在中段飞行: {midcourse_start} <= {current_time} <= {midcourse_end}")

            return is_in_midcourse

        except Exception as e:
            logger.error(f"❌ 判断导弹中段飞行状态失败 {missile_id}: {e}")
            return False

    async def _execute_collection(self, collection_time: datetime, midcourse_missiles: List[str]) -> Optional[Dict[str, Any]]:
        """执行数据采集"""
        try:
            logger.info(f"📊 执行第 {self.current_collection} 次数据采集...")

            # 创建本次采集的专用文件夹
            collection_folder = self._create_collection_folder(collection_time)

            # 临时设置导弹管理器的目标列表为当前中段飞行的导弹
            original_targets = self.missile_manager.missile_targets.copy()

            # 筛选中段飞行的导弹
            midcourse_targets = {
                missile_id: self.all_missiles[missile_id]
                for missile_id in midcourse_missiles
                if missile_id in self.all_missiles
            }

            self.missile_manager.missile_targets = midcourse_targets

            # 执行数据采集
            collection_result = self.data_collector.collect_complete_meta_task_data(collection_time)

            # 恢复原始目标列表
            self.missile_manager.missile_targets = original_targets

            if collection_result:
                # 添加滚动采集的元数据
                collection_result["rolling_collection_info"] = {
                    "collection_index": self.current_collection,
                    "collection_time": collection_time.isoformat(),
                    "midcourse_missiles": midcourse_missiles,
                    "total_missiles_in_scenario": len(self.all_missiles),
                    "collection_folder": str(collection_folder)
                }

                # 保存本次采集的数据到专用文件夹
                await self._save_collection_data(collection_result, collection_folder)

                # 生成可视化数据
                await self._generate_collection_visualizations(collection_result, collection_folder)

                logger.info(f"✅ 第 {self.current_collection} 次数据采集成功，数据保存到: {collection_folder}")
                return collection_result
            else:
                logger.error(f"❌ 第 {self.current_collection} 次数据采集失败")
                return None

        except Exception as e:
            logger.error(f"❌ 执行数据采集失败: {e}")
            return None

    def _generate_missile_config(self, missile_id: str, launch_time: datetime) -> Dict[str, Any]:
        """生成导弹配置"""
        try:
            # 生成随机发射和目标位置
            launch_position = self._generate_random_launch_position()
            target_position = self._generate_random_target_position()

            # 从配置获取飞行时间范围，使用标准化的飞行时间
            flight_duration_range = self.config.get("dynamic_missiles", {}).get("flight_duration_range", [1800, 2400])
            min_duration, max_duration = flight_duration_range

            # 使用正态分布生成更一致的飞行时间
            mean_duration = (min_duration + max_duration) / 2
            std_duration = (max_duration - min_duration) / 6

            flight_duration = max(min_duration,
                                min(max_duration,
                                    int(random.normalvariate(mean_duration, std_duration))))

            return {
                "missile_id": missile_id,
                "launch_position": launch_position,
                "target_position": target_position,
                "launch_time": launch_time,
                "flight_duration": flight_duration,
                "creation_time": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ 生成导弹配置失败 {missile_id}: {e}")
            return {}

    async def _create_missile(self, missile_id: str, missile_config: Dict[str, Any]) -> bool:
        """创建导弹对象"""
        try:
            # 使用导弹管理器创建导弹
            result = self.missile_manager.create_single_missile_target({
                "missile_id": missile_id,
                "launch_position": missile_config["launch_position"],
                "target_position": missile_config["target_position"],
                "launch_time": missile_config["launch_time"]
            })

            # 导弹管理器返回导弹信息字典表示成功，None表示失败
            return result is not None

        except Exception as e:
            logger.error(f"❌ 创建导弹对象失败 {missile_id}: {e}")
            return False

    def _calculate_next_collection_time(self, current_time: datetime) -> datetime:
        """计算下次采集时间 - 优化为更均匀的分布"""
        try:
            # 使用正态分布生成更均匀的时间间隔
            min_interval, max_interval = self.interval_range
            mean_interval = (min_interval + max_interval) / 2
            std_interval = (max_interval - min_interval) / 6  # 99.7%的值在范围内

            # 生成正态分布的时间间隔
            interval_seconds = max(min_interval,
                                 min(max_interval,
                                     int(random.normalvariate(mean_interval, std_interval))))

            next_time = current_time + timedelta(seconds=interval_seconds)

            logger.info(f"⏰ 下次采集时间: {next_time} (间隔: {interval_seconds}秒, 均值: {mean_interval:.0f}秒)")

            return next_time

        except Exception as e:
            logger.error(f"❌ 计算下次采集时间失败: {e}")
            return current_time + timedelta(seconds=450)  # 默认7.5分钟

    def _get_scenario_start_time(self) -> datetime:
        """获取场景开始时间"""
        try:
            # 从STK获取场景开始时间
            scenario_start_str = self.stk_manager.scenario.StartTime
            # 解析STK时间格式: "25 Jul 2025 00:00:00.000"
            scenario_start = datetime.strptime(scenario_start_str.split('.')[0], "%d %b %Y %H:%M:%S")
            return scenario_start

        except Exception as e:
            logger.error(f"❌ 获取场景开始时间失败: {e}")
            return datetime.now()

    def _is_scenario_time_exceeded(self, current_time: datetime) -> bool:
        """检查是否超过最大场景时间"""
        try:
            if not self.scenario_start_time:
                return False

            elapsed_seconds = (current_time - self.scenario_start_time).total_seconds()
            return elapsed_seconds > self.max_scenario_duration

        except Exception as e:
            logger.error(f"❌ 检查场景时间失败: {e}")
            return False

    def _generate_random_launch_position(self) -> Dict[str, float]:
        """生成随机发射位置"""
        # 使用更合理的地理范围，键名与导弹管理器保持一致
        return {
            "lat": random.uniform(30.0, 50.0),   # 北纬30-50度
            "lon": random.uniform(100.0, 140.0), # 东经100-140度
            "alt": 0.0
        }

    def _generate_random_target_position(self) -> Dict[str, float]:
        """生成随机目标位置"""
        # 使用更合理的目标区域，键名与导弹管理器保持一致
        return {
            "lat": random.uniform(35.0, 45.0),    # 北纬35-45度
            "lon": random.uniform(-125.0, -70.0), # 西经125-70度
            "alt": 0.0
        }

    def _create_collection_folder(self, collection_time: datetime) -> str:
        """创建本次采集的专用文件夹"""
        try:
            from pathlib import Path

            # 创建文件夹名称：collection_YYYYMMDD_HHMMSS_N
            timestamp = collection_time.strftime("%Y%m%d_%H%M%S")
            folder_name = f"collection_{timestamp}_{self.current_collection:02d}"

            # 创建完整路径
            base_path = Path("output/rolling_collections")
            collection_folder = base_path / folder_name

            # 创建文件夹结构
            collection_folder.mkdir(parents=True, exist_ok=True)
            (collection_folder / "data").mkdir(exist_ok=True)
            (collection_folder / "charts").mkdir(exist_ok=True)
            (collection_folder / "logs").mkdir(exist_ok=True)

            logger.info(f"📁 创建采集文件夹: {collection_folder}")

            return collection_folder

        except Exception as e:
            logger.error(f"❌ 创建采集文件夹失败: {e}")
            return "output/data"  # 回退到默认路径

    async def _save_collection_data(self, collection_result: Dict[str, Any], collection_folder: str):
        """保存本次采集的数据到专用文件夹"""
        try:
            import json
            from pathlib import Path

            collection_folder = Path(collection_folder)

            # 保存主要采集数据
            data_file = collection_folder / "data" / "meta_task_data.json"
            with open(data_file, 'w', encoding='utf-8') as f:
                json.dump(collection_result, f, indent=2, ensure_ascii=False, default=str)

            # 转换并保存时间轴数据
            logger.info(f"🔄 转换时间轴数据...")
            timeline_data = self.timeline_converter.convert_collection_data(collection_result)

            if timeline_data:
                timeline_file = collection_folder / "data" / "timeline_data.json"
                with open(timeline_file, 'w', encoding='utf-8') as f:
                    json.dump(timeline_data, f, indent=2, ensure_ascii=False, default=str)
                logger.info(f"⏱️ 时间轴数据已保存: {timeline_file}")
            else:
                logger.warning(f"⚠️ 时间轴数据转换失败，跳过保存")

            # 保存采集摘要信息
            summary = {
                "collection_info": collection_result.get("rolling_collection_info", {}),
                "meta_tasks_summary": {
                    "total_missiles": len(collection_result.get("meta_tasks", {}).get("meta_tasks", {})),
                    "total_meta_tasks": sum(len(missile_data.get("atomic_tasks", []))
                                          for missile_data in collection_result.get("meta_tasks", {}).get("meta_tasks", {}).values()),
                    "total_real_tasks": sum(missile_data.get("real_task_count", 0)
                                          for missile_data in collection_result.get("meta_tasks", {}).get("meta_tasks", {}).values()),
                    "total_virtual_tasks": sum(missile_data.get("virtual_task_count", 0)
                                             for missile_data in collection_result.get("meta_tasks", {}).get("meta_tasks", {}).values())
                },
                "visible_tasks_summary": {
                    "total_satellites": len(collection_result.get("visible_meta_tasks", {}).get("constellation_visible_task_sets", {})),
                    "total_visible_tasks": sum(len(satellite_data.get("visible_tasks", []))
                                             for satellite_data in collection_result.get("visible_meta_tasks", {}).get("constellation_visible_task_sets", {}).values()),
                    "total_virtual_visible_tasks": sum(len(satellite_data.get("virtual_tasks", []))
                                                     for satellite_data in collection_result.get("visible_meta_tasks", {}).get("constellation_visible_task_sets", {}).values())
                }
            }

            summary_file = collection_folder / "data" / "collection_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"💾 采集数据已保存: {data_file}")
            logger.info(f"📋 采集摘要已保存: {summary_file}")

        except Exception as e:
            logger.error(f"❌ 保存采集数据失败: {e}")

    async def _generate_collection_visualizations(self, collection_result: Dict[str, Any], collection_folder: str):
        """生成本次采集的可视化数据"""
        try:
            from pathlib import Path

            collection_folder = Path(collection_folder)
            charts_folder = collection_folder / "charts"

            logger.info(f"📊 生成第 {self.current_collection} 次采集的可视化数据...")

            # 生成甘特图
            try:
                # 直接调用甘特图生成器，而不是使用子进程
                from aerospace_meta_task_gantt import AerospaceMetaTaskGantt

                # 使用实际保存的数据文件路径
                actual_data_file = collection_folder / "data" / "meta_task_data.json"

                # 确保数据文件存在
                if not actual_data_file.exists():
                    logger.warning(f"⚠️ 数据文件不存在: {actual_data_file}")
                    return

                # 创建甘特图生成器
                gantt = AerospaceMetaTaskGantt()

                # 加载数据
                gantt.load_data(str(actual_data_file))

                # 提取数据
                meta_df = gantt.extract_meta_task_data()
                visible_df = gantt.extract_visible_meta_task_data()

                logger.info(f"📊 提取到 {len(meta_df)} 条元任务数据")
                logger.info(f"👁️ 提取到 {len(visible_df)} 条可见元任务数据")

                if len(meta_df) == 0 and len(visible_df) == 0:
                    logger.warning("⚠️ 没有足够的数据生成甘特图")
                    return

                # 确保图表输出目录存在
                charts_folder.mkdir(parents=True, exist_ok=True)

                # 定义输出路径
                chart_filename = charts_folder / f"collection_{self.current_collection:02d}_aerospace_meta_task_gantt.png"

                # 生成甘特图
                result = gantt.create_professional_gantt_chart(
                    meta_df, visible_df, output_path=str(chart_filename)
                )

                # 处理返回结果
                if len(result) == 4:
                    fig, (ax1, ax2), saved_path, save_success = result
                    if save_success:
                        logger.info(f"📈 甘特图已保存: {saved_path}")
                    else:
                        logger.warning(f"⚠️ 甘特图保存失败，但图表已生成")
                else:
                    fig, (ax1, ax2) = result
                    logger.info(f"📈 甘特图已生成: {chart_filename}")

                # 关闭图表以释放内存
                import matplotlib.pyplot as plt
                plt.close(fig)

            except Exception as e:
                logger.warning(f"⚠️ 甘特图生成异常: {e}")
                import traceback
                logger.warning(f"⚠️ 详细错误: {traceback.format_exc()}")



            # 生成采集信息文本文件
            info_file = collection_folder / "collection_info.txt"
            with open(info_file, 'w', encoding='utf-8') as f:
                rolling_info = collection_result.get("rolling_collection_info", {})
                f.write(f"滚动数据采集 - 第 {self.current_collection} 次\n")
                f.write("=" * 50 + "\n")
                f.write(f"采集时间: {rolling_info.get('collection_time', 'Unknown')}\n")
                f.write(f"中段飞行导弹: {len(rolling_info.get('midcourse_missiles', []))} 个\n")
                f.write(f"场景总导弹数: {rolling_info.get('total_missiles_in_scenario', 0)} 个\n")
                f.write(f"数据文件夹: {collection_folder}\n")
                f.write("\n中段飞行导弹列表:\n")
                for missile_id in rolling_info.get('midcourse_missiles', []):
                    f.write(f"  • {missile_id}\n")

            logger.info(f"📄 采集信息已保存: {info_file}")

        except Exception as e:
            logger.error(f"❌ 生成可视化数据失败: {e}")
