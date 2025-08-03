#!/usr/bin/env python3
"""
可见性计算器模块 - 清理版
负责卫星-导弹可见性计算，只保留真正使用的方法
基于实际运行验证，删除了所有未使用的方法
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class VisibilityCalculator:
    """可见性计算器 - 清理版，只保留核心功能"""
    
    def __init__(self, stk_manager):
        """初始化可见性计算器"""
        self.stk_manager = stk_manager

        # 获取配置
        from src.utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        self.visibility_config = config_manager.get_visibility_config()

        logger.info("🔍 可见性计算器初始化")
    
    def calculate_satellite_to_missile_access(self, satellite_id: str, missile_id: str) -> Dict[str, Any]:
        """计算卫星到导弹的访问 - 唯一被使用的公共方法"""
        try:
            logger.info(f"🔍 计算可见性: {satellite_id} -> {missile_id}")
            
            # 使用STK计算访问
            access_result = self._compute_stk_access(satellite_id, missile_id)
            
            if access_result:
                logger.info(f"   ✅ 可见性计算成功: {satellite_id}")
                return {
                    "satellite_id": satellite_id,
                    "missile_id": missile_id,
                    "success": True,
                    "has_access": access_result["has_access"],
                    "access_intervals": access_result["intervals"],
                    "total_intervals": len(access_result["intervals"])
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
    
    def _compute_stk_access(self, satellite_id: str, missile_id: str) -> Optional[Dict[str, Any]]:
        """使用STK真正的Access计算 - 基于STK官方文档"""
        try:
            logger.info(f"   🔍 使用STK API计算访问: {satellite_id} -> {missile_id}")

            if not self.stk_manager or not self.stk_manager.scenario:
                logger.error("STK管理器或场景不可用，无法计算可见性")
                return self._handle_stk_access_failure()

            # 1. 获取STK根对象和场景
            root = self.stk_manager.root
            scenario = self.stk_manager.scenario

            # 2. 基于STK官方文档: 使用对象路径获取访问
            satellite_path = f"Satellite/{satellite_id}"
            missile_path = f"Missile/{missile_id}"

            try:
                # 基于STK官方代码: Get access by object path
                satellite = root.GetObjectFromPath(satellite_path)
                access = satellite.GetAccess(missile_path)
                logger.debug(f"   ✅ 创建访问对象成功: {satellite_path} -> {missile_path}")
            except Exception as e:
                logger.error(f"   ❌ 创建访问对象失败: {e}")
                return self._handle_stk_access_failure()

            # 3. 基于STK官方文档: 配置访问约束
            self._configure_stk_access_constraints(access)

            # 4. 基于STK官方文档: Compute access
            try:
                access.ComputeAccess()
                logger.debug(f"   ✅ 访问计算完成")
            except Exception as e:
                logger.error(f"   ❌ 访问计算失败: {e}")
                return self._handle_stk_access_failure()

            # 5. 基于STK官方文档: Get and display the Computed Access Intervals
            access_intervals = self._extract_stk_access_intervals(access)

            # 6. 构建返回数据
            access_data = {
                "has_access": len(access_intervals) > 0,
                "intervals": access_intervals
            }

            logger.info(f"   ✅ STK访问计算完成: {satellite_id}, 有访问: {access_data['has_access']}, 间隔数: {len(access_intervals)}")
            return access_data

        except Exception as e:
            logger.error(f"❌ STK访问计算异常: {e}")
            return self._handle_stk_access_failure()

    def _configure_stk_access_constraints(self, access):
        """配置STK访问约束 - 基于STK官方文档"""
        try:
            # 基于STK官方代码: Get handle to the object access constraints
            access_constraints = access.AccessConstraints

            # 基于STK官方代码: Add and configure an altitude access constraint
            altitude_constraint = access_constraints.AddConstraint(2)  # eCstrAltitude
            altitude_constraint.EnableMin = True
            altitude_constraint.Min = self.visibility_config["access_constraints"]["min_altitude"]

            # 基于STK官方代码: Add and configure a sun elevation angle access constraint
            sun_elevation = access_constraints.AddConstraint(58)  # eCstrSunElevationAngle
            sun_elevation.EnableMin = True
            sun_elevation.Min = self.visibility_config["access_constraints"]["sun_elevation_min"]

            logger.debug("   ✅ STK访问约束配置完成")

        except Exception as e:
            logger.debug(f"   ⚠️ STK访问约束配置失败: {e}")

    def _extract_stk_access_intervals(self, access) -> List[Dict[str, str]]:
        """提取STK访问间隔 - 基于STK官方文档"""
        try:
            intervals = []

            # 基于STK官方代码: Compute and extract access interval times
            interval_collection = access.ComputedAccessIntervalTimes

            if interval_collection and interval_collection.Count > 0:
                logger.debug(f"   📊 找到 {interval_collection.Count} 个访问间隔")

                # 基于STK官方代码: Set the intervals to use to the Computed Access Intervals
                computed_intervals = interval_collection.ToArray(0, -1)

                # 解析间隔数据 - STK返回的是元组的元组格式
                for interval_tuple in computed_intervals:
                    if isinstance(interval_tuple, tuple) and len(interval_tuple) >= 2:
                        start_time = interval_tuple[0]
                        end_time = interval_tuple[1]

                        intervals.append({
                            "start": str(start_time),
                            "stop": str(end_time)
                        })
                    elif len(computed_intervals) >= 2:
                        # 备用解析方式：如果是平坦数组
                        for i in range(0, len(computed_intervals), 2):
                            if i + 1 < len(computed_intervals):
                                start_time = computed_intervals[i]
                                end_time = computed_intervals[i + 1]

                                intervals.append({
                                    "start": str(start_time),
                                    "stop": str(end_time)
                                })
                        break

                logger.debug(f"   ✅ 成功提取 {len(intervals)} 个访问间隔")
            else:
                logger.debug("   📊 没有找到访问间隔")

            return intervals

        except Exception as e:
            logger.debug(f"   ❌ STK访问间隔提取失败: {e}")
            return []

    def _handle_stk_access_failure(self) -> Dict[str, Any]:
        """处理STK访问计算失败的情况"""
        logger.error("STK访问计算失败，无法获取真实可见性数据")
        return {
            "has_access": False,
            "intervals": [],
            "error": "STK访问计算失败",
            "data_source": "error"
        }
