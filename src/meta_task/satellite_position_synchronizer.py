#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
卫星位置同步器
为每个可见元任务同步卫星在任务时间段内的位置信息
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import asyncio
import concurrent.futures
import threading
from functools import partial

from .parallel_position_manager import ParallelPositionManager, PositionRequest, PositionResult

logger = logging.getLogger(__name__)

class SatellitePositionSynchronizer:
    """卫星位置同步器"""
    
    def __init__(self, stk_manager, time_manager, config_manager=None):
        """
        初始化卫星位置同步器

        Args:
            stk_manager: STK管理器实例
            time_manager: 时间管理器实例
            config_manager: 配置管理器实例
        """
        self.stk_manager = stk_manager
        self.time_manager = time_manager

        # 获取配置
        if config_manager:
            from ..utils.config_manager import get_config_manager
            self.config_manager = config_manager
        else:
            from ..utils.config_manager import get_config_manager
            self.config_manager = get_config_manager()

        # 获取位置同步配置
        meta_task_config = self.config_manager.config.get("meta_task_management", {})
        position_sync_config = meta_task_config.get("position_sync", {})

        # 位置采样配置
        self.position_sample_interval = position_sync_config.get("sample_interval_seconds", 30)
        self.max_samples_per_task = position_sync_config.get("max_samples_per_task", 20)
        self.enable_statistics = position_sync_config.get("enable_statistics", True)
        self.export_detailed_data = position_sync_config.get("export_detailed_data", False)

        # 并发配置
        self.enable_concurrent = position_sync_config.get("enable_concurrent", True)
        self.max_workers = position_sync_config.get("max_workers", 4)
        self.concurrent_batch_size = position_sync_config.get("concurrent_batch_size", 10)
        self.stk_com_timeout = position_sync_config.get("stk_com_timeout", 30)

        # STK COM接口线程安全锁
        self._stk_lock = threading.Lock()

        # 初始化并行位置管理器
        self.parallel_position_manager = ParallelPositionManager(
            stk_manager=self.stk_manager,
            config_manager=self.config_manager
        )

        # 并行处理配置
        self.enable_parallel_optimization = position_sync_config.get("enable_parallel_optimization", True)

        logger.info("🛰️ 卫星位置同步器初始化完成")
        logger.info(f"   采样间隔: {self.position_sample_interval}秒")
        logger.info(f"   最大采样点数: {self.max_samples_per_task}")
        logger.info(f"   统计计算: {'启用' if self.enable_statistics else '禁用'}")
        logger.info(f"   并发处理: {'启用' if self.enable_concurrent else '禁用'}")
        logger.info(f"   并行优化: {'启用' if self.enable_parallel_optimization else '禁用'}")
        if self.enable_concurrent:
            logger.info(f"   最大工作线程: {self.max_workers}")
            logger.info(f"   批处理大小: {self.concurrent_batch_size}")
    
    def synchronize_satellite_positions_for_visible_tasks(self, visible_meta_tasks: Dict[str, Any]) -> Dict[str, Any]:
        """
        为所有可见元任务同步卫星位置（支持并发处理）

        Args:
            visible_meta_tasks: 可见元任务数据

        Returns:
            增强后的可见元任务数据（包含卫星位置信息）
        """
        try:
            start_time = datetime.now()
            logger.info("🛰️ 开始为可见元任务同步卫星位置...")

            enhanced_visible_tasks = visible_meta_tasks.copy()

            # 获取星座可见任务集
            constellation_visible_task_sets = enhanced_visible_tasks.get("constellation_visible_task_sets", {})

            # 选择最优的处理模式
            if self.enable_parallel_optimization:
                logger.info("🚀 使用并行优化模式")
                total_tasks_processed, total_positions_collected = self._process_tasks_parallel_optimized(
                    constellation_visible_task_sets
                )
            elif self.enable_concurrent:
                logger.info("🧵 使用并发处理模式")
                total_tasks_processed, total_positions_collected = self._process_tasks_concurrently(
                    constellation_visible_task_sets
                )
            else:
                logger.info("📝 使用串行处理模式")
                total_tasks_processed, total_positions_collected = self._process_tasks_serially(
                    constellation_visible_task_sets
                )

            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()

            # 添加同步统计信息
            enhanced_visible_tasks["position_sync_metadata"] = {
                "sync_time": datetime.now().isoformat(),
                "total_tasks_processed": total_tasks_processed,
                "total_positions_collected": total_positions_collected,
                "sample_interval_seconds": self.position_sample_interval,
                "processing_time_seconds": processing_time,
                "concurrent_enabled": self.enable_concurrent,
                "max_workers": self.max_workers if self.enable_concurrent else 1,
                "sync_status": "completed"
            }

            logger.info(f"🛰️ 卫星位置同步完成:")
            logger.info(f"   处理任务数: {total_tasks_processed}")
            logger.info(f"   采集位置点数: {total_positions_collected}")
            logger.info(f"   处理时间: {processing_time:.2f}秒")
            logger.info(f"   处理模式: {'并发' if self.enable_concurrent else '串行'}")

            return enhanced_visible_tasks

        except Exception as e:
            logger.error(f"❌ 卫星位置同步失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return visible_meta_tasks

    def _process_tasks_parallel_optimized(self, constellation_visible_task_sets: Dict[str, Any]) -> Tuple[int, int]:
        """
        使用并行位置管理器优化处理所有可见任务的位置同步

        Args:
            constellation_visible_task_sets: 星座可见任务集

        Returns:
            (处理任务数, 采集位置点数)
        """
        try:
            logger.info("🚀 开始并行优化位置同步...")

            # 1. 收集所有位置请求
            position_requests = []
            task_mapping = {}  # 用于映射请求到任务

            for satellite_id, satellite_tasks in constellation_visible_task_sets.items():
                missile_tasks = satellite_tasks.get("missile_tasks", {})

                for missile_id, missile_task_data in missile_tasks.items():
                    visible_tasks = missile_task_data.get("visible_tasks", [])

                    for task in visible_tasks:
                        # 为每个任务生成位置请求
                        task_requests = self._generate_position_requests_for_task(satellite_id, task)
                        position_requests.extend(task_requests)

                        # 建立映射关系 - 使用唯一键避免task_id冲突
                        task_id = task.get("task_id")
                        unique_task_key = f"{satellite_id}_{missile_id}_{task_id}"
                        task_mapping[unique_task_key] = {
                            "satellite_id": satellite_id,
                            "missile_id": missile_id,
                            "task_id": task_id,
                            "task": task,
                            "request_indices": list(range(len(position_requests) - len(task_requests), len(position_requests)))
                        }

            # 计算优化效果
            expected_requests_old = len(task_mapping) * 11  # 旧策略：平均每任务11个采样点（30秒间隔）
            actual_requests = len(position_requests)
            optimization_ratio = (expected_requests_old - actual_requests) / max(1, expected_requests_old) * 100

            logger.info(f"📊 收集到 {actual_requests} 个位置请求，覆盖 {len(task_mapping)} 个任务")
            logger.info(f"🚀 采样优化: 预期{expected_requests_old}个请求 → 实际{actual_requests}个请求 (减少{optimization_ratio:.1f}%)")
            logger.info(f"⚡ 策略: 每个可见元任务只采集开始和结束时刻位置，大幅加速数据采集")

            # 2. 并行获取所有位置
            if position_requests:
                position_results = self.parallel_position_manager.get_positions_parallel(position_requests)

                # 3. 组织结果并更新任务
                total_tasks_processed = 0
                total_positions_collected = 0

                for unique_task_key, mapping_info in task_mapping.items():
                    satellite_id = mapping_info["satellite_id"]
                    missile_id = mapping_info["missile_id"]
                    task_id = mapping_info["task_id"]
                    task = mapping_info["task"]
                    request_indices = mapping_info["request_indices"]

                    # 提取该任务的位置结果
                    task_position_results = [position_results[i] for i in request_indices if i < len(position_results)]

                    # 构建位置同步数据
                    position_sync_data = self._build_position_sync_data_from_results(
                        satellite_id, task, task_position_results
                    )

                    if position_sync_data:
                        task["satellite_position_sync"] = position_sync_data
                        total_positions_collected += len(position_sync_data.get("position_samples", []))
                        total_tasks_processed += 1
                        logger.debug(f"✅ 任务 {satellite_id}-{missile_id}-{task_id} 并行位置同步完成")
                    else:
                        logger.warning(f"⚠️ 任务 {satellite_id}-{missile_id}-{task_id} 并行位置同步失败")

                # 4. 输出性能统计
                parallel_stats = self.parallel_position_manager.get_stats()
                logger.info("📊 并行位置同步性能统计:")
                logger.info(f"   总请求数: {parallel_stats.get('total_requests', 0)}")
                logger.info(f"   成功率: {parallel_stats.get('success_rate', 0):.1f}%")
                logger.info(f"   缓存命中率: {parallel_stats.get('cache_hit_rate', 0):.1f}%")
                logger.info(f"   平均处理时间: {parallel_stats.get('average_time_per_request', 0):.3f}s")

                return total_tasks_processed, total_positions_collected
            else:
                logger.warning("⚠️ 没有位置请求需要处理")
                return 0, 0

        except Exception as e:
            logger.error(f"❌ 并行优化位置同步失败: {e}")
            # 回退到串行处理
            logger.info("🔄 回退到串行处理模式...")
            return self._process_tasks_serially(constellation_visible_task_sets)

    def _process_tasks_concurrently(self, constellation_visible_task_sets: Dict[str, Any]) -> Tuple[int, int]:
        """
        并发处理所有可见任务的位置同步

        Args:
            constellation_visible_task_sets: 星座可见任务集

        Returns:
            (处理任务数, 采集位置点数)
        """
        try:
            # 收集所有需要处理的任务
            task_items = []

            for satellite_id, satellite_tasks in constellation_visible_task_sets.items():
                missile_tasks = satellite_tasks.get("missile_tasks", {})

                for missile_id, missile_task_data in missile_tasks.items():
                    visible_tasks = missile_task_data.get("visible_tasks", [])

                    for task in visible_tasks:
                        task_items.append((satellite_id, task))

            logger.info(f"🚀 并发处理 {len(task_items)} 个可见任务，使用 {self.max_workers} 个工作线程")

            total_tasks_processed = 0
            total_positions_collected = 0

            # 分批处理以避免过多的并发连接
            batch_size = self.concurrent_batch_size

            for i in range(0, len(task_items), batch_size):
                batch = task_items[i:i + batch_size]
                logger.debug(f"处理批次 {i//batch_size + 1}: {len(batch)} 个任务")

                # 使用线程池并发处理当前批次
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    # 提交所有任务
                    future_to_task = {
                        executor.submit(self._synchronize_position_for_task_thread_safe, satellite_id, task): (satellite_id, task)
                        for satellite_id, task in batch
                    }

                    # 收集结果
                    for future in concurrent.futures.as_completed(future_to_task):
                        satellite_id, task = future_to_task[future]
                        try:
                            position_data = future.result()

                            if position_data:
                                task["satellite_position_sync"] = position_data
                                total_positions_collected += len(position_data.get("position_samples", []))
                                total_tasks_processed += 1

                                logger.debug(f"✅ 任务 {task.get('task_id')} 位置同步完成")
                            else:
                                logger.warning(f"⚠️ 任务 {task.get('task_id')} 位置同步失败")

                        except Exception as e:
                            logger.error(f"❌ 任务 {task.get('task_id')} 处理异常: {e}")

            return total_tasks_processed, total_positions_collected

        except Exception as e:
            logger.error(f"❌ 并发处理失败: {e}")
            return 0, 0

    def _process_tasks_serially(self, constellation_visible_task_sets: Dict[str, Any]) -> Tuple[int, int]:
        """
        串行处理所有可见任务的位置同步（原有逻辑）

        Args:
            constellation_visible_task_sets: 星座可见任务集

        Returns:
            (处理任务数, 采集位置点数)
        """
        total_tasks_processed = 0
        total_positions_collected = 0

        # 遍历每个卫星的可见任务
        for satellite_id, satellite_tasks in constellation_visible_task_sets.items():
            logger.info(f"🛰️ 处理卫星 {satellite_id} 的可见任务...")

            # 处理该卫星的所有导弹任务
            missile_tasks = satellite_tasks.get("missile_tasks", {})

            for missile_id, missile_task_data in missile_tasks.items():
                # 处理可见任务
                visible_tasks = missile_task_data.get("visible_tasks", [])

                for task in visible_tasks:
                    # 为每个可见任务同步卫星位置
                    position_data = self._synchronize_position_for_task(
                        satellite_id, task
                    )

                    if position_data:
                        task["satellite_position_sync"] = position_data
                        total_positions_collected += len(position_data.get("position_samples", []))
                        total_tasks_processed += 1

                        logger.debug(f"✅ 任务 {task.get('task_id')} 位置同步完成")
                    else:
                        logger.warning(f"⚠️ 任务 {task.get('task_id')} 位置同步失败")

        return total_tasks_processed, total_positions_collected

    def _synchronize_position_for_task_thread_safe(self, satellite_id: str, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        线程安全的任务位置同步方法

        Args:
            satellite_id: 卫星ID
            task: 任务信息

        Returns:
            位置同步数据
        """
        try:
            # 使用锁确保STK COM接口的线程安全
            with self._stk_lock:
                return self._synchronize_position_for_task(satellite_id, task)
        except Exception as e:
            logger.error(f"❌ 线程安全位置同步失败 {task.get('task_id')}: {e}")
            return None

    def _synchronize_position_for_task(self, satellite_id: str, task: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        为单个任务同步卫星位置
        
        Args:
            satellite_id: 卫星ID
            task: 任务信息
            
        Returns:
            位置同步数据
        """
        try:
            # 获取任务时间范围
            start_time_str = task.get("start_time_iso") or task.get("start_time")
            end_time_str = task.get("end_time_iso") or task.get("end_time")
            
            if not start_time_str or not end_time_str:
                logger.warning(f"⚠️ 任务时间信息不完整: {task.get('task_id')}")
                return None
            
            # 解析时间
            start_time = self._parse_time_string(start_time_str)
            end_time = self._parse_time_string(end_time_str)
            
            if not start_time or not end_time:
                logger.warning(f"⚠️ 任务时间解析失败: {task.get('task_id')}")
                return None
            
            # 计算采样时间点
            sample_times = self._calculate_sample_times(start_time, end_time)
            
            # 采集位置数据
            position_samples = []
            
            for sample_time in sample_times:
                # 计算相对于场景开始时间的偏移
                time_offset = self._calculate_time_offset(sample_time)
                
                # 获取卫星在该时间点的位置（使用配置的超时时间）
                position_data = self.stk_manager.get_satellite_position(satellite_id, time_offset, self.stk_com_timeout)
                
                if position_data:
                    # 增强位置数据
                    enhanced_position = {
                        "sample_time": sample_time.isoformat(),
                        "time_offset_seconds": time_offset,
                        "position": position_data,
                        "task_relative_time": (sample_time - start_time).total_seconds()
                    }
                    position_samples.append(enhanced_position)
                else:
                    logger.debug(f"⚠️ 无法获取 {satellite_id} 在 {sample_time} 的位置")
            
            if not position_samples:
                logger.warning(f"⚠️ 任务 {task.get('task_id')} 未获取到任何位置数据")
                return None
            
            # 计算位置统计信息
            position_stats = self._calculate_position_statistics(position_samples)
            
            return {
                "task_id": task.get("task_id"),
                "satellite_id": satellite_id,
                "task_time_range": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": (end_time - start_time).total_seconds()
                },
                "position_samples": position_samples,
                "position_statistics": position_stats,
                "sample_count": len(position_samples),
                "sample_interval_seconds": self.position_sample_interval
            }
            
        except Exception as e:
            logger.error(f"❌ 任务位置同步失败 {task.get('task_id')}: {e}")
            return None
    
    def _parse_time_string(self, time_str: str) -> Optional[datetime]:
        """解析时间字符串"""
        try:
            # 尝试ISO格式
            if 'T' in time_str:
                return datetime.fromisoformat(time_str.replace('T', ' '))
            else:
                return datetime.fromisoformat(time_str)
        except:
            try:
                # 尝试标准格式
                return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            except:
                logger.warning(f"⚠️ 无法解析时间字符串: {time_str}")
                return None
    
    def _calculate_sample_times(self, start_time: datetime, end_time: datetime) -> List[datetime]:
        """
        计算采样时间点

        🚀 优化策略：对于可见元任务，只采集开始和结束时刻的位置信息
        这样可以大大加速数据采集速度，从699个请求减少到128个请求（64个任务 × 2个时间点）
        """
        sample_times = []

        # 任务持续时间
        duration = (end_time - start_time).total_seconds()

        # 🚀 优化：对于可见元任务，只采集开始和结束时刻的位置
        # 这是最高效的策略，满足位置信息需求的同时最大化采集速度
        sample_times = [start_time]
        if start_time != end_time:
            sample_times.append(end_time)

        logger.debug(f"📍 任务采样策略: 持续时间{duration:.1f}s, 采样点数: {len(sample_times)}")

        return sample_times
    
    def _calculate_time_offset(self, target_time: datetime) -> float:
        """计算相对于场景开始时间的偏移量（秒）"""
        try:
            scenario_start = self.time_manager.start_time
            offset = (target_time - scenario_start).total_seconds()
            return offset
        except Exception as e:
            logger.warning(f"⚠️ 时间偏移计算失败: {e}")
            return 0.0
    
    def _calculate_position_statistics(self, position_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算位置统计信息"""
        try:
            if not position_samples:
                return {}
            
            # 提取坐标数据
            coordinates = []
            for sample in position_samples:
                pos = sample.get("position", {})
                if "x" in pos and "y" in pos and "z" in pos:
                    coordinates.append((pos["x"], pos["y"], pos["z"]))
                elif "lat" in pos and "lon" in pos and "alt" in pos:
                    coordinates.append((pos["lat"], pos["lon"], pos["alt"]))
            
            if not coordinates:
                return {"error": "no_valid_coordinates"}
            
            # 计算统计信息
            if len(coordinates[0]) == 3:  # 笛卡尔坐标或LLA坐标
                x_coords, y_coords, z_coords = zip(*coordinates)
                
                stats = {
                    "coordinate_type": "cartesian" if abs(max(x_coords)) > 1000 else "lla",
                    "x_range": {"min": min(x_coords), "max": max(x_coords)},
                    "y_range": {"min": min(y_coords), "max": max(y_coords)},
                    "z_range": {"min": min(z_coords), "max": max(z_coords)},
                    "sample_count": len(coordinates)
                }
                
                # 计算移动距离（如果是笛卡尔坐标）
                if stats["coordinate_type"] == "cartesian":
                    total_distance = 0
                    for i in range(1, len(coordinates)):
                        dx = coordinates[i][0] - coordinates[i-1][0]
                        dy = coordinates[i][1] - coordinates[i-1][1]
                        dz = coordinates[i][2] - coordinates[i-1][2]
                        distance = (dx**2 + dy**2 + dz**2)**0.5
                        total_distance += distance
                    
                    stats["total_movement_km"] = total_distance / 1000  # 转换为公里
                
                return stats
            
        except Exception as e:
            logger.warning(f"⚠️ 位置统计计算失败: {e}")
            return {"error": str(e)}
        
        return {}
    
    def export_position_sync_data(self, enhanced_visible_tasks: Dict[str, Any], output_file: str):
        """导出位置同步数据到文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(enhanced_visible_tasks, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"📁 位置同步数据已导出: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ 导出位置同步数据失败: {e}")

    def _generate_position_requests_for_task(self, satellite_id: str, task: Dict[str, Any]) -> List[PositionRequest]:
        """
        为单个任务生成位置请求列表

        Args:
            satellite_id: 卫星ID
            task: 任务信息

        Returns:
            位置请求列表
        """
        try:
            # 解析任务时间范围 - 优先使用ISO格式
            start_time_str = task.get("start_time_iso") or task.get("start_time")
            end_time_str = task.get("end_time_iso") or task.get("end_time")
            task_id = task.get("task_id")

            if not start_time_str or not end_time_str:
                logger.warning(f"⚠️ 任务 {task_id} 时间范围无效")
                return []

            # 转换时间格式 - 处理不同的时间格式
            try:
                # 首先尝试ISO格式
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except ValueError:
                # 如果ISO格式失败，尝试标准格式
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

            # 计算采样时间点
            sample_times = self._calculate_sample_times(start_time, end_time)

            # 生成位置请求
            requests = []
            for sample_time in sample_times:
                time_offset = self._calculate_time_offset(sample_time)

                request = PositionRequest(
                    satellite_id=satellite_id,
                    time_offset=time_offset,
                    sample_time=sample_time,
                    task_id=task_id,
                    priority=1  # 高优先级
                )
                requests.append(request)

            return requests

        except Exception as e:
            logger.error(f"❌ 生成任务 {task.get('task_id')} 位置请求失败: {e}")
            return []

    def _build_position_sync_data_from_results(self, satellite_id: str, task: Dict[str, Any],
                                             position_results: List[PositionResult]) -> Optional[Dict[str, Any]]:
        """
        从位置结果构建位置同步数据

        Args:
            satellite_id: 卫星ID
            task: 任务信息
            position_results: 位置结果列表

        Returns:
            位置同步数据
        """
        try:
            # 过滤成功的结果
            successful_results = [r for r in position_results if r.success and r.position_data]

            if not successful_results:
                logger.warning(f"⚠️ 任务 {task.get('task_id')} 没有成功的位置数据")
                return None

            # 构建位置样本
            position_samples = []

            # 解析任务开始时间用于计算相对时间
            task_start_time_str = task.get("start_time_iso") or task.get("start_time")
            try:
                # 首先尝试ISO格式
                task_start_time = datetime.fromisoformat(task_start_time_str.replace('Z', '+00:00'))
            except ValueError:
                # 如果ISO格式失败，尝试标准格式
                task_start_time = datetime.strptime(task_start_time_str, "%Y-%m-%d %H:%M:%S")

            for result in successful_results:
                enhanced_position = {
                    "sample_time": result.request.sample_time.isoformat(),
                    "time_offset_seconds": result.request.time_offset,
                    "position": result.position_data,
                    "task_relative_time": (result.request.sample_time - task_start_time).total_seconds(),
                    "processing_time": result.processing_time
                }
                position_samples.append(enhanced_position)

            # 计算位置统计信息
            position_stats = self._calculate_position_statistics(position_samples)

            # 解析任务时间范围 - 优先使用ISO格式
            start_time_str = task.get("start_time_iso") or task.get("start_time")
            end_time_str = task.get("end_time_iso") or task.get("end_time")

            # 转换时间格式 - 处理不同的时间格式
            try:
                # 首先尝试ISO格式
                start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            except ValueError:
                # 如果ISO格式失败，尝试标准格式
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")

            return {
                "task_id": task.get("task_id"),
                "satellite_id": satellite_id,
                "task_time_range": {
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": (end_time - start_time).total_seconds()
                },
                "position_samples": position_samples,
                "position_statistics": position_stats,
                "sample_count": len(position_samples),
                "sample_interval_seconds": self.position_sample_interval,
                "parallel_processing": True,
                "success_rate": len(successful_results) / len(position_results) * 100 if position_results else 0
            }

        except Exception as e:
            logger.error(f"❌ 构建任务 {task.get('task_id')} 位置同步数据失败: {e}")
            return None

    def get_parallel_performance_stats(self) -> Dict[str, Any]:
        """获取并行处理性能统计"""
        if hasattr(self, 'parallel_position_manager'):
            return self.parallel_position_manager.get_stats()
        return {}

    def clear_parallel_cache(self):
        """清空并行处理缓存"""
        if hasattr(self, 'parallel_position_manager'):
            self.parallel_position_manager.clear_cache()
            logger.info("🧹 并行位置缓存已清空")
