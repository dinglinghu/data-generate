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

        logger.info("🛰️ 卫星位置同步器初始化完成")
        logger.info(f"   采样间隔: {self.position_sample_interval}秒")
        logger.info(f"   最大采样点数: {self.max_samples_per_task}")
        logger.info(f"   统计计算: {'启用' if self.enable_statistics else '禁用'}")
        logger.info(f"   并发处理: {'启用' if self.enable_concurrent else '禁用'}")
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

            # 🔧 修复：由于STK COM接口的多线程问题，暂时禁用并发处理
            logger.info("🔧 使用串行处理模式（避免STK COM多线程问题）")
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
        """计算采样时间点"""
        sample_times = []

        # 任务持续时间
        duration = (end_time - start_time).total_seconds()

        # 🔧 修复：改进短任务的判断逻辑
        if duration <= self.position_sample_interval * 2:
            # 短任务：只采样开始和结束时间
            sample_times = [start_time]
            if start_time != end_time:
                sample_times.append(end_time)
        else:
            # 长任务：按间隔采样
            current_time = start_time
            while current_time <= end_time:
                sample_times.append(current_time)
                current_time += timedelta(seconds=self.position_sample_interval)

            # 确保包含结束时间
            if sample_times[-1] != end_time:
                sample_times.append(end_time)

        # 限制最大采样点数
        if len(sample_times) > self.max_samples_per_task:
            # 均匀分布采样点
            step = max(1, len(sample_times) // self.max_samples_per_task)
            sample_times = sample_times[::step][:self.max_samples_per_task]

            # 确保包含开始和结束时间
            if start_time not in sample_times:
                sample_times[0] = start_time
            if end_time not in sample_times and len(sample_times) > 1:
                sample_times[-1] = end_time

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
