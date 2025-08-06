#!/usr/bin/env python3
"""
可见性计算器重构版本
基于运行日志分析，保留实际使用的方法，删除无效分支
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class VisibilityCalculator:
    """可见性计算器重构版本 - 基于实际使用情况优化"""
    
    def __init__(self, stk_manager):
        """初始化可见性计算器"""
        self.stk_manager = stk_manager

        # 从配置获取参数
        from src.utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()

        self.wait_times = stk_config.get("wait_times", {"access_computation": 1.0})

        # 约束类型 (基于实际使用)
        self.constraint_types = {
            "elevation_angle": 1,
            "range": 34,
            "lighting": 15
        }

        # 对象缓存 - 避免重复查找STK对象
        self._satellite_cache = {}
        self._missile_cache = {}
        self._sensor_cache = {}
        self._cache_initialized = False

        logger.info("👁️ 可见性计算器初始化完成，对象缓存已准备")

    def _initialize_object_cache(self):
        """
        初始化对象缓存 - 一次性建立所有STK对象的索引
        这样避免每次计算时都要遍历场景对象
        """
        if self._cache_initialized:
            return

        try:
            logger.info("🔄 开始初始化STK对象缓存...")
            scenario = self.stk_manager.scenario

            # 清空缓存
            self._satellite_cache.clear()
            self._missile_cache.clear()
            self._sensor_cache.clear()

            # 一次性遍历所有场景对象
            total_objects = scenario.Children.Count
            satellites_found = 0
            missiles_found = 0

            for i in range(total_objects):
                try:
                    child = scenario.Children.Item(i)
                    child_class = getattr(child, 'ClassName', None)
                    child_name = getattr(child, 'InstanceName', None)

                    if child_class == 'Satellite' and child_name:
                        self._satellite_cache[child_name] = child
                        satellites_found += 1

                        # 同时缓存卫星的传感器
                        sensor = self._find_satellite_sensor_direct(child)
                        if sensor:
                            self._sensor_cache[child_name] = sensor

                    elif child_class == 'Missile' and child_name:
                        self._missile_cache[child_name] = child
                        missiles_found += 1

                except Exception as e:
                    logger.debug(f"跳过对象 {i}: {e}")
                    continue

            self._cache_initialized = True
            logger.info(f"✅ STK对象缓存初始化完成:")
            logger.info(f"   🛰️ 卫星: {satellites_found} 个")
            logger.info(f"   🚀 导弹: {missiles_found} 个")
            logger.info(f"   📡 传感器: {len(self._sensor_cache)} 个")

        except Exception as e:
            logger.error(f"❌ 对象缓存初始化失败: {e}")
            self._cache_initialized = False

    def calculate_access(self, satellite_id: str, missile_id: str,
                        constraints: Optional[Dict] = None) -> Dict[str, Any]:
        """
        计算可见性 - 重构版本，基于实际使用的STK API方法
        """
        try:
            logger.info(f"🔍 开始计算可见性: {satellite_id} -> {missile_id}")

            # 确保对象缓存已初始化
            if not self._cache_initialized:
                self._initialize_object_cache()

            # 从缓存中快速获取对象
            satellite = self._get_satellite_from_cache(satellite_id)
            missile = self._get_missile_from_cache(missile_id)
            
            if not satellite:
                logger.error(f"❌ 卫星 {satellite_id} 不存在")
                return self._create_error_result(f"卫星 {satellite_id} 不存在")
            
            if not missile:
                logger.error(f"❌ 导弹 {missile_id} 不存在")
                return self._create_error_result(f"导弹 {missile_id} 不存在")
            
            # 使用STK API计算访问 (日志显示成功使用)
            access_result = self._compute_stk_access_optimized(satellite, missile, constraints)
            
            if access_result['success']:
                logger.info(f"✅ 可见性计算成功: {satellite_id} -> {missile_id}")
                return access_result
            else:
                logger.warning(f"⚠️ 可见性计算失败: {access_result.get('error', '未知错误')}")
                return access_result
            
        except Exception as e:
            logger.error(f"❌ 可见性计算异常: {e}")
            return self._create_error_result(str(e))

    def calculate_satellite_to_missile_access(self, satellite_id: str, missile_id: str) -> Dict[str, Any]:
        """计算卫星到导弹的访问 - 兼容性方法，调用calculate_access"""
        try:
            logger.info(f"🔍 计算可见性: {satellite_id} -> {missile_id}")

            # 调用主要的计算方法
            access_result = self.calculate_access(satellite_id, missile_id)

            if access_result.get('success'):
                logger.info(f"   ✅ 可见性计算成功: {satellite_id}")
                return {
                    "satellite_id": satellite_id,
                    "missile_id": missile_id,
                    "success": True,
                    "has_access": access_result.get("has_access", False),
                    "access_intervals": access_result.get("intervals", []),  # 修复字段名
                    "total_intervals": access_result.get("interval_count", 0)
                }
            else:
                logger.warning(f"   ❌ 可见性计算失败: {satellite_id}")
                return {
                    "satellite_id": satellite_id,
                    "missile_id": missile_id,
                    "success": False,
                    "has_access": False,
                    "access_intervals": [],
                    "total_intervals": 0
                }

        except Exception as e:
            logger.error(f"❌ 可见性计算异常 {satellite_id}: {e}")
            return {
                "satellite_id": satellite_id,
                "missile_id": missile_id,
                "success": False,
                "error": str(e),
                "has_access": False,
                "access_intervals": [],
                "total_intervals": 0
            }
    
    def _compute_stk_access_optimized(self, satellite, missile, constraints: Optional[Dict]) -> Dict[str, Any]:
        """
        使用STK API计算访问 - 基于实际成功的方法
        """
        try:
            # 从缓存获取卫星的传感器 (如果存在)
            satellite_name = getattr(satellite, 'InstanceName', None)
            sensor = self._sensor_cache.get(satellite_name) if satellite_name else None

            if sensor:
                logger.info("🔭 使用传感器计算访问")
                from_object = sensor
            else:
                logger.info("🛰️ 使用卫星本体计算访问")
                from_object = satellite
            
            # 计算访问 (日志显示成功使用)
            access = from_object.GetAccessToObject(missile)
            logger.info("✅ STK访问对象创建成功")
            
            # # 设置约束 (如果提供) 暂时停止使用约束（linghuding）
            # if constraints:
            #     self._apply_access_constraints_optimized(access, constraints)
            
            # 计算访问
            access.ComputeAccess()
            logger.info("✅ 访问计算完成")
            
            # 获取访问间隔 (日志显示成功解析)
            intervals = self._extract_access_intervals_optimized(access)
            
            # 计算总访问时间
            total_access_time = sum(interval['duration'] for interval in intervals)
            
            result = {
                'success': True,
                'has_access': len(intervals) > 0,
                'intervals': intervals,
                'access_intervals': intervals,  # 添加兼容性字段
                'total_access_time': total_access_time,
                'interval_count': len(intervals)
            }
            
            logger.info(f"✅ 访问结果: {len(intervals)}个间隔, 总时长{total_access_time:.1f}秒")
            return result
            
        except Exception as e:
            logger.error(f"❌ STK访问计算失败: {e}")
            return self._create_error_result(str(e))

    def _get_satellite_from_cache(self, satellite_id: str):
        """从缓存中快速获取卫星对象"""
        satellite = self._satellite_cache.get(satellite_id)
        if satellite:
            logger.debug(f"✅ 从缓存获取卫星: {satellite_id}")
            return satellite
        else:
            logger.warning(f"⚠️ 缓存中未找到卫星: {satellite_id}")
            # 尝试重新初始化缓存
            self._cache_initialized = False
            self._initialize_object_cache()
            return self._satellite_cache.get(satellite_id)

    def _get_missile_from_cache(self, missile_id: str):
        """从缓存中快速获取导弹对象"""
        missile = self._missile_cache.get(missile_id)
        if missile:
            logger.debug(f"✅ 从缓存获取导弹: {missile_id}")
            return missile
        else:
            logger.warning(f"⚠️ 缓存中未找到导弹: {missile_id}")
            # 尝试重新初始化缓存
            self._cache_initialized = False
            self._initialize_object_cache()
            return self._missile_cache.get(missile_id)

    def _find_satellite_sensor_direct(self, satellite):
        """直接查找卫星的传感器（用于缓存初始化）"""
        try:
            for i in range(satellite.Children.Count):
                child = satellite.Children.Item(i)
                if getattr(child, 'ClassName', None) == 'Sensor':
                    return child
            return None
        except Exception:
            return None

    def _find_satellite(self, satellite_id: str):
        """查找卫星对象"""
        try:
            scenario = self.stk_manager.scenario
            logger.info(f"🔍 查找卫星: {satellite_id}")

            # 列出所有卫星对象进行调试
            satellites_found = []
            for i in range(scenario.Children.Count):
                child = scenario.Children.Item(i)
                child_class = getattr(child, 'ClassName', None)
                child_name = getattr(child, 'InstanceName', None)

                if child_class == 'Satellite':
                    satellites_found.append(child_name)
                    if child_name == satellite_id:
                        logger.info(f"✅ 找到匹配的卫星: {satellite_id}")
                        return child

            logger.warning(f"⚠️ 未找到卫星 {satellite_id}，可用卫星: {satellites_found}")
            return None
        except Exception as e:
            logger.error(f"❌ 查找卫星失败: {e}")
            return None
    
    def _find_missile(self, missile_id: str):
        """查找导弹对象"""
        try:
            scenario = self.stk_manager.scenario
            logger.info(f"🔍 查找导弹: {missile_id}")

            # 列出所有导弹对象进行调试
            missiles_found = []
            for i in range(scenario.Children.Count):
                child = scenario.Children.Item(i)
                child_class = getattr(child, 'ClassName', None)
                child_name = getattr(child, 'InstanceName', None)

                if child_class == 'Missile':
                    missiles_found.append(child_name)
                    if child_name == missile_id:
                        logger.info(f"✅ 找到匹配的导弹: {missile_id}")
                        return child

            logger.warning(f"⚠️ 未找到导弹 {missile_id}，可用导弹: {missiles_found}")
            return None
        except Exception as e:
            logger.error(f"❌ 查找导弹失败: {e}")
            return None
    
    def _find_satellite_sensor(self, satellite):
        """查找卫星的传感器"""
        try:
            for i in range(satellite.Children.Count):
                child = satellite.Children.Item(i)
                if getattr(child, 'ClassName', None) == 'Sensor':
                    logger.info(f"🔭 找到传感器: {getattr(child, 'InstanceName', 'Unknown')}")
                    return child
            return None
        except Exception as e:
            logger.warning(f"⚠️ 查找传感器失败: {e}")
            return None
    
    def _apply_access_constraints_optimized(self, access, constraints: Dict):
        """
        应用访问约束 - 基于实际使用的方法
        """
        try:
            access_constraints = access.AccessConstraints
            
            # 高度角约束
            if 'min_elevation_angle' in constraints:
                min_elevation = constraints['min_elevation_angle']
                logger.info(f"🔧 设置最小高度角约束: {min_elevation}°")
                
                elev_constraint = access_constraints.AddConstraint(self.constraint_types["elevation_angle"])
                elev_constraint.EnableMin = True
                elev_constraint.Min = min_elevation
                logger.info("✅ 高度角约束设置成功")
            
            # 距离约束
            if 'min_range_km' in constraints and 'max_range_km' in constraints:
                min_range = constraints['min_range_km']
                max_range = constraints['max_range_km']
                logger.info(f"🔧 设置距离约束: {min_range}-{max_range} km")
                
                range_constraint = access_constraints.AddConstraint(self.constraint_types["range"])
                range_constraint.EnableMin = True
                range_constraint.EnableMax = True
                range_constraint.Min = min_range
                range_constraint.Max = max_range
                logger.info("✅ 距离约束设置成功")
            
            # 光照约束
            if 'lighting_condition' in constraints:
                lighting = constraints['lighting_condition']
                if lighting in ['sunlit', 'penumbra', 'umbra']:
                    logger.info(f"🔧 设置光照约束: {lighting}")
                    
                    lighting_constraint = access_constraints.AddConstraint(self.constraint_types["lighting"])
                    # 根据光照条件设置具体参数
                    if lighting == 'sunlit':
                        lighting_constraint.Condition = 0  # eSunlit
                    elif lighting == 'penumbra':
                        lighting_constraint.Condition = 1  # ePenumbra
                    elif lighting == 'umbra':
                        lighting_constraint.Condition = 2  # eUmbra
                    
                    logger.info("✅ 光照约束设置成功")
            
        except Exception as e:
            logger.warning(f"⚠️ 约束设置失败: {e}")
    
    def _extract_access_intervals_optimized(self, access) -> List[Dict[str, Any]]:
        """
        提取访问间隔 - 基于实际成功的解析方法
        """
        intervals = []
        
        try:
            # 获取访问间隔数据 (日志显示成功使用)
            access_intervals = access.ComputedAccessIntervalTimes
            
            if access_intervals and access_intervals.Count > 0:
                logger.info(f"🔍 找到 {access_intervals.Count} 个访问间隔")
                
                # 基于STK官方文档: 使用ToArray方法获取间隔数据
                computed_intervals = access_intervals.ToArray(0, -1)
                logger.info(f"🔍 成功获取访问间隔数组，长度: {len(computed_intervals)}")

                # 解析间隔数据 - STK返回的是元组的元组格式
                for i, interval_tuple in enumerate(computed_intervals):
                    try:
                        if isinstance(interval_tuple, tuple) and len(interval_tuple) >= 2:
                            start_time = str(interval_tuple[0])
                            end_time = str(interval_tuple[1])
                        else:
                            # 备用解析方式：如果是平坦数组
                            if i * 2 + 1 < len(computed_intervals):
                                start_time = str(computed_intervals[i * 2])
                                end_time = str(computed_intervals[i * 2 + 1])
                            else:
                                continue

                        # 计算持续时间 (秒)
                        duration = self._calculate_duration_seconds(start_time, end_time)

                        interval_data = {
                            'start': start_time,
                            'end': end_time,
                            'duration': duration,
                            'start_formatted': self._format_time_string(start_time),
                            'end_formatted': self._format_time_string(end_time)
                        }

                        intervals.append(interval_data)
                        logger.info(f"📅 间隔 {i+1}: {interval_data['start_formatted']} - {interval_data['end_formatted']} ({duration:.1f}s)")

                    except Exception as interval_error:
                        logger.warning(f"⚠️ 解析间隔 {i+1} 失败: {interval_error}")
                        continue
            else:
                logger.info("🚫 没有找到访问间隔")
            
        except Exception as e:
            logger.error(f"❌ 提取访问间隔失败: {e}")
        
        return intervals
    
    def _calculate_duration_seconds(self, start_time: str, end_time: str) -> float:
        """计算持续时间（秒）"""
        try:
            from datetime import datetime

            # 解析STK时间格式: "26 Jul 2025 00:08:27.858"
            def parse_stk_time(time_str):
                try:
                    # 移除微秒部分，只保留到秒
                    time_clean = time_str.split('.')[0]
                    return datetime.strptime(time_clean, "%d %b %Y %H:%M:%S")
                except:
                    # 备用解析方法
                    try:
                        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    except:
                        return None

            start_dt = parse_stk_time(start_time)
            end_dt = parse_stk_time(end_time)

            if start_dt and end_dt:
                duration = (end_dt - start_dt).total_seconds()
                logger.debug(f"   时间差计算: {start_time} -> {end_time} = {duration:.1f}秒")
                return duration
            else:
                logger.warning(f"⚠️ 无法解析时间: {start_time} -> {end_time}")
                return 600.0  # 默认值

        except Exception as e:
            logger.warning(f"⚠️ 时间差计算失败: {e}")
            return 600.0  # 默认值
    
    def _format_time_string(self, time_str: str) -> str:
        """格式化时间字符串"""
        try:
            # 简化的时间格式化
            return time_str
        except Exception as e:
            logger.warning(f"⚠️ 时间格式化失败: {e}")
            return time_str
    
    def _create_error_result(self, error_message: str) -> Dict[str, Any]:
        """创建错误结果"""
        return {
            'success': False,
            'has_access': False,
            'intervals': [],
            'total_access_time': 0.0,
            'interval_count': 0,
            'error': error_message
        }
    
    def get_access_summary(self, satellite_id: str, missile_id: str) -> Dict[str, Any]:
        """
        获取访问摘要 - 快速检查是否有访问
        """
        try:
            result = self.calculate_access(satellite_id, missile_id)
            
            summary = {
                'satellite_id': satellite_id,
                'missile_id': missile_id,
                'has_access': result.get('has_access', False),
                'interval_count': result.get('interval_count', 0),
                'total_access_time': result.get('total_access_time', 0.0),
                'success': result.get('success', False)
            }
            
            if result.get('error'):
                summary['error'] = result['error']
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ 获取访问摘要失败: {e}")
            return {
                'satellite_id': satellite_id,
                'missile_id': missile_id,
                'has_access': False,
                'success': False,
                'error': str(e)
            }
    
    def batch_calculate_access(self, satellite_ids: List[str], missile_ids: List[str], 
                             constraints: Optional[Dict] = None) -> Dict[str, Dict[str, Any]]:
        """
        批量计算访问 - 优化的批处理方法
        """
        results = {}
        
        try:
            total_combinations = len(satellite_ids) * len(missile_ids)
            logger.info(f"🔄 开始批量计算访问: {total_combinations} 个组合")
            
            for satellite_id in satellite_ids:
                for missile_id in missile_ids:
                    key = f"{satellite_id}->{missile_id}"
                    
                    try:
                        result = self.calculate_access(satellite_id, missile_id, constraints)
                        results[key] = result
                        
                        # 添加延迟避免STK过载
                        time.sleep(0.1)
                        
                    except Exception as e:
                        logger.error(f"❌ 批量计算失败 {key}: {e}")
                        results[key] = self._create_error_result(str(e))
            
            # 统计结果
            successful_count = sum(1 for r in results.values() if r.get('success', False))
            access_count = sum(1 for r in results.values() if r.get('has_access', False))
            
            logger.info(f"✅ 批量计算完成: {successful_count}/{total_combinations} 成功, {access_count} 有访问")
            
        except Exception as e:
            logger.error(f"❌ 批量计算异常: {e}")
        
        return results
