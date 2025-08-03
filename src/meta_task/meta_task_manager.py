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
        
        logger.info("🎯 元任务管理器初始化完成")
        logger.info(f"   元子任务时间间隔: {self.atomic_task_interval}秒")
    
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

            # 获取标准化参数
            standard_duration = standardized_config.get("standard_duration", 2400)  # 40分钟
            min_duration = standardized_config.get("min_duration", 1800)  # 30分钟
            max_duration = standardized_config.get("max_duration", 2700)  # 45分钟
            overlap_duration = standardized_config.get("overlap_duration", 300)  # 5分钟

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
        计算导弹的中段飞行时间段
        
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
            
            # 估算导弹飞行总时间（默认30分钟）
            flight_time_config = self.config_manager.config.get("missile_management", {}).get("flight_time", {})
            default_flight_minutes = flight_time_config.get("default_minutes", 30)
            total_flight_time = timedelta(minutes=default_flight_minutes)
            
            # 计算撞击时间
            impact_time = launch_time + total_flight_time
            
            # 中段飞行阶段：假设为飞行时间的中间60%（跳过起始和结束各20%）
            boost_phase_ratio = 0.2  # 助推段占20%
            terminal_phase_ratio = 0.2  # 末段占20%
            midcourse_ratio = 1.0 - boost_phase_ratio - terminal_phase_ratio  # 中段占60%
            
            boost_duration = total_flight_time * boost_phase_ratio
            midcourse_duration = total_flight_time * midcourse_ratio
            
            midcourse_start = launch_time + boost_duration
            midcourse_end = midcourse_start + midcourse_duration
            
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
                }
            }
            
            logger.debug(f"导弹 {missile_id} 中段飞行时间: {midcourse_start} -> {midcourse_end}")
            
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

                # 创建任务
                task = {
                    "task_id": time_slot["task_id"],
                    "task_index": time_slot["task_index"],
                    "start_time": slot_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": slot_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_seconds": time_slot["duration_seconds"],
                    "start_time_iso": time_slot["start_time_iso"],
                    "end_time_iso": time_slot["end_time_iso"],
                    "task_type": "real_meta_task" if is_real_task else "virtual_meta_task"
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
