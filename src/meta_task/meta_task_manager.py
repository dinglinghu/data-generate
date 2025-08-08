"""
元任务管理器
负责元任务定义、元子任务生成、可见元子任务计算等功能
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from ..utils.config_manager import get_config_manager
from ..utils.time_manager import get_time_manager

logger = logging.getLogger(__name__)

class MetaTaskManager:
    """元任务管理器"""
    
    def __init__(self, missile_manager, time_manager=None, config_manager=None):
        """
        初始化元任务管理器
        
        Args:
            missile_manager: 导弹管理器
            time_manager: 时间管理器
            config_manager: 配置管理器
        """
        self.missile_manager = missile_manager
        self.time_manager = time_manager or get_time_manager()
        self.config_manager = config_manager or get_config_manager()
        
        # 获取元任务配置
        self.meta_task_config = self.config_manager.config.get("meta_task_management", {})
        self.atomic_task_interval = self.meta_task_config.get("atomic_task_interval", 300)  # 5分钟
        
        # 存储元任务数据
        self.meta_tasks = {}  # 存储所有导弹的元任务
        self.atomic_task_sets = {}  # 存储元子任务集

        # 存储导弹轨迹数据缓存
        self.missile_trajectory_cache = {}  # 缓存导弹轨迹数据，避免重复获取

        # 批量处理缓存
        self._batch_altitude_analysis_cache = {}  # 批量高度分析缓存

        logger.info("🎯 元任务管理器初始化完成，批量处理已准备")
        logger.info(f"   元子任务时间间隔: {self.atomic_task_interval}秒")

    def batch_analyze_missile_altitudes(self, missile_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量分析多个导弹的高度数据，优化性能

        Args:
            missile_ids: 导弹ID列表

        Returns:
            字典: {missile_id: altitude_analysis}
        """
        logger.info(f"🚀 批量分析 {len(missile_ids)} 个导弹的高度数据...")

        # 检查是否有导弹管理器的批量方法
        if hasattr(self.missile_manager, 'batch_get_missile_flight_phases_by_altitude'):
            return self.missile_manager.batch_get_missile_flight_phases_by_altitude(missile_ids)
        else:
            # 回退到逐个处理
            results = {}
            for missile_id in missile_ids:
                results[missile_id] = self.missile_manager.get_missile_flight_phases_by_altitude(missile_id)
            return results

    def batch_get_missile_trajectories(self, missile_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量获取多个导弹的轨迹数据，优化性能

        Args:
            missile_ids: 导弹ID列表

        Returns:
            字典: {missile_id: trajectory_data}
        """
        logger.info(f"🚀 批量获取 {len(missile_ids)} 个导弹的轨迹数据...")

        # 检查是否有导弹管理器的批量方法
        if hasattr(self.missile_manager, 'batch_get_missile_trajectory_info'):
            return self.missile_manager.batch_get_missile_trajectory_info(missile_ids)
        else:
            # 回退到逐个处理
            results = {}
            for missile_id in missile_ids:
                results[missile_id] = self.get_missile_trajectory_data(missile_id)
            return results

    def generate_meta_tasks_for_all_missiles(self, current_planning_time: datetime) -> Dict[str, Any]:
        """
        为所有导弹目标生成独立的元任务

        Args:
            current_planning_time: 当前规划时刻

        Returns:
            包含所有导弹元任务的字典
        """
        try:
            logger.info(f"🎯 开始为所有导弹生成独立元任务，当前规划时刻: {current_planning_time}")

            # 1. 为每个导弹生成独立的元任务
            all_meta_tasks = self._generate_individual_meta_tasks_for_missiles(current_planning_time)

            if not all_meta_tasks:
                logger.error("❌ 无法生成导弹元任务")
                return {}

            # 2. 确定全局规划周期（用于统计）
            global_planning_cycle = self._determine_global_planning_cycle(all_meta_tasks)

            # 3. 存储元任务数据
            self.meta_tasks = all_meta_tasks
            self.atomic_task_sets = {
                "individual_sets": {missile_id: meta_task["atomic_tasks"]
                                  for missile_id, meta_task in all_meta_tasks.items()},
                "global_planning_cycle": global_planning_cycle,
                "generation_time": current_planning_time.isoformat()
            }

            # 4. 统计信息
            total_atomic_tasks = sum(len(meta_task["atomic_tasks"]) for meta_task in all_meta_tasks.values())
            total_real_tasks = sum(meta_task.get("real_task_count", 0) for meta_task in all_meta_tasks.values())
            total_virtual_tasks = sum(meta_task.get("virtual_task_count", 0) for meta_task in all_meta_tasks.values())

            logger.info(f"✅ 独立元任务生成完成，覆盖 {len(all_meta_tasks)} 个导弹目标")
            logger.info(f"📊 全局规划周期: {global_planning_cycle['start_time']} -> {global_planning_cycle['end_time']}")
            logger.info(f"   规划时长: {global_planning_cycle['duration_seconds']}秒 ({global_planning_cycle['duration_seconds']/3600:.1f}小时)")
            logger.info(f"   总任务: {total_atomic_tasks}, 真实任务: {total_real_tasks}, 虚拟任务: {total_virtual_tasks}")

            return {
                "meta_tasks": all_meta_tasks,
                "planning_cycle_info": global_planning_cycle,
                "generation_summary": {
                    "total_missiles": len(all_meta_tasks),
                    "total_atomic_tasks": total_atomic_tasks,
                    "total_real_tasks": total_real_tasks,
                    "total_virtual_tasks": total_virtual_tasks,
                    "planning_duration_hours": global_planning_cycle['duration_seconds'] / 3600,
                    "generation_time": current_planning_time.isoformat()
                }
            }

        except Exception as e:
            logger.error(f"❌ 元任务生成失败: {e}")
            return {}
    
    def _determine_planning_cycle(self, current_planning_time: datetime) -> Optional[Dict[str, Any]]:
        """
        确定所有导弹目标的元任务规划周期
        规划周期为：[所有导弹中段飞行最早时刻：所有导弹中段飞行最晚时刻]

        Args:
            current_planning_time: 当前规划时刻

        Returns:
            规划周期信息字典
        """
        try:
            logger.info("🔍 确定元任务规划周期...")

            # 获取所有导弹的中段飞行时间信息
            all_missiles = self.missile_manager.missile_targets

            if not all_missiles:
                logger.warning("⚠️ 当前没有导弹目标")
                return None

            earliest_midcourse_start = None
            latest_midcourse_end = None
            midcourse_info = []

            for missile_id, missile_info in all_missiles.items():
                try:
                    # 获取导弹的中段飞行时间
                    midcourse_period = self._calculate_missile_midcourse_period(missile_id, missile_info)

                    if midcourse_period:
                        midcourse_info.append({
                            "missile_id": missile_id,
                            "midcourse_start": midcourse_period["start_time"],
                            "midcourse_end": midcourse_period["end_time"],
                            "duration_seconds": midcourse_period["duration_seconds"]
                        })

                        # 更新最早的中段飞行开始时间
                        if earliest_midcourse_start is None or midcourse_period["start_time"] < earliest_midcourse_start:
                            earliest_midcourse_start = midcourse_period["start_time"]

                        # 更新最晚的中段飞行结束时间
                        if latest_midcourse_end is None or midcourse_period["end_time"] > latest_midcourse_end:
                            latest_midcourse_end = midcourse_period["end_time"]

                except Exception as e:
                    logger.warning(f"⚠️ 计算导弹 {missile_id} 中段飞行时间失败: {e}")
                    continue

            if earliest_midcourse_start is None or latest_midcourse_end is None:
                logger.error("❌ 无法确定任何导弹的中段飞行时间")
                return None

            # 应用标准化规划周期配置
            planning_start_time, planning_end_time = self._apply_standardized_planning_cycle(
                earliest_midcourse_start, latest_midcourse_end, current_planning_time)

            # 构建规划周期
            planning_cycle = {
                "start_time": planning_start_time,
                "end_time": planning_end_time,
                "duration_seconds": (planning_end_time - planning_start_time).total_seconds(),
                "midcourse_info": midcourse_info,
                "earliest_missile": min(midcourse_info, key=lambda x: x["midcourse_start"])["missile_id"],
                "latest_missile": max(midcourse_info, key=lambda x: x["midcourse_end"])["missile_id"],
                "original_start": earliest_midcourse_start,
                "original_end": latest_midcourse_end,
                "standardized": True
            }

            logger.info(f"✅ 元任务规划周期确定完成:")
            logger.info(f"   开始时间: {planning_start_time} (最早中段飞行开始)")
            logger.info(f"   结束时间: {latest_midcourse_end} (最晚中段飞行结束)")
            logger.info(f"   持续时间: {planning_cycle['duration_seconds']}秒 ({planning_cycle['duration_seconds']/3600:.1f}小时)")
            logger.info(f"   最早导弹: {planning_cycle['earliest_missile']}")
            logger.info(f"   最晚导弹: {planning_cycle['latest_missile']}")
            logger.info(f"   覆盖导弹数: {len(midcourse_info)}")
            
            return planning_cycle
            
        except Exception as e:
            logger.error(f"❌ 确定规划周期失败: {e}")
            return None

    def _apply_standardized_planning_cycle(self, earliest_start: datetime, latest_end: datetime,
                                         current_time: datetime) -> tuple[datetime, datetime]:
        """
        应用标准化规划周期配置

        Args:
            earliest_start: 最早中段飞行开始时间
            latest_end: 最晚中段飞行结束时间
            current_time: 当前规划时间

        Returns:
            (标准化开始时间, 标准化结束时间)
        """
        try:
            # 从配置获取标准化参数
            config = self.config_manager.config.get("meta_task", {}).get("rolling_collection", {})
            standardized_config = config.get("standardized_planning", {})

            if not standardized_config.get("enable", False):
                # 如果未启用标准化，返回原始时间
                return earliest_start, latest_end

            # 获取标准化参数（从配置文件）
            standardization_config = self.meta_task_config.get("standardization", {})
            standard_duration = standardization_config.get("standard_duration", 2400)  # 40分钟
            min_duration = standardization_config.get("min_duration", 1800)  # 30分钟
            max_duration = standardization_config.get("max_duration", 2700)  # 45分钟
            overlap_duration = standardization_config.get("overlap_duration", 300)  # 5分钟

            # 计算原始持续时间
            original_duration = (latest_end - earliest_start).total_seconds()

            # 确定标准化持续时间
            if original_duration < min_duration:
                target_duration = min_duration
            elif original_duration > max_duration:
                target_duration = max_duration
            else:
                # 使用标准持续时间，但不小于原始持续时间
                target_duration = max(standard_duration, original_duration)

            # 计算标准化的开始和结束时间
            # 策略：以原始时间范围的中心为基准，向两边扩展
            original_center = earliest_start + timedelta(seconds=original_duration / 2)

            standardized_start = original_center - timedelta(seconds=target_duration / 2)
            standardized_end = original_center + timedelta(seconds=target_duration / 2)

            # 确保标准化时间范围包含所有原始中段飞行时间
            if standardized_start > earliest_start:
                # 向前扩展开始时间，并相应调整结束时间
                adjustment = (earliest_start - standardized_start).total_seconds() - overlap_duration
                standardized_start = earliest_start - timedelta(seconds=overlap_duration)
                standardized_end = standardized_start + timedelta(seconds=target_duration)

            if standardized_end < latest_end:
                # 向后扩展结束时间，并相应调整开始时间
                adjustment = (latest_end - standardized_end).total_seconds() + overlap_duration
                standardized_end = latest_end + timedelta(seconds=overlap_duration)
                standardized_start = standardized_end - timedelta(seconds=target_duration)

            logger.info(f"📏 应用标准化规划周期:")
            logger.info(f"   原始持续时间: {original_duration:.0f}秒 ({original_duration/60:.1f}分钟)")
            logger.info(f"   标准化持续时间: {target_duration:.0f}秒 ({target_duration/60:.1f}分钟)")
            logger.info(f"   时间重叠: {overlap_duration:.0f}秒")

            return standardized_start, standardized_end

        except Exception as e:
            logger.error(f"❌ 应用标准化规划周期失败: {e}")
            return earliest_start, latest_end
    
    def _calculate_missile_midcourse_period(self, missile_id: str, missile_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        基于真实轨迹高度数据计算导弹的中段飞行时间段

        Args:
            missile_id: 导弹ID
            missile_info: 导弹信息

        Returns:
            中段飞行时间段信息
        """
        try:
            # 获取导弹发射时间
            launch_time = missile_info.get("launch_time")
            if not isinstance(launch_time, datetime):
                logger.debug(f"导弹 {missile_id} 发射时间无效")
                return None

            # 优先使用基于真实轨迹高度的飞行阶段分析
            logger.info(f"🎯 分析导弹 {missile_id} 的真实轨迹高度数据...")
            flight_phases_analysis = self.missile_manager.get_missile_flight_phases_by_altitude(missile_id)
            if flight_phases_analysis:
                logger.info(f"✅ 使用基于真实轨迹高度的飞行阶段分析")

                # 使用轨迹高度分析的结果
                launch_time = flight_phases_analysis["launch_time"]
                impact_time = flight_phases_analysis["impact_time"]
                total_flight_time = timedelta(seconds=flight_phases_analysis["total_flight_time"])

                # 直接使用分析得到的飞行阶段
                flight_phases = flight_phases_analysis["flight_phases"]
                midcourse_start = flight_phases["midcourse"]["start"]
                midcourse_end = flight_phases["midcourse"]["end"]
                midcourse_duration = timedelta(seconds=flight_phases["midcourse"]["duration_seconds"])

                # 验证中段飞行时间的合理性
                midcourse_info = flight_phases["midcourse"]
                altitude_above_threshold = midcourse_info.get("altitude_above_threshold", False)
                max_altitude = midcourse_info.get("max_altitude", 0)
                min_altitude_threshold = midcourse_info.get("min_altitude_threshold", 100)

                logger.info(f"🎯 基于真实轨迹高度的飞行阶段分析:")
                logger.info(f"   发射时间: {launch_time}")
                logger.info(f"   撞击时间: {impact_time}")
                logger.info(f"   最大飞行高度: {flight_phases_analysis['max_altitude']:.1f}km")
                logger.info(f"   中段高度阈值: {min_altitude_threshold}km")
                logger.info(f"   中段最大高度: {max_altitude:.1f}km")
                logger.info(f"   高度满足阈值: {'是' if altitude_above_threshold else '否'}")
                logger.info(f"   助推段: {flight_phases['boost']['start']} - {flight_phases['boost']['end']} ({flight_phases['boost']['duration_seconds']:.0f}秒)")
                logger.info(f"   中段: {midcourse_start} - {midcourse_end} ({midcourse_duration.total_seconds():.0f}秒)")
                logger.info(f"   末段: {flight_phases['terminal']['start']} - {flight_phases['terminal']['end']} ({flight_phases['terminal']['duration_seconds']:.0f}秒)")

                # 跳过后续的时间计算，直接使用分析结果
                use_altitude_analysis = True
            else:
                # 回退到时间范围分析
                logger.warning(f"⚠️ 无法进行轨迹高度分析，回退到时间范围分析")
                missile_time_range = self.missile_manager.get_missile_actual_time_range(missile_id)
                if missile_time_range:
                    actual_launch_time, actual_impact_time = missile_time_range
                    logger.info(f"✅ 使用导弹真实时间范围: {actual_launch_time} - {actual_impact_time}")
                    # 使用真实的发射和撞击时间
                    launch_time = actual_launch_time
                    impact_time = actual_impact_time
                    total_flight_time = impact_time - launch_time
                else:
                    # 最后回退到估算时间
                    logger.warning(f"⚠️ 无法获取导弹 {missile_id} 真实时间，使用估算时间")
                    flight_time_config = self.config_manager.config.get("missile_management", {}).get("flight_time", {})
                    default_flight_minutes = flight_time_config.get("default_minutes", 30)
                    total_flight_time = timedelta(minutes=default_flight_minutes)
                    impact_time = launch_time + total_flight_time

                use_altitude_analysis = False
            
            # 只有在没有使用高度分析时才进行传统的时间比例计算
            if not use_altitude_analysis:
                # 基于真实飞行时间计算各阶段时间
                flight_phases_config = self.meta_task_config.get("flight_phases", {})
                boost_phase_ratio = flight_phases_config.get("boost_phase_ratio", 0.1)    # 助推段占比10%
                terminal_phase_ratio = flight_phases_config.get("terminal_phase_ratio", 0.1)  # 末段占比10%
                midcourse_ratio = 1.0 - boost_phase_ratio - terminal_phase_ratio  # 中段占比80%

                logger.info(f"📊 飞行阶段配置: 助推段{boost_phase_ratio*100:.1f}%, 中段{midcourse_ratio*100:.1f}%, 末段{terminal_phase_ratio*100:.1f}%")

                # 基于真实飞行时间计算各阶段时间
                total_flight_seconds = total_flight_time.total_seconds()
                boost_duration_seconds = total_flight_seconds * boost_phase_ratio
                terminal_duration_seconds = total_flight_seconds * terminal_phase_ratio

                # 中段开始和结束时间（基于真实时间范围）
                midcourse_start = launch_time + timedelta(seconds=boost_duration_seconds)
                midcourse_end = impact_time - timedelta(seconds=terminal_duration_seconds)
                midcourse_duration = midcourse_end - midcourse_start

                logger.info(f"⏰ 真实时间范围: 发射{launch_time} - 撞击{impact_time}")
                logger.info(f"⏰ 中段时间范围: {midcourse_start} - {midcourse_end}")
                logger.info(f"⏰ 中段持续时间: {midcourse_duration.total_seconds():.1f}秒")
            
            # 构建元任务结果
            if use_altitude_analysis:
                # 使用高度分析的结果
                midcourse_period = {
                    "start_time": midcourse_start,
                    "end_time": midcourse_end,
                    "duration_seconds": midcourse_duration.total_seconds(),
                    "launch_time": launch_time,
                    "impact_time": impact_time,
                    "flight_phases": flight_phases_analysis["flight_phases"],
                    "altitude_analysis": flight_phases_analysis["altitude_analysis"],
                    "max_altitude": flight_phases_analysis["max_altitude"],
                    "time_source": "trajectory_altitude_analysis"  # 标记时间来源
                }
                logger.info(f"✅ 使用轨迹高度分析结果构建元任务")
            else:
                # 使用传统时间比例分析的结果
                midcourse_period = {
                    "start_time": midcourse_start,
                    "end_time": midcourse_end,
                    "duration_seconds": midcourse_duration.total_seconds(),
                    "launch_time": launch_time,
                    "impact_time": impact_time,
                    "flight_phases": {
                        "boost": {"start": launch_time, "end": midcourse_start},
                        "midcourse": {"start": midcourse_start, "end": midcourse_end},
                        "terminal": {"start": midcourse_end, "end": impact_time}
                    },
                    "time_source": "missile_actual_time"  # 标记时间来源
                }
                logger.info(f"✅ 使用时间范围分析结果构建元任务")
            
            # 输出最终的时间范围分析结果
            logger.info(f"🚀 导弹 {missile_id} 最终时间范围分析:")
            logger.info(f"   发射时间: {launch_time}")
            logger.info(f"   撞击时间: {impact_time}")
            logger.info(f"   总飞行时间: {total_flight_time.total_seconds():.1f}秒")
            logger.info(f"   中段飞行: {midcourse_start} -> {midcourse_end} ({midcourse_duration.total_seconds():.1f}秒)")
            logger.info(f"   元任务时间窗口: {midcourse_start} -> {midcourse_end}")
            logger.info(f"   时间来源: {midcourse_period.get('time_source', 'unknown')}")

            if use_altitude_analysis:
                logger.info(f"   最大高度: {flight_phases_analysis['max_altitude']:.1f}m")
                logger.info(f"   高度范围: {flight_phases_analysis['altitude_analysis']['altitude_range']:.1f}m")
            
            return midcourse_period
            
        except Exception as e:
            logger.error(f"❌ 计算导弹 {missile_id} 中段飞行时间失败: {e}")
            return None
    
    def _generate_atomic_task_set(self, planning_cycle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据配置文件的元子任务时间间隔，生成元子任务集
        
        Args:
            planning_cycle: 规划周期信息
            
        Returns:
            元子任务集列表
        """
        try:
            logger.info("📋 生成元子任务集...")
            
            start_time = planning_cycle["start_time"]
            end_time = planning_cycle["end_time"]
            interval_seconds = self.atomic_task_interval
            
            atomic_tasks = []
            task_index = 1
            current_time = start_time
            
            while current_time < end_time:
                # 计算任务结束时间
                task_end_time = current_time + timedelta(seconds=interval_seconds)
                
                # 确保不超过规划周期结束时间
                if task_end_time > end_time:
                    task_end_time = end_time
                
                # 创建元子任务
                atomic_task = {
                    "task_id": f"atomic_task_{task_index:03d}",
                    "task_index": task_index,
                    "start_time": current_time,
                    "end_time": task_end_time,
                    "duration_seconds": (task_end_time - current_time).total_seconds(),
                    "start_time_iso": current_time.isoformat(),
                    "end_time_iso": task_end_time.isoformat(),
                    "task_type": "atomic_meta_task"
                }
                
                atomic_tasks.append(atomic_task)
                
                # 移动到下一个时间间隔
                current_time = task_end_time
                task_index += 1
                
                # 防止无限循环
                if task_index > 1000:
                    logger.warning("⚠️ 元子任务数量超过1000，停止生成")
                    break
            
            logger.info(f"✅ 元子任务集生成完成: {len(atomic_tasks)}个任务")
            logger.info(f"   时间间隔: {interval_seconds}秒")
            logger.info(f"   总时长: {(end_time - start_time).total_seconds()}秒")
            
            return atomic_tasks
            
        except Exception as e:
            logger.error(f"❌ 生成元子任务集失败: {e}")
            return []
    
    def _generate_individual_meta_tasks_for_missiles(self, current_planning_time: datetime) -> Dict[str, Any]:
        """
        为每个导弹生成独立的元任务（真实任务+虚拟任务）

        Args:
            current_planning_time: 当前规划时刻

        Returns:
            所有导弹的独立元任务字典
        """
        try:
            logger.info("🎯 为每个导弹生成独立元任务...")

            # 1. 确定全局规划周期
            global_planning_cycle = self._determine_planning_cycle(current_planning_time)
            if not global_planning_cycle:
                logger.error("❌ 无法确定全局规划周期")
                return {}

            logger.info(f"📊 全局规划周期: {global_planning_cycle['start_time']} -> {global_planning_cycle['end_time']}")

            # 2. 生成全局时间网格
            global_time_grid = self._generate_time_grid(global_planning_cycle)

            # 3. 为每个导弹生成独立的元任务
            all_meta_tasks = {}
            all_missiles = self.missile_manager.missile_targets

            for missile_id in all_missiles.keys():
                logger.info(f"🚀 生成导弹 {missile_id} 的独立元任务...")

                # 获取导弹的中段飞行时间
                midcourse_info = self._get_missile_midcourse_time(missile_id)
                if not midcourse_info:
                    logger.warning(f"⚠️ 无法获取导弹 {missile_id} 的中段飞行时间，跳过")
                    continue

                # 生成该导弹的真实任务和虚拟任务
                missile_tasks = self._generate_missile_specific_tasks(
                    missile_id, global_time_grid, midcourse_info, global_planning_cycle
                )

                # 创建导弹元任务结构
                missile_meta_task = {
                    "missile_id": missile_id,
                    "planning_cycle": global_planning_cycle,
                    "midcourse_info": midcourse_info,
                    "atomic_tasks": missile_tasks["all_tasks"],
                    "real_tasks": missile_tasks["real_tasks"],
                    "virtual_tasks": missile_tasks["virtual_tasks"],
                    "total_tasks": len(missile_tasks["all_tasks"]),
                    "real_task_count": len(missile_tasks["real_tasks"]),
                    "virtual_task_count": len(missile_tasks["virtual_tasks"]),
                    "assignment_time": datetime.now().isoformat(),
                    "task_status": "assigned"
                }

                all_meta_tasks[missile_id] = missile_meta_task

                logger.info(f"✅ 导弹 {missile_id}: {len(missile_tasks['real_tasks'])} 真实任务, {len(missile_tasks['virtual_tasks'])} 虚拟任务")

            logger.info(f"✅ 独立元任务生成完成，覆盖 {len(all_meta_tasks)} 个导弹")

            return all_meta_tasks

        except Exception as e:
            logger.error(f"❌ 独立元任务生成失败: {e}")
            return {}
    
    def get_meta_tasks_for_missile(self, missile_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定导弹的元任务
        
        Args:
            missile_id: 导弹ID
            
        Returns:
            导弹的元任务信息
        """
        return self.meta_tasks.get(missile_id)
    
    def get_all_meta_tasks(self) -> Dict[str, Any]:
        """
        获取所有导弹的元任务

        Returns:
            所有元任务字典
        """
        return self.meta_tasks

    def _generate_time_grid(self, planning_cycle: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        生成全局时间网格

        Args:
            planning_cycle: 规划周期信息

        Returns:
            时间网格列表
        """
        try:
            start_time = planning_cycle["start_time"]
            end_time = planning_cycle["end_time"]
            interval_seconds = self.atomic_task_interval

            time_grid = []
            task_index = 1
            current_time = start_time

            while current_time < end_time:
                # 计算任务结束时间
                task_end_time = current_time + timedelta(seconds=interval_seconds)

                # 确保不超过规划周期结束时间
                if task_end_time > end_time:
                    task_end_time = end_time

                # 创建时间槽
                time_slot = {
                    "task_id": f"atomic_task_{task_index:03d}",
                    "task_index": task_index,
                    "start_time": current_time,
                    "end_time": task_end_time,
                    "duration_seconds": (task_end_time - current_time).total_seconds(),
                    "start_time_iso": current_time.isoformat(),
                    "end_time_iso": task_end_time.isoformat()
                }

                time_grid.append(time_slot)

                # 移动到下一个时间间隔
                current_time = task_end_time
                task_index += 1

                # 防止无限循环
                if task_index > 1000:
                    logger.warning("⚠️ 时间网格数量超过1000，停止生成")
                    break

            logger.debug(f"✅ 时间网格生成完成: {len(time_grid)}个时间槽")

            return time_grid

        except Exception as e:
            logger.error(f"❌ 生成时间网格失败: {e}")
            return []

    def _get_missile_midcourse_time(self, missile_id: str) -> Optional[Dict[str, Any]]:
        """
        获取导弹的中段飞行时间

        Args:
            missile_id: 导弹ID

        Returns:
            中段飞行时间信息
        """
        try:
            # 从导弹管理器获取导弹信息
            missile_info = self.missile_manager.missile_targets.get(missile_id)
            if not missile_info:
                logger.warning(f"⚠️ 未找到导弹 {missile_id} 的信息")
                return None

            # 使用统一的中段飞行时间计算方法
            midcourse_period = self._calculate_missile_midcourse_period(missile_id, missile_info)

            if not midcourse_period:
                logger.warning(f"⚠️ 无法计算导弹 {missile_id} 的中段飞行时间")
                return None

            return {
                "missile_id": missile_id,
                "midcourse_start": midcourse_period["start_time"],
                "midcourse_end": midcourse_period["end_time"],
                "duration_seconds": midcourse_period["duration_seconds"]
            }

        except Exception as e:
            logger.error(f"❌ 获取导弹 {missile_id} 中段飞行时间失败: {e}")
            return None

    def _get_or_cache_missile_trajectory(self, missile_id: str) -> Optional[Dict[str, Any]]:
        """
        获取或缓存导弹轨迹数据

        Args:
            missile_id: 导弹ID

        Returns:
            导弹轨迹数据
        """
        try:
            # 检查缓存
            if missile_id in self.missile_trajectory_cache:
                logger.debug(f"🎯 使用缓存的轨迹数据: {missile_id}")
                return self.missile_trajectory_cache[missile_id]

            # 获取轨迹数据
            logger.info(f"🎯 获取导弹轨迹数据: {missile_id}")
            trajectory_data = self.missile_manager.get_missile_trajectory_info(missile_id)

            if trajectory_data:
                # 缓存轨迹数据
                self.missile_trajectory_cache[missile_id] = trajectory_data
                logger.info(f"✅ 导弹 {missile_id} 轨迹数据获取并缓存成功")

                # 记录轨迹数据统计
                trajectory_points = trajectory_data.get("trajectory_points", [])
                logger.info(f"   轨迹点数: {len(trajectory_points)}")

                if trajectory_points:
                    logger.info(f"   时间范围: {trajectory_points[0].get('time')} -> {trajectory_points[-1].get('time')}")

                return trajectory_data
            else:
                logger.warning(f"⚠️ 无法获取导弹 {missile_id} 的轨迹数据")
                return None

        except Exception as e:
            logger.error(f"❌ 获取导弹 {missile_id} 轨迹数据失败: {e}")
            return None

    def _find_missile_position_at_time(self, missile_id: str, target_time: datetime) -> Optional[Dict[str, Any]]:
        """
        从已有轨迹数据中查找指定时刻的导弹位置

        Args:
            missile_id: 导弹ID
            target_time: 目标时间

        Returns:
            位置信息字典
        """
        try:
            # 获取轨迹数据
            trajectory_data = self._get_or_cache_missile_trajectory(missile_id)
            if not trajectory_data:
                return None

            trajectory_points = trajectory_data.get("trajectory_points", [])
            if not trajectory_points:
                return None

            # 查找最接近目标时间的轨迹点，支持插值
            closest_point = None
            min_time_diff = float('inf')
            before_point = None
            after_point = None

            # 获取导弹发射时间
            missile_info = self.missile_manager.missile_targets.get(missile_id)
            if not missile_info:
                logger.warning(f"⚠️ 未找到导弹 {missile_id} 的配置信息")
                return None

            launch_time = missile_info.get("launch_time")
            if not launch_time:
                logger.warning(f"⚠️ 未找到导弹 {missile_id} 的发射时间")
                return None

            # 解析所有轨迹点的时间并排序
            parsed_points = []
            for point in trajectory_points:
                point_time = point.get("time")

                # 处理不同的时间格式
                if isinstance(point_time, datetime):
                    # 如果已经是datetime对象，直接使用
                    abs_time = point_time
                elif isinstance(point_time, (int, float)):
                    # 如果是相对秒数，转换为绝对时间
                    abs_time = launch_time + timedelta(seconds=float(point_time))
                elif isinstance(point_time, str):
                    # 如果是字符串，尝试多种解析方式
                    try:
                        # 方法1: ISO格式
                        abs_time = datetime.fromisoformat(point_time.replace('Z', '+00:00'))
                    except:
                        try:
                            # 方法2: STK格式 "26 Jul 2025 00:01:00.000000000"
                            abs_time = datetime.strptime(point_time.split('.')[0], "%d %b %Y %H:%M:%S")
                        except:
                            try:
                                # 方法3: 其他常见格式
                                abs_time = datetime.strptime(point_time, "%Y-%m-%d %H:%M:%S")
                            except:
                                logger.debug(f"   ⚠️ 无法解析时间格式: {point_time}")
                                continue
                else:
                    continue

                # 添加到解析点列表
                parsed_points.append({
                    'abs_time': abs_time,
                    'point': point,
                    'time_diff': abs((abs_time - target_time).total_seconds())
                })

            # 按时间排序
            parsed_points.sort(key=lambda x: x['abs_time'])

            # 查找最接近的点
            for parsed_point in parsed_points:
                if parsed_point['time_diff'] < min_time_diff:
                    min_time_diff = parsed_point['time_diff']
                    closest_point = parsed_point['point']
                    closest_abs_time = parsed_point['abs_time']

            # 尝试找到目标时间前后的点进行插值
            target_timestamp = target_time.timestamp()
            for i, parsed_point in enumerate(parsed_points):
                point_timestamp = parsed_point['abs_time'].timestamp()

                if point_timestamp <= target_timestamp:
                    before_point = parsed_point
                elif point_timestamp > target_timestamp and before_point is not None:
                    after_point = parsed_point
                    break

            # 尝试插值计算更精确的位置
            interpolated_position = None
            if before_point and after_point and min_time_diff > 15.0:  # 如果时间差大于15秒，尝试插值
                try:
                    before_time = before_point['abs_time']
                    after_time = after_point['abs_time']
                    before_pos = before_point['point']
                    after_pos = after_point['point']

                    # 计算插值权重
                    total_duration = (after_time - before_time).total_seconds()
                    if total_duration > 0:
                        weight = (target_time - before_time).total_seconds() / total_duration

                        # 线性插值计算位置
                        interpolated_lat = before_pos.get("lat", 0) + weight * (after_pos.get("lat", 0) - before_pos.get("lat", 0))
                        interpolated_lon = before_pos.get("lon", 0) + weight * (after_pos.get("lon", 0) - before_pos.get("lon", 0))
                        interpolated_alt = before_pos.get("alt", 0) + weight * (after_pos.get("alt", 0) - before_pos.get("alt", 0))

                        interpolated_position = {
                            "latitude": interpolated_lat,
                            "longitude": interpolated_lon,
                            "altitude": interpolated_alt,
                            "altitude_km": interpolated_alt if interpolated_alt else None
                        }

                        logger.debug(f"✅ 使用插值计算导弹 {missile_id} 在 {target_time} 的位置")

                except Exception as interp_error:
                    logger.debug(f"⚠️ 插值计算失败: {interp_error}")

            if closest_point or interpolated_position:
                # 构建位置信息
                position_info = {
                    "missile_id": missile_id,
                    "query_time": target_time.isoformat(),
                    "actual_time": closest_abs_time.isoformat() if 'closest_abs_time' in locals() else closest_point.get("time"),
                    "time_difference_seconds": min_time_diff if not interpolated_position else 0.0,
                    "position": interpolated_position if interpolated_position else {
                        "latitude": closest_point.get("lat"),
                        "longitude": closest_point.get("lon"),
                        "altitude": closest_point.get("alt"),
                        "altitude_km": closest_point.get("alt", 0) if closest_point.get("alt") else None
                    },
                    "data_source": "interpolated_trajectory" if interpolated_position else "cached_trajectory",
                    "trajectory_analysis": trajectory_data.get("trajectory_analysis", {})
                }

                # 检查时间差是否在合理范围内（插值的话直接接受，否则允许最大60秒的时间差）
                # 从配置获取最大时间差阈值
                max_time_diff = self.config_manager.get_task_planning_config().get("altitude_analysis", {}).get("max_time_difference", 600)

                if interpolated_position or min_time_diff <= max_time_diff:
                    method = "插值" if interpolated_position else f"最近点(时间差: {min_time_diff:.1f}秒)"
                    if min_time_diff > 60.0:
                        logger.debug(f"✅ 找到导弹 {missile_id} 在 {target_time} 的位置 ({method}) - 时间差较大但在允许范围内")
                    else:
                        logger.debug(f"✅ 找到导弹 {missile_id} 在 {target_time} 的位置 ({method})")
                    return position_info
                else:
                    logger.warning(f"⚠️ 导弹 {missile_id} 在 {target_time} 的最近位置时间差过大: {min_time_diff:.1f}秒 (阈值: {max_time_diff}秒)")
                    return None
            else:
                logger.warning(f"⚠️ 未找到导弹 {missile_id} 在 {target_time} 的位置数据")
                return None

        except Exception as e:
            logger.error(f"❌ 查找导弹 {missile_id} 位置失败: {e}")
            return None

    def _generate_missile_specific_tasks(self, missile_id: str, time_grid: List[Dict[str, Any]],
                                       midcourse_info: Dict[str, Any],
                                       planning_cycle: Dict[str, Any]) -> Dict[str, Any]:
        """
        为特定导弹生成真实任务和虚拟任务

        Args:
            missile_id: 导弹ID
            time_grid: 全局时间网格
            midcourse_info: 中段飞行时间信息
            planning_cycle: 规划周期信息

        Returns:
            包含真实任务和虚拟任务的字典
        """
        try:
            midcourse_start = midcourse_info["midcourse_start"]
            midcourse_end = midcourse_info["midcourse_end"]

            real_tasks = []
            virtual_tasks = []
            all_tasks = []

            for time_slot in time_grid:
                slot_start = time_slot["start_time"]
                slot_end = time_slot["end_time"]

                # 判断该时间槽是否与导弹中段飞行时间重叠
                is_real_task = self._is_time_overlap(slot_start, slot_end, midcourse_start, midcourse_end)

                # 获取任务起始时刻的导弹位置信息（从已有轨迹数据中查找）
                missile_position_start = self._find_missile_position_at_time(missile_id, slot_start)
                missile_position_end = self._find_missile_position_at_time(missile_id, slot_end)

                # 创建任务
                task = {
                    "task_id": time_slot["task_id"],
                    "task_index": time_slot["task_index"],
                    "start_time": slot_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": slot_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": time_slot["duration_seconds"],
                    "start_time_iso": time_slot["start_time_iso"],
                    "end_time_iso": time_slot["end_time_iso"],
                    "task_type": "real_meta_task" if is_real_task else "virtual_meta_task",

                    # 导弹位置信息
                    "missile_position": {
                        "start_position": missile_position_start,
                        "end_position": missile_position_end,
                        "has_position_data": missile_position_start is not None and missile_position_end is not None
                    }
                }

                # 分类任务
                if is_real_task:
                    real_tasks.append(task)
                else:
                    virtual_tasks.append(task)

                all_tasks.append(task)

            logger.debug(f"导弹 {missile_id}: {len(real_tasks)} 真实任务, {len(virtual_tasks)} 虚拟任务")

            return {
                "all_tasks": all_tasks,
                "real_tasks": real_tasks,
                "virtual_tasks": virtual_tasks
            }

        except Exception as e:
            logger.error(f"❌ 生成导弹 {missile_id} 特定任务失败: {e}")
            return {"all_tasks": [], "real_tasks": [], "virtual_tasks": []}

    def _is_time_overlap(self, slot_start: datetime, slot_end: datetime,
                        midcourse_start: datetime, midcourse_end: datetime) -> bool:
        """
        判断时间槽是否与中段飞行时间重叠

        Args:
            slot_start: 时间槽开始时间
            slot_end: 时间槽结束时间
            midcourse_start: 中段飞行开始时间
            midcourse_end: 中段飞行结束时间

        Returns:
            是否重叠
        """
        # 时间重叠判断：slot_start < midcourse_end 且 slot_end > midcourse_start
        return slot_start < midcourse_end and slot_end > midcourse_start

    def _determine_global_planning_cycle(self, all_meta_tasks: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据所有导弹的元任务确定全局规划周期

        Args:
            all_meta_tasks: 所有导弹的元任务

        Returns:
            全局规划周期信息
        """
        try:
            if not all_meta_tasks:
                return {}

            # 获取第一个导弹的规划周期作为全局规划周期
            first_missile = next(iter(all_meta_tasks.values()))
            return first_missile["planning_cycle"]

        except Exception as e:
            logger.error(f"❌ 确定全局规划周期失败: {e}")
            return {}
    
    def get_atomic_task_set(self) -> Dict[str, Any]:
        """
        获取公共元子任务集
        
        Returns:
            元子任务集信息
        """
        return self.atomic_task_sets
