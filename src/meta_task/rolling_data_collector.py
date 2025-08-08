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
        self.time_manager = collection_system.time_manager

        # 初始化时间轴转换器
        self.timeline_converter = TimelineConverter()
        
        # 获取配置
        from src.utils.config_manager import get_config_manager
        self.config_manager = get_config_manager()  # 保存为实例属性
        # 直接从顶级配置获取 data_collection，而不是从 simulation.data_collection
        self.config = self.config_manager.config.get("data_collection", {})
        self.rolling_config = self.config.get("rolling_collection", {})
        self.missile_config = self.config_manager.get_missile_config()
        
        # 滚动采集参数
        self.enable_rolling = self.rolling_config.get("enable", True)
        self.total_collections = self.rolling_config.get("total_collections", 10)
        self.interval_range = self.rolling_config.get("interval_range", [300, 900])
        self.max_scenario_duration = self.rolling_config.get("max_scenario_duration", 604800)
        
        # 导弹动态管理参数
        self.dynamic_config = self.rolling_config.get("dynamic_missiles", {})
        self.missile_count_range = self.dynamic_config.get("missile_count_range", [2, 5])
        self.clear_existing_missiles = self.dynamic_config.get("clear_existing_missiles", True)
        self.launch_at_collection_time = self.dynamic_config.get("launch_at_collection_time", True)
        self.launch_time_offset_range = self.dynamic_config.get("launch_time_offset_range", [-300, 300])
        self.only_midcourse_targets = self.dynamic_config.get("only_midcourse_targets", True)
        self.flight_duration_range = self.dynamic_config.get("flight_duration_range", [1800, 2400])
        
        # 并发控制（已移除最大并发导弹数限制）

        # 导弹池管理器（性能优化）
        self.use_missile_pool = True  # 启用导弹池优化
        self.missile_pool_manager = None

        # 状态跟踪
        self.current_collection = 0
        self.scenario_start_time = None
        self.all_missiles = {}  # 所有创建的导弹
        self.collection_results = []  # 所有采集结果

        # 输出控制
        self.output_base_dir = None  # 输出基础目录，由外部设置
        self.enable_gantt = True     # 是否生成甘特图，由外部设置
        self.session_name = None     # 会话名称，由外部设置

        # 初始化冲突消解和统一数据管理组件
        from src.conflict_resolution.conflict_data_processor import ConflictResolutionDataProcessor
        from src.data_management.unified_data_manager import UnifiedDataManager

        self.conflict_processor = ConflictResolutionDataProcessor(self.config_manager)
        self.unified_data_manager = UnifiedDataManager(self.config_manager)
        self.unified_session_initialized = False

        logger.info("🔄 滚动数据采集管理器初始化完成")
        logger.info(f"   总采集次数: {self.total_collections}")
        logger.info(f"   采集间隔: {self.interval_range[0]}-{self.interval_range[1]}秒")
        logger.info(f"   最大场景持续时间: {self.max_scenario_duration}秒 ({self.max_scenario_duration/3600:.1f}小时)")
        logger.info(f"   导弹数量范围: {self.missile_count_range[0]}-{self.missile_count_range[1]}")
        logger.info(f"   导弹池优化: {'启用' if self.use_missile_pool else '禁用'}")
    
    async def initialize_missile_pool(self) -> bool:
        """初始化导弹池（性能优化）"""
        if not self.use_missile_pool:
            return True

        try:
            logger.info("🏊 初始化导弹池管理器...")

            # 导入导弹池管理器
            from src.optimization.missile_pool_manager import MissilePoolManager

            # 创建导弹池管理器
            self.missile_pool_manager = MissilePoolManager(
                self.collection_system.stk_manager,
                self.collection_system.config_manager,
                self.missile_manager
            )

            # 初始化导弹池
            success = await self.missile_pool_manager.initialize_pool()

            if success:
                logger.info("✅ 导弹池初始化成功")
                return True
            else:
                logger.warning("⚠️ 导弹池初始化失败，回退到传统模式")
                self.use_missile_pool = False
                return True

        except Exception as e:
            logger.error(f"❌ 导弹池初始化异常: {e}")
            logger.warning("⚠️ 回退到传统导弹创建模式")
            self.use_missile_pool = False
            return True

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
            
            # 初始化导弹池（如果启用）
            await self.initialize_missile_pool()

            # 执行滚动采集
            for collection_idx in range(self.total_collections):
                self.current_collection = collection_idx + 1

                logger.info(f"\n🔄 第 {self.current_collection}/{self.total_collections} 次数据采集")
                logger.info(f"⏰ 当前采集时刻: {current_time}")

                # 1. 动态管理导弹（清理旧导弹，创建新导弹）
                await self._manage_missiles_for_collection(current_time)
                
                # 2. 筛选有中段飞行阶段的导弹（基于轨迹分析，不依赖采集时间）
                midcourse_missiles = self._get_midcourse_missiles(current_time)

                # 监控导弹池状态
                if self.use_missile_pool and self.missile_pool_manager:
                    available_count = len(self.missile_pool_manager.available_missiles)
                    active_count = len(self.missile_pool_manager.active_missiles)
                    total_count = len(self.missile_pool_manager.missile_pool)
                    logger.info(f"📊 导弹池状态: 可用={available_count}, 活跃={active_count}, 总计={total_count}")

                if not midcourse_missiles:
                    logger.warning(f"⚠️ 第 {self.current_collection} 次采集：没有中段飞行的导弹")
                    # 计算下次采集时间
                    current_time = self._calculate_next_collection_time(current_time)

                    # 检查是否超过最大场景时间
                    if self._is_scenario_time_exceeded(current_time):
                        logger.warning("⚠️ 场景时间超过最大限制，停止采集")
                        break
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

                # 4. 立即释放本次采集使用的导弹回池中
                await self._release_current_missiles()
                
                # 5. 计算下次采集时间
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
    
    async def _manage_missiles_for_collection(self, collection_time: datetime):
        """为当前采集管理导弹（清理旧导弹，创建新导弹）"""
        try:
            logger.info(f"🚀 为第 {self.current_collection} 次采集管理导弹...")

            # 1. 清理现有导弹（如果配置启用）
            if self.clear_existing_missiles:
                await self._clear_existing_missiles()

            # 2. 生成随机导弹数量
            min_count, max_count = self.missile_count_range
            missiles_to_create = random.randint(min_count, max_count)

            logger.info(f"   计划创建导弹数: {missiles_to_create} (范围: {min_count}-{max_count})")

            # 3. 创建新导弹（使用导弹池或传统方式）
            if self.use_missile_pool and self.missile_pool_manager:
                # 使用导弹池（性能优化）
                missile_configs = self.missile_pool_manager.get_missiles_for_collection(
                    collection_time, missiles_to_create
                )

                for missile_config in missile_configs:
                    self.all_missiles[missile_config["missile_id"]] = missile_config
                    logger.info(f"   ✅ 从池获取导弹: {missile_config['missile_id']}")
                    logger.info(f"      发射时间: {missile_config['launch_time']}")

                created_count = len(missile_configs)
            else:
                # 传统方式创建导弹
                created_count = 0
                for i in range(missiles_to_create):
                    missile_id = f"RollingThreat_{self.current_collection:03d}_{i+1:02d}_{random.randint(1000, 9999)}"

                    # 生成导弹配置（发射时间基于采集时间）
                    missile_config = self._generate_missile_config(missile_id, collection_time)

                    # 创建导弹
                    success = await self._create_missile(missile_id, missile_config)

                    if success:
                        self.all_missiles[missile_id] = missile_config
                        created_count += 1
                        logger.info(f"   ✅ 导弹创建成功: {missile_id}")
                        logger.info(f"      发射时间: {missile_config['launch_time']}")
                    else:
                        logger.error(f"   ❌ 导弹创建失败: {missile_id}")

            logger.info(f"   📊 导弹管理完成: 成功创建 {created_count}/{missiles_to_create} 个导弹")

        except Exception as e:
            logger.error(f"❌ 导弹管理失败: {e}")

    async def _release_current_missiles(self):
        """释放当前采集使用的导弹回池中"""
        try:
            if self.use_missile_pool and self.missile_pool_manager:
                # 使用导弹池：释放活跃导弹
                active_missile_ids = list(self.all_missiles.keys())
                if active_missile_ids:
                    self.missile_pool_manager.release_missiles(active_missile_ids)
                    logger.info(f"🔄 释放 {len(active_missile_ids)} 个导弹回池中")

                    # 清空当前导弹列表，为下次采集做准备
                    self.all_missiles.clear()

        except Exception as e:
            logger.error(f"❌ 释放导弹失败: {e}")

    async def _clear_existing_missiles(self):
        """清理现有导弹"""
        removed_count = 0  # 在函数开始就初始化

        try:
            logger.info("🧹 清理现有导弹...")

            if self.use_missile_pool and self.missile_pool_manager:
                # 使用导弹池：释放活跃导弹
                active_missile_ids = list(self.all_missiles.keys())
                if active_missile_ids:
                    self.missile_pool_manager.release_missiles(active_missile_ids)
                    logger.info(f"   ✅ 释放 {len(active_missile_ids)} 个导弹回池中")
                    removed_count = len(active_missile_ids)  # 记录释放的导弹数
            else:
                # 传统方式：删除STK对象
                # 获取STK场景中的所有导弹对象
                scenario = self.stk_manager.scenario
                if not scenario:
                    logger.warning("   ⚠️ STK场景不可用，跳过清理")
                    return

                missiles_to_remove = []
                children = scenario.Children

                # 收集所有导弹对象
                for i in range(children.Count):
                    child = children.Item(i)
                    if child.ClassName == "Missile":
                        missiles_to_remove.append(child.InstanceName)

                # 删除导弹对象
                for missile_name in missiles_to_remove:
                    try:
                        # 方法1：尝试通过名称删除
                        try:
                            missile_obj = scenario.Children.Item(missile_name)
                            missile_obj.Unload()
                            removed_count += 1
                            logger.info(f"   🗑️ 删除导弹: {missile_name}")
                        except:
                            # 方法2：尝试通过Unload方法删除
                            scenario.Children.Unload(missile_name)
                            removed_count += 1
                            logger.info(f"   🗑️ 删除导弹: {missile_name}")
                    except Exception as e:
                        logger.warning(f"   ⚠️ 删除导弹失败 {missile_name}: {e}")

            # 清理内部记录
            self.all_missiles.clear()
            self.missile_manager.missile_targets.clear()

            logger.info(f"   📊 清理完成: 删除 {removed_count} 个导弹对象")

        except Exception as e:
            logger.error(f"❌ 清理导弹失败: {e}")
    
    def _get_midcourse_missiles(self, current_time: datetime) -> List[str]:
        """获取当前时刻正在中段飞行的导弹"""
        try:
            midcourse_missiles = []

            logger.info(f"🔍 检查中段飞行导弹，当前时间: {current_time}")
            logger.info(f"   总导弹数: {len(self.all_missiles)}")

            for missile_id, missile_config in self.all_missiles.items():
                logger.info(f"   检查导弹: {missile_id}")
                logger.info(f"     发射时间: {missile_config.get('launch_time')}")
                logger.info(f"     飞行时长: {missile_config.get('flight_duration')}秒")

                if self._is_missile_in_midcourse(missile_id, missile_config, current_time):
                    midcourse_missiles.append(missile_id)
                    logger.info(f"     ✅ 在中段飞行")
                else:
                    logger.info(f"     ❌ 不在中段飞行")

            logger.info(f"🎯 中段飞行导弹: {midcourse_missiles}")
            return midcourse_missiles

        except Exception as e:
            logger.error(f"❌ 获取中段飞行导弹失败: {e}")
            return []

    def _find_next_midcourse_time(self, current_time: datetime) -> Optional[datetime]:
        """找到下一个有导弹进入中段飞行的时间"""
        try:
            earliest_midcourse_time = None

            for missile_id, missile_config in self.all_missiles.items():
                launch_time = missile_config.get("launch_time")
                if not isinstance(launch_time, datetime):
                    continue

                # 计算中段飞行开始时间
                flight_duration = missile_config.get("flight_duration", 1800)
                midcourse_start_offset = flight_duration * 0.1  # 中段开始：飞行时间的10%
                midcourse_start = launch_time + timedelta(seconds=midcourse_start_offset)

                # 如果中段飞行开始时间在当前时间之后，考虑这个时间
                if midcourse_start > current_time:
                    if earliest_midcourse_time is None or midcourse_start < earliest_midcourse_time:
                        earliest_midcourse_time = midcourse_start

            return earliest_midcourse_time

        except Exception as e:
            logger.error(f"❌ 查找下一个中段飞行时间失败: {e}")
            return None
    
    def _is_missile_in_midcourse(self, missile_id: str, missile_config: Dict, current_time: datetime) -> bool:
        """判断导弹是否在中段飞行"""
        try:
            launch_time = missile_config.get("launch_time")
            if not isinstance(launch_time, datetime):
                return False

            # 优先使用基于轨迹高度的飞行阶段分析
            flight_phases_analysis = self.missile_manager.get_missile_flight_phases_by_altitude(missile_id)
            if flight_phases_analysis:
                logger.info(f"       ✅ 使用基于轨迹高度的飞行阶段分析")
                flight_phases = flight_phases_analysis["flight_phases"]
                midcourse_start = flight_phases["midcourse"]["start"]
                midcourse_end = flight_phases["midcourse"]["end"]

                logger.info(f"       轨迹高度分析结果:")
                logger.info(f"         最大高度: {flight_phases_analysis['max_altitude']:.1f}km")
                logger.info(f"         中段时间: {midcourse_start} - {midcourse_end}")
            else:
                # 回退到导弹真实时间范围
                logger.warning(f"       ⚠️ 无法进行轨迹高度分析，回退到时间范围分析")
                missile_time_range = self.missile_manager.get_missile_actual_time_range(missile_id)
                if missile_time_range:
                    actual_launch_time, actual_impact_time = missile_time_range
                    total_flight_seconds = (actual_impact_time - actual_launch_time).total_seconds()

                    # 使用真实时间计算中段飞行时间
                    midcourse_start_offset = total_flight_seconds * 0.1  # 中段开始：飞行时间的10%
                    midcourse_end_offset = total_flight_seconds * 0.1    # 末段时间：飞行时间的10%

                    midcourse_start = actual_launch_time + timedelta(seconds=midcourse_start_offset)
                    midcourse_end = actual_impact_time - timedelta(seconds=midcourse_end_offset)

                    logger.info(f"       使用导弹真实时间范围: {actual_launch_time} - {actual_impact_time}")
                else:
                    # 最后回退到估算时间
                    logger.warning(f"       ⚠️ 无法获取导弹 {missile_id} 真实时间，使用估算时间")
                    flight_duration = missile_config.get("flight_duration", 1800)  # 默认30分钟
                    midcourse_start_offset = flight_duration * 0.1  # 中段开始：飞行时间的10%
                    midcourse_end_offset = flight_duration * 0.9    # 中段结束：飞行时间的90%

                    midcourse_start = launch_time + timedelta(seconds=midcourse_start_offset)
                    midcourse_end = launch_time + timedelta(seconds=midcourse_end_offset)

            # 判断导弹是否有中段飞行阶段（基于轨迹分析，而不是当前时间）
            # 如果导弹有中段飞行时间段，说明它达到了中段高度阈值
            has_midcourse_phase = midcourse_start is not None and midcourse_end is not None

            if has_midcourse_phase:
                # 进一步检查中段时间段的合理性（至少5分钟）
                midcourse_duration = (midcourse_end - midcourse_start).total_seconds()
                has_valid_midcourse = midcourse_duration >= 300  # 至少5分钟
            else:
                has_valid_midcourse = False

            logger.info(f"       中段飞行时间: {midcourse_start} - {midcourse_end}")
            logger.info(f"       中段飞行时长: {midcourse_duration if has_midcourse_phase else 0:.0f}秒")
            logger.info(f"       是否有中段飞行: {has_valid_midcourse}")

            return has_valid_midcourse

        except Exception as e:
            logger.error(f"❌ 判断导弹中段飞行状态失败 {missile_id}: {e}")
            return False

    async def _execute_collection(self, collection_time: datetime, midcourse_missiles: List[str]) -> Optional[Dict[str, Any]]:
        """执行数据采集 - 仅保存到统一目录"""
        try:
            logger.info(f"📊 执行第 {self.current_collection} 次数据采集...")

            # 不创建专用文件夹，只保存到统一目录
            collection_folder = None

            # 临时设置导弹管理器的目标列表为当前中段飞行的导弹
            original_targets = self.missile_manager.missile_targets.copy()

            # 使用所有激活的导弹进行元任务生成
            active_targets = self.all_missiles.copy()
            logger.info(f"   🎯 使用所有激活导弹进行元任务生成: {len(active_targets)} 个")

            # 记录导弹详细信息
            for missile_id, missile_config in active_targets.items():
                logger.info(f"     导弹: {missile_id}")
                logger.info(f"       发射时间: {missile_config.get('launch_time')}")
                logger.info(f"       发射位置: {missile_config.get('launch_position')}")
                logger.info(f"       目标位置: {missile_config.get('target_position')}")

            self.missile_manager.missile_targets = active_targets

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
                    "collection_folder": "unified_collections_only"
                }

                # 只保存到统一目录
                await self._save_collection_data(collection_result, None)

                # 生成甘特图（如果启用）
                await self._generate_collection_visualizations(collection_result, None)

                logger.info(f"✅ 第 {self.current_collection} 次数据采集成功，数据仅保存到统一目录")
                return collection_result
            else:
                logger.error(f"❌ 第 {self.current_collection} 次数据采集失败")
                return None

        except Exception as e:
            logger.error(f"❌ 执行数据采集失败: {e}")
            return None

    def _generate_missile_config(self, missile_id: str, collection_time: datetime) -> Dict[str, Any]:
        """生成导弹配置"""
        try:
            # 生成随机发射和目标位置
            launch_position = self._generate_random_launch_position()
            target_position = self._generate_random_target_position()

            # 计算发射时间
            if self.launch_at_collection_time:
                # 发射时间基于采集时间，确保在场景时间范围内
                min_offset, max_offset = self.launch_time_offset_range
                offset_seconds = random.randint(min_offset, max_offset)

                # 确保发射时间不早于场景开始时间
                scenario_start = self.time_manager.start_time
                earliest_launch = max(collection_time + timedelta(seconds=offset_seconds),
                                     scenario_start + timedelta(minutes=1))  # 场景开始后1分钟

                launch_time = earliest_launch
                actual_offset = (launch_time - collection_time).total_seconds()

                logger.debug(f"   🎯 导弹 {missile_id} 发射时间: {launch_time} (实际偏移: {actual_offset:.0f}秒)")
            else:
                # 使用传入的时间，但确保在场景范围内
                scenario_start = self.time_manager.start_time
                launch_time = max(collection_time, scenario_start + timedelta(minutes=1))

            # 生成飞行时间
            min_duration, max_duration = self.flight_duration_range
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
                "collection_time": collection_time,
                "creation_time": collection_time.isoformat()  # 使用仿真时间而非系统时间
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
                "launch_time": missile_config["launch_time"],
                "flight_duration": missile_config["flight_duration"]
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
            # 使用配置的默认间隔
            default_interval = sum(self.interval_range) // 2  # 使用间隔范围的中值
            return current_time + timedelta(seconds=default_interval)

    def _get_scenario_start_time(self) -> datetime:
        """获取场景开始时间（从配置文件）"""
        try:
            # 从配置管理器获取时间管理器
            from src.utils.time_manager import get_time_manager
            time_manager = get_time_manager()

            # 使用配置文件中的开始时间
            scenario_start = time_manager.start_time

            logger.info(f"📅 从配置文件获取场景开始时间: {scenario_start}")
            return scenario_start

        except Exception as e:
            logger.error(f"❌ 获取场景开始时间失败: {e}")
            # 备用方案：尝试从STK获取
            try:
                scenario_start_str = self.stk_manager.scenario.StartTime
                scenario_start = datetime.strptime(scenario_start_str.split('.')[0], "%d %b %Y %H:%M:%S")
                logger.warning(f"⚠️ 使用STK场景时间作为备用: {scenario_start}")
                return scenario_start
            except:
                logger.error(f"❌ STK场景时间获取也失败，使用配置默认时间")
                # 使用配置文件中的默认开始时间
                return datetime.strptime("2025/08/06 00:00:00", "%Y/%m/%d %H:%M:%S")

    def _is_scenario_time_exceeded(self, current_time: datetime) -> bool:
        """检查是否超过最大场景时间"""
        try:
            if not self.scenario_start_time:
                return False

            # 检查1：是否超过配置的最大场景持续时间
            elapsed_seconds = (current_time - self.scenario_start_time).total_seconds()
            duration_exceeded = elapsed_seconds > self.max_scenario_duration

            # 检查2：是否超过仿真结束时间
            from src.utils.time_manager import get_time_manager
            time_manager = get_time_manager()
            end_time_exceeded = current_time > time_manager.end_time

            if duration_exceeded:
                logger.warning(f"⚠️ 超过最大场景持续时间: {elapsed_seconds:.0f}秒 > {self.max_scenario_duration}秒")

            if end_time_exceeded:
                logger.warning(f"⚠️ 超过仿真结束时间: {current_time} > {time_manager.end_time}")

            return duration_exceeded or end_time_exceeded

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

            # 使用统一的输出目录
            if self.output_base_dir:
                base_path = Path(self.output_base_dir)
            else:
                # 从配置获取滚动采集输出目录
                output_config = self.config_manager.get_output_config()
                rolling_config = output_config.get("rolling_collections", {})
                base_path = Path(rolling_config.get("base_directory", "output/rolling_collections"))

            # 创建文件夹名称：collection_N
            output_config = self.config_manager.get_output_config()
            file_naming = output_config.get("file_naming", {})
            collection_prefix = file_naming.get("collection_prefix", "collection_")
            folder_name = f"{collection_prefix}{self.current_collection:03d}"
            collection_folder = base_path / "collections" / folder_name

            # 创建文件夹结构
            collection_folder.mkdir(parents=True, exist_ok=True)
            (collection_folder / "data").mkdir(exist_ok=True)

            # 只有启用甘特图时才创建charts目录
            if self.enable_gantt:
                (collection_folder / "charts").mkdir(exist_ok=True)

            (collection_folder / "logs").mkdir(exist_ok=True)

            logger.info(f"📁 创建采集文件夹: {collection_folder}")
            logger.info(f"📊 甘特图生成: {'启用' if self.enable_gantt else '禁用'}")

            return collection_folder

        except Exception as e:
            logger.error(f"❌ 创建采集文件夹失败: {e}")
            # 从配置获取回退路径
            output_config = self.config_manager.get_output_config()
            rolling_config = output_config.get("rolling_collections", {})
            fallback_path = rolling_config.get("default_fallback", "output/data")
            return fallback_path

    async def _save_collection_data(self, collection_result: Dict[str, Any], collection_folder: str):
        """保存本次采集的数据 - 仅保存到统一目录"""
        try:
            logger.info(f"💾 仅保存数据到统一目录，跳过专用文件夹保存")

            # 生成冲突消解数据
            logger.info(f"🎯 生成冲突消解数据...")
            conflict_resolution_data = self.conflict_processor.generate_conflict_resolution_data(collection_result)

            # 初始化统一会话（如果尚未初始化）
            if not self.unified_session_initialized:
                from datetime import datetime
                # 使用外部设置的会话名称，如果没有则使用默认名称
                if self.session_name:
                    session_name = self.session_name
                else:
                    session_name = f"conflict_resolution_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.unified_data_manager.initialize_session(session_name)
                self.unified_session_initialized = True
                logger.info(f"📁 统一数据会话已初始化")

            # 保存到统一目录（这是唯一的保存位置）
            collection_index = collection_result.get("rolling_collection_info", {}).get("collection_index", 0)
            saved_files = self.unified_data_manager.save_collection_data(
                collection_index, collection_result, conflict_resolution_data
            )

            if saved_files:
                logger.info(f"💾 数据已保存到统一目录:")
                for file_type, file_path in saved_files.items():
                    import os
                    logger.info(f"   {file_type}: {os.path.basename(file_path)}")

            logger.info(f"💾 采集数据仅保存到统一目录")

        except Exception as e:
            logger.error(f"❌ 保存采集数据失败: {e}")
            import traceback
            traceback.print_exc()

    async def _generate_collection_visualizations(self, collection_result: Dict[str, Any], collection_folder: str):
        """生成本次采集的可视化数据"""
        try:
            # 检查是否启用甘特图生成
            if not self.enable_gantt:
                logger.info(f"📊 第 {self.current_collection} 次采集：甘特图生成已禁用，跳过图表生成")
                return

            logger.info(f"📊 第 {self.current_collection} 次采集：开始生成甘特图...")

            # 生成甘特图
            try:
                # 直接调用甘特图生成器，而不是使用子进程
                from aerospace_meta_task_gantt import AerospaceMetaTaskGantt
                from pathlib import Path

                # 处理collection_folder为None的情况（统一目录模式）
                if collection_folder is None:
                    # 使用统一数据管理器获取最新的数据文件
                    if not self.unified_session_initialized:
                        logger.warning("⚠️ 统一数据会话未初始化，无法生成甘特图")
                        return

                    # 获取当前采集的数据文件路径
                    collection_index = collection_result.get("rolling_collection_info", {}).get("collection_index", 1)
                    unified_data_dir = Path(self.unified_data_manager.session_dir) / "json_data"
                    actual_data_file = unified_data_dir / f"collection_{collection_index:03d}_original.json"

                    # 甘特图输出到统一目录的charts文件夹
                    charts_folder = Path(self.unified_data_manager.session_dir) / "charts"
                    charts_folder.mkdir(parents=True, exist_ok=True)

                    logger.info(f"📊 使用统一目录模式生成甘特图")
                    logger.info(f"   数据文件: {actual_data_file}")
                    logger.info(f"   输出目录: {charts_folder}")
                else:
                    # 传统模式：使用collection_folder
                    collection_path = Path(collection_folder)
                    actual_data_file = collection_path / "data" / "meta_task_data.json"
                    charts_folder = collection_path / "charts"
                    charts_folder.mkdir(parents=True, exist_ok=True)

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

                # 定义输出路径
                collection_index = collection_result.get("rolling_collection_info", {}).get("collection_index", self.current_collection)
                chart_filename = charts_folder / f"collection_{collection_index:03d}_aerospace_meta_task_gantt.png"

                # 生成甘特图
                result = gantt.create_professional_gantt_chart(
                    meta_df, visible_df, output_path=str(chart_filename)
                )

                # 处理返回结果
                if len(result) == 4:
                    fig, (ax1, ax2), saved_path, save_success = result
                    if save_success:
                        logger.info(f"📈 甘特图已保存: {saved_path}")

                        # 如果使用统一目录模式，甘特图已经直接保存到统一目录
                        if collection_folder is None:
                            logger.info(f"📈 甘特图已保存到统一目录: {Path(saved_path).name}")
                        else:
                            # 传统模式：保存甘特图到统一目录
                            if self.unified_session_initialized:
                                collection_index = collection_result.get("rolling_collection_info", {}).get("collection_index", 0)
                                unified_chart_path = self.unified_data_manager.save_gantt_chart(
                                    collection_index, saved_path, "aerospace_meta_task_gantt"
                                )
                                if unified_chart_path:
                                    logger.info(f"📈 甘特图已复制到统一目录: {Path(unified_chart_path).name}")
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



            # 生成采集信息文本文件（仅在传统模式下）
            if collection_folder is not None:
                info_file = Path(collection_folder) / "collection_info.txt"
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
            else:
                logger.info(f"📄 统一目录模式：采集信息已包含在会话汇总中")

        except Exception as e:
            logger.error(f"❌ 生成可视化数据失败: {e}")

    async def finalize_session(self):
        """结束会话并生成最终汇总"""
        try:
            if self.unified_session_initialized:
                logger.info(f"📋 生成会话汇总...")
                summary_file = self.unified_data_manager.save_session_summary()
                if summary_file:
                    logger.info(f"📋 会话汇总已保存: {summary_file}")

                    # 显示统一目录信息
                    session_summary = self.unified_data_manager.generate_session_summary()
                    session_info = session_summary.get("session_info", {})
                    statistics = session_summary.get("statistics", {})

                    logger.info(f"🎉 统一数据采集会话完成:")
                    logger.info(f"   会话目录: {session_info.get('session_dir', '')}")
                    logger.info(f"   总采集次数: {session_info.get('total_collections', 0)}")
                    logger.info(f"   总元任务数: {statistics.get('total_meta_tasks', 0)}")
                    logger.info(f"   总可见任务数: {statistics.get('total_visible_tasks', 0)}")
                    logger.info(f"   总导弹数: {statistics.get('total_missiles', 0)}")
                else:
                    logger.warning(f"⚠️ 会话汇总保存失败")
            else:
                logger.info(f"📋 未使用统一数据管理，跳过会话汇总")

        except Exception as e:
            logger.error(f"❌ 结束会话失败: {e}")
            import traceback
            traceback.print_exc()
