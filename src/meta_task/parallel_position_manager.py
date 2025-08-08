#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行卫星位置管理器
使用多种并行策略优化卫星位置获取性能
"""

import logging
import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from queue import Queue
import multiprocessing as mp

logger = logging.getLogger(__name__)

@dataclass
class PositionRequest:
    """位置请求数据结构"""
    satellite_id: str
    time_offset: float
    sample_time: datetime
    task_id: str = None
    priority: int = 1  # 1=高优先级, 2=中优先级, 3=低优先级

@dataclass
class PositionResult:
    """位置结果数据结构"""
    request: PositionRequest
    position_data: Optional[Dict[str, Any]]
    success: bool
    error: Optional[str] = None
    processing_time: float = 0.0

class ParallelPositionManager:
    """并行卫星位置管理器"""
    
    def __init__(self, stk_manager, config_manager=None):
        """
        初始化并行位置管理器
        
        Args:
            stk_manager: STK管理器实例
            config_manager: 配置管理器实例
        """
        self.stk_manager = stk_manager
        self.config_manager = config_manager
        
        # 并行配置
        self.max_workers = min(8, mp.cpu_count())  # 最大工作线程数
        self.batch_size = 20  # 批处理大小
        self.timeout_per_request = 10.0  # 单个请求超时时间
        self.enable_async = True  # 启用异步处理
        self.enable_threading = True  # 启用多线程
        self.enable_batching = True  # 启用批处理

        # 缓存配置 - 从配置文件读取
        if config_manager:
            position_config = config_manager.get_position_config()
            self.enable_cache = position_config.get('enable_position_cache', False)
        else:
            self.enable_cache = False  # 默认禁用缓存

        logger.info(f"💾 位置缓存: {'启用' if self.enable_cache else '禁用'}")
        
        # 性能统计
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "parallel_time": 0.0,
            "cache_hits": 0,
            "batch_count": 0
        }
        
        # 位置缓存
        self._position_cache = {}
        self._cache_lock = threading.Lock()
        
        logger.info(f"🚀 并行位置管理器初始化完成")
        logger.info(f"   最大工作线程: {self.max_workers}")
        logger.info(f"   批处理大小: {self.batch_size}")
    
    def get_positions_parallel(self, requests: List[PositionRequest]) -> List[PositionResult]:
        """
        并行获取多个卫星位置
        
        Args:
            requests: 位置请求列表
            
        Returns:
            位置结果列表
        """
        if not requests:
            return []
        
        start_time = time.time()
        logger.info(f"🚀 开始并行获取 {len(requests)} 个位置...")
        
        # 临时禁用多线程模式，避免STK COM对象的多线程问题
        # 强制使用串行模式
        logger.info("🔧 使用串行模式避免STK COM多线程问题")
        results = self._get_positions_serial(requests)
        
        total_time = time.time() - start_time
        
        # 更新统计
        self.stats["total_requests"] += len(requests)
        self.stats["successful_requests"] += sum(1 for r in results if r.success)
        self.stats["failed_requests"] += sum(1 for r in results if not r.success)
        self.stats["parallel_time"] += total_time
        
        success_rate = self.stats["successful_requests"] / self.stats["total_requests"] * 100
        
        logger.info(f"✅ 并行位置获取完成")
        logger.info(f"   处理时间: {total_time:.2f}s")
        logger.info(f"   成功率: {success_rate:.1f}%")
        logger.info(f"   平均每个: {total_time/len(requests):.3f}s")
        
        return results
    
    def _get_positions_async(self, requests: List[PositionRequest]) -> List[PositionResult]:
        """异步并行获取位置"""
        logger.info(f"🔄 使用异步并行模式处理 {len(requests)} 个请求...")
        
        try:
            # 创建新的事件循环（避免与现有循环冲突）
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                results = loop.run_until_complete(self._async_get_positions(requests))
                return results
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"❌ 异步处理失败，回退到线程模式: {e}")
            return self._get_positions_threaded(requests)
    
    async def _async_get_positions(self, requests: List[PositionRequest]) -> List[PositionResult]:
        """异步获取位置的核心实现"""
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def get_single_position(request: PositionRequest) -> PositionResult:
            async with semaphore:
                return await self._async_single_position(request)
        
        # 创建所有任务
        tasks = [get_single_position(req) for req in requests]
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(PositionResult(
                    request=requests[i],
                    position_data=None,
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _async_single_position(self, request: PositionRequest) -> PositionResult:
        """异步获取单个位置"""
        start_time = time.time()
        
        try:
            # 检查缓存
            cache_key = f"{request.satellite_id}_{request.time_offset}"
            cached_result = self._get_cached_position(cache_key)
            if cached_result:
                self.stats["cache_hits"] += 1
                return PositionResult(
                    request=request,
                    position_data=cached_result,
                    success=True,
                    processing_time=time.time() - start_time
                )
            
            # 在线程池中执行STK调用（避免阻塞事件循环）
            loop = asyncio.get_event_loop()
            position_data = await loop.run_in_executor(
                None,
                self._get_position_sync,
                request.satellite_id,
                request.time_offset
            )
            
            # 缓存结果
            if position_data:
                self._cache_position(cache_key, position_data)
            
            return PositionResult(
                request=request,
                position_data=position_data,
                success=position_data is not None,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return PositionResult(
                request=request,
                position_data=None,
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _get_positions_threaded(self, requests: List[PositionRequest]) -> List[PositionResult]:
        """多线程并行获取位置"""
        logger.info(f"🧵 使用多线程模式处理 {len(requests)} 个请求...")
        
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_request = {
                executor.submit(self._get_single_position_threaded, req): req 
                for req in requests
            }
            
            # 收集结果
            for future in as_completed(future_to_request, timeout=self.timeout_per_request * len(requests)):
                try:
                    result = future.result(timeout=self.timeout_per_request)
                    results.append(result)
                except Exception as e:
                    request = future_to_request[future]
                    results.append(PositionResult(
                        request=request,
                        position_data=None,
                        success=False,
                        error=str(e)
                    ))
        
        return results
    
    def _get_single_position_threaded(self, request: PositionRequest) -> PositionResult:
        """线程安全的单个位置获取"""
        start_time = time.time()
        
        try:
            # 检查缓存
            cache_key = f"{request.satellite_id}_{request.time_offset}"
            cached_result = self._get_cached_position(cache_key)
            if cached_result:
                self.stats["cache_hits"] += 1
                return PositionResult(
                    request=request,
                    position_data=cached_result,
                    success=True,
                    processing_time=time.time() - start_time
                )
            
            # 获取位置数据
            position_data = self._get_position_sync(request.satellite_id, request.time_offset)
            
            # 缓存结果
            if position_data:
                self._cache_position(cache_key, position_data)
            
            return PositionResult(
                request=request,
                position_data=position_data,
                success=position_data is not None,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return PositionResult(
                request=request,
                position_data=None,
                success=False,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _get_positions_serial(self, requests: List[PositionRequest]) -> List[PositionResult]:
        """串行获取位置（回退方案）"""
        logger.info(f"📝 使用串行模式处理 {len(requests)} 个请求...")

        results = []
        for i, request in enumerate(requests):
            start_time = time.time()
            logger.info(f"📍 处理位置请求 {i+1}/{len(requests)}: {request.satellite_id} @ {request.time_offset}s")

            try:
                logger.info(f"🔍 开始处理请求: {request.satellite_id} @ {request.time_offset}s")

                # 检查缓存（如果启用）
                cache_key = f"{request.satellite_id}_{request.time_offset}"
                logger.info(f"🔍 检查缓存: {cache_key}")
                cached_result = self._get_cached_position(cache_key)
                if cached_result:
                    self.stats["cache_hits"] += 1
                    logger.info(f"💾 使用缓存数据: {request.satellite_id}")
                    results.append(PositionResult(
                        request=request,
                        position_data=cached_result,
                        success=True,
                        processing_time=time.time() - start_time
                    ))
                    continue

                logger.info(f"🔍 从STK获取实时位置: {request.satellite_id}")
                # 使用原始STK管理器方法获取位置
                position_data = self.stk_manager.get_satellite_position(
                    request.satellite_id,
                    str(request.time_offset),
                    timeout=self.timeout_per_request
                )
                logger.info(f"🔍 STK位置获取完成: {request.satellite_id}, 结果: {position_data is not None}")

                # 缓存结果（如果启用且获取成功）
                if position_data and self.enable_cache:
                    self._cache_position(cache_key, position_data)
                    logger.info(f"💾 位置数据已缓存: {request.satellite_id}")

                success = position_data is not None
                processing_time = time.time() - start_time

                if success:
                    logger.info(f"✅ 位置获取成功: {request.satellite_id} (耗时: {processing_time:.3f}s)")
                else:
                    logger.error(f"❌ 位置获取失败: {request.satellite_id} (耗时: {processing_time:.3f}s)")

                results.append(PositionResult(
                    request=request,
                    position_data=position_data,
                    success=success,
                    processing_time=processing_time
                ))

            except Exception as e:
                logger.error(f"❌ 处理请求异常: {request.satellite_id} @ {request.time_offset}s - {e}")
                import traceback
                logger.error(f"❌ 异常详情: {traceback.format_exc()}")
                results.append(PositionResult(
                    request=request,
                    position_data=None,
                    success=False,
                    error=str(e),
                    processing_time=time.time() - start_time
                ))

        return results
    
    def _get_position_sync(self, satellite_id: str, time_offset: float) -> Optional[Dict[str, Any]]:
        """同步获取位置数据（线程安全）"""
        try:
            # 在多线程环境中初始化COM
            import pythoncom
            pythoncom.CoInitialize()

            try:
                # 在每个线程中重新获取STK应用程序对象
                import win32com.client
                stk_app = win32com.client.Dispatch("STK12.Application")

                # 获取当前场景
                scenario = stk_app.ActiveScenario
                if not scenario:
                    logger.warning(f"线程中无法获取活动场景")
                    return None

                # 查找卫星
                satellite = None
                target_name = satellite_id
                if satellite_id.startswith("Satellite/"):
                    target_name = satellite_id.split("/", 1)[1]

                for i in range(scenario.Children.Count):
                    child = scenario.Children.Item(i)
                    if (getattr(child, 'ClassName', None) == 'Satellite' and
                        getattr(child, 'InstanceName', None) == target_name):
                        satellite = child
                        break

                if not satellite:
                    logger.warning(f"线程中未找到卫星: {satellite_id}")
                    return None

                # 计算目标时间
                from src.utils.time_manager import get_time_manager
                from datetime import timedelta
                time_manager = get_time_manager()
                target_time = time_manager.start_time + timedelta(seconds=float(time_offset))
                stk_time = target_time.strftime("%d %b %Y %H:%M:%S.000")

                # 获取位置数据
                try:
                    dp = satellite.DataProviders.Item("Cartesian Position")
                    result = dp.Exec(stk_time, stk_time)

                    if result and result.DataSets.Count > 0:
                        dataset = result.DataSets.Item(0)
                        if dataset.RowCount > 0:
                            x = float(dataset.GetValue(0, 1))
                            y = float(dataset.GetValue(0, 2))
                            z = float(dataset.GetValue(0, 3))
                            return {
                                'time': stk_time,
                                'x': x,
                                'y': y,
                                'z': z
                            }
                except Exception as pos_e:
                    logger.debug(f"Cartesian Position失败: {pos_e}")

                    # 尝试LLA Position
                    try:
                        dp = satellite.DataProviders.Item("LLA Position")
                        result = dp.Exec(stk_time, stk_time)

                        if result and result.DataSets.Count > 0:
                            dataset = result.DataSets.Item(0)
                            if dataset.RowCount > 0:
                                lat = float(dataset.GetValue(0, 1))
                                lon = float(dataset.GetValue(0, 2))
                                alt = float(dataset.GetValue(0, 3))
                                return {
                                    'time': stk_time,
                                    'latitude': lat,
                                    'longitude': lon,
                                    'altitude': alt
                                }
                    except Exception as lla_e:
                        logger.debug(f"LLA Position失败: {lla_e}")

                return None

            finally:
                # 清理COM
                pythoncom.CoUninitialize()

        except Exception as e:
            logger.warning(f"位置获取失败 {satellite_id}: {e}")
            return None
    
    def _get_cached_position(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """线程安全的缓存获取"""
        if not self.enable_cache:
            logger.debug(f"🚫 缓存已禁用，跳过缓存查询: {cache_key}")
            return None

        with self._cache_lock:
            cached_data = self._position_cache.get(cache_key)
            if cached_data:
                logger.debug(f"💾 缓存命中: {cache_key}")
            else:
                logger.debug(f"💾 缓存未命中: {cache_key}")
            return cached_data

    def _cache_position(self, cache_key: str, position_data: Dict[str, Any]):
        """线程安全的缓存存储"""
        if not self.enable_cache:
            logger.debug(f"🚫 缓存已禁用，跳过缓存存储: {cache_key}")
            return

        with self._cache_lock:
            self._position_cache[cache_key] = position_data
            logger.debug(f"💾 数据已缓存: {cache_key}")
    
    def clear_cache(self):
        """清空位置缓存"""
        with self._cache_lock:
            self._position_cache.clear()
        logger.info("🧹 位置缓存已清空")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        stats = self.stats.copy()
        
        if stats["total_requests"] > 0:
            stats["success_rate"] = stats["successful_requests"] / stats["total_requests"] * 100
            stats["average_time_per_request"] = stats["parallel_time"] / stats["total_requests"]
        else:
            stats["success_rate"] = 0.0
            stats["average_time_per_request"] = 0.0
        
        stats["cache_hit_rate"] = (stats["cache_hits"] / stats["total_requests"] * 100) if stats["total_requests"] > 0 else 0.0
        stats["cache_size"] = len(self._position_cache)
        
        return stats
    
    def reset_stats(self):
        """重置性能统计"""
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "parallel_time": 0.0,
            "cache_hits": 0,
            "batch_count": 0
        }
