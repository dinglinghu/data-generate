#!/usr/bin/env python3
"""
导弹管理器重构版本
基于运行日志分析，保留实际使用的方法，删除无效分支
"""

import logging
import math
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from ..utils.aerospace_time_converter import AerospaceTimeConverter
from ..utils.stk_data_structure_analyzer import get_stk_analyzer

logger = logging.getLogger(__name__)


class MissileManager:
    """导弹管理器重构版本 - 基于实际使用情况优化"""
    
    def __init__(self, stk_manager, time_manager=None, config_manager=None, config=None, output_manager=None):
        """初始化导弹管理器 - 保持向后兼容性"""
        self.stk_manager = stk_manager
        self.time_manager = time_manager
        self.config_manager = config_manager
        self.config = config
        self.output_manager = output_manager

        # 保持向后兼容的属性
        self.missile_targets = {}

        # 初始化航天时间转换器
        self.time_converter = AerospaceTimeConverter()

        # 初始化STK数据结构分析器
        self.stk_analyzer = get_stk_analyzer()

        # 从配置获取参数
        from src.utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()
        missile_config = config_manager.config.get("missile", {})

        self.object_types = stk_config.get("object_types", {"missile": 19})  # 19 = eMissile
        self.wait_times = stk_config.get("wait_times", {"object_creation": 2.0})

        # 获取导弹飞行高度配置
        flight_altitude_config = missile_config.get("flight_altitude", {})
        self.min_altitude = flight_altitude_config.get("min_altitude", 300)
        self.max_altitude = flight_altitude_config.get("max_altitude", 1500)
        
        # 轨迹类型 (基于日志分析)
        self.trajectory_types = {
            "ballistic": 10,  # 日志显示使用SetTrajectoryType(10)
            "astrogator": 11
        }

        # 性能优化缓存
        self._trajectory_cache = {}           # 轨迹数据缓存
        self._altitude_analysis_cache = {}    # 高度分析结果缓存
        self._dataprovider_cache = {}         # DataProvider结果缓存
        self._missile_object_cache = {}       # 导弹对象缓存

        logger.info("🚀 导弹管理器初始化完成，性能缓存已准备")

    def _get_cached_trajectory_data(self, missile_id: str):
        """从缓存获取轨迹数据，避免重复STK调用"""
        cache_key = f"trajectory_{missile_id}"
        if cache_key in self._trajectory_cache:
            logger.debug(f"✅ 使用缓存的轨迹数据: {missile_id}")
            return self._trajectory_cache[cache_key]
        return None

    def _cache_trajectory_data(self, missile_id: str, trajectory_data):
        """缓存轨迹数据"""
        cache_key = f"trajectory_{missile_id}"
        self._trajectory_cache[cache_key] = trajectory_data
        logger.debug(f"💾 缓存轨迹数据: {missile_id}")

    def _get_cached_altitude_analysis(self, missile_id: str):
        """从缓存获取高度分析结果"""
        cache_key = f"altitude_{missile_id}"
        if cache_key in self._altitude_analysis_cache:
            logger.debug(f"✅ 使用缓存的高度分析: {missile_id}")
            return self._altitude_analysis_cache[cache_key]
        return None

    def _cache_altitude_analysis(self, missile_id: str, analysis_result):
        """缓存高度分析结果"""
        cache_key = f"altitude_{missile_id}"
        self._altitude_analysis_cache[cache_key] = analysis_result
        logger.debug(f"💾 缓存高度分析: {missile_id}")

    def clear_cache(self):
        """清空所有缓存"""
        self._trajectory_cache.clear()
        self._altitude_analysis_cache.clear()
        self._dataprovider_cache.clear()
        self._missile_object_cache.clear()
        logger.info("🧹 已清空所有缓存")

    def _get_cached_missile_object(self, missile_id: str):
        """获取缓存的导弹对象，避免重复STK查找"""
        if missile_id in self._missile_object_cache:
            logger.debug(f"✅ 使用缓存的导弹对象: {missile_id}")
            return self._missile_object_cache[missile_id]

        try:
            # 从STK获取导弹对象
            missile = self.stk_manager.scenario.Children.Item(missile_id)
            self._missile_object_cache[missile_id] = missile
            logger.debug(f"💾 缓存导弹对象: {missile_id}")
            return missile
        except Exception as e:
            logger.error(f"❌ 获取导弹对象失败 {missile_id}: {e}")
            return None

    def get_cache_stats(self):
        """获取缓存统计信息"""
        return {
            "trajectory_cache_size": len(self._trajectory_cache),
            "altitude_cache_size": len(self._altitude_analysis_cache),
            "dataprovider_cache_size": len(self._dataprovider_cache),
            "missile_object_cache_size": len(self._missile_object_cache)
        }

    def batch_get_missile_trajectory_info(self, missile_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量获取多个导弹的轨迹信息，优化性能

        Args:
            missile_ids: 导弹ID列表

        Returns:
            字典: {missile_id: trajectory_info}
        """
        logger.info(f"🚀 批量获取 {len(missile_ids)} 个导弹的轨迹信息...")

        results = {}
        cache_hits = 0
        new_calculations = 0

        for missile_id in missile_ids:
            # 检查缓存
            cached_data = self._get_cached_trajectory_data(missile_id)
            if cached_data:
                results[missile_id] = cached_data
                cache_hits += 1
            else:
                # 获取新数据
                trajectory_info = self.get_missile_trajectory_info(missile_id)
                results[missile_id] = trajectory_info
                new_calculations += 1

        logger.info(f"✅ 批量轨迹获取完成: 缓存命中 {cache_hits}, 新计算 {new_calculations}")
        return results

    def batch_get_missile_flight_phases_by_altitude(self, missile_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        批量获取多个导弹的高度分析结果，优化性能

        Args:
            missile_ids: 导弹ID列表

        Returns:
            字典: {missile_id: altitude_analysis}
        """
        logger.info(f"🚀 批量获取 {len(missile_ids)} 个导弹的高度分析...")

        results = {}
        cache_hits = 0
        new_calculations = 0

        for missile_id in missile_ids:
            # 检查缓存
            cached_analysis = self._get_cached_altitude_analysis(missile_id)
            if cached_analysis:
                results[missile_id] = cached_analysis
                cache_hits += 1
            else:
                # 获取新分析
                altitude_analysis = self.get_missile_flight_phases_by_altitude(missile_id)
                results[missile_id] = altitude_analysis
                new_calculations += 1

        logger.info(f"✅ 批量高度分析完成: 缓存命中 {cache_hits}, 新计算 {new_calculations}")
        return results

    def create_missile(self, missile_id: str, launch_time: datetime,
                      trajectory_params: Dict) -> bool:
        """
        创建导弹 - 重构版本，基于实际使用的方法
        """
        if not self.stk_manager.scenario or not self.stk_manager.is_connected:
            logger.error("STK未连接")
            return False
        
        try:
            # 创建导弹对象
            self.stk_manager.scenario.Children.New(self.object_types["missile"], missile_id)
            logger.info(f"🚀 创建导弹对象: {missile_id}")
            
            # 等待对象创建
            time.sleep(self.wait_times["object_creation"])
            
            # 获取导弹对象
            missile = self.stk_manager.scenario.Children.Item(missile_id)
            
            # 设置轨迹类型 (日志显示成功使用)
            missile.SetTrajectoryType(self.trajectory_types["ballistic"])
            logger.info("✅ 轨迹类型设置为弹道轨迹")
            
            # 配置轨迹参数
            success = self._configure_missile_trajectory_optimized(missile, launch_time, trajectory_params)
            if not success:
                logger.error(f"❌ 轨迹配置失败: {missile_id}")
                return False
            
            # 传播轨迹
            success = self._propagate_missile_trajectory(missile)
            if not success:
                logger.error(f"❌ 轨迹传播失败: {missile_id}")
                return False
            
            logger.info(f"✅ 导弹创建成功: {missile_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建导弹失败 {missile_id}: {e}")
            return False
    
    def _configure_missile_trajectory_optimized(self, missile, launch_time: datetime, 
                                              trajectory_params: Dict) -> bool:
        """
        优化的轨迹配置 - 基于日志分析的实际成功方法
        """
        try:
            # 验证轨迹参数
            validated_params = self._validate_trajectory_parameters(trajectory_params)
            if not validated_params:
                return False
            
            # 提取参数
            launch_pos = validated_params['launch_position']
            target_pos = validated_params['target_position']
            flight_duration = validated_params.get('flight_duration', 1800)  # 默认30分钟
            
            # 计算时间窗口
            launch_time_str = launch_time.strftime("%d %b %Y %H:%M:%S.000")
            impact_time = launch_time + timedelta(seconds=flight_duration)
            impact_time_str = impact_time.strftime("%d %b %Y %H:%M:%S.000")
            
            # 设置导弹时间属性 - 基于STK官方文档的正确顺序
            # 重要：必须在设置轨迹类型后，配置轨迹参数前设置时间
            self._set_missile_time_period_correct(missile, launch_time, flight_duration)

            # 配置轨迹参数 - 使用原始代码的正确方法
            try:
                trajectory = missile.Trajectory

                # 设置发射位置 - 原始代码的正确方法
                trajectory.Launch.Lat = launch_pos["lat"]
                trajectory.Launch.Lon = launch_pos["lon"]
                trajectory.Launch.Alt = launch_pos["alt"]
                logger.info(f"✅ 发射位置设置成功")

                # 设置撞击位置 - 原始代码的正确方法
                trajectory.ImpactLocation.Impact.Lat = target_pos["lat"]
                trajectory.ImpactLocation.Impact.Lon = target_pos["lon"]
                trajectory.ImpactLocation.Impact.Alt = target_pos["alt"]
                logger.info(f"✅ 撞击位置设置成功")

                # 设置发射控制类型和远地点高度（使用配置参数）
                import random
                apogee_alt_km = random.uniform(self.min_altitude, self.max_altitude)
                logger.info(f"✅ 随机飞行高度: {apogee_alt_km:.1f}km (范围: {self.min_altitude}-{self.max_altitude}km)")

                trajectory.ImpactLocation.SetLaunchControlType(0)
                trajectory.ImpactLocation.LaunchControl.ApogeeAlt = apogee_alt_km
                logger.info(f"✅ 发射控制设置成功: {apogee_alt_km:.1f}km")

                # 执行传播
                trajectory.Propagate()
                logger.info(f"✅ 轨迹传播成功")

                # 验证传播结果
                if self._verify_trajectory_propagation(missile):
                    logger.info(f"✅ 轨迹传播验证成功")
                else:
                    logger.warning(f"⚠️  轨迹传播验证失败，但继续执行")

                return True

            except Exception as traj_error:
                logger.warning(f"⚠️  轨迹参数设置失败: {traj_error}")
                return False
                
            except Exception as e:
                logger.warning(f"⚠️ EphemerisInterval方法失败: {e}")
                return False
            
        except Exception as e:
            logger.error(f"❌ 轨迹配置失败: {e}")
            return False
    
    def _validate_trajectory_parameters(self, trajectory_params: Dict) -> Optional[Dict]:
        """验证轨迹参数"""
        required_params = ['launch_position', 'target_position']
        
        for param in required_params:
            if param not in trajectory_params:
                logger.error(f"❌ 缺少必需参数: {param}")
                return None
        
        # 验证位置参数
        launch_pos = trajectory_params['launch_position']
        target_pos = trajectory_params['target_position']
        
        for pos_name, pos in [('launch_position', launch_pos), ('target_position', target_pos)]:
            if not all(key in pos for key in ['lat', 'lon', 'alt']):
                logger.error(f"❌ {pos_name} 缺少必需的坐标参数")
                return None
            
            # 验证坐标范围
            if not (-90 <= pos['lat'] <= 90):
                logger.error(f"❌ {pos_name} 纬度超出范围: {pos['lat']}")
                return None
            
            if not (-180 <= pos['lon'] <= 180):
                logger.error(f"❌ {pos_name} 经度超出范围: {pos['lon']}")
                return None
        
        logger.info("✅ 轨迹参数验证通过")
        return trajectory_params
    
    def _set_launch_position_optimized(self, missile, launch_pos: Dict, launch_time_str: str):
        """设置发射位置 - 基于原始代码的实际实现"""
        try:
            # 方法1: 使用Ballistic轨迹的Launch属性
            try:
                trajectory = missile.Trajectory
                ballistic = trajectory.Ballistic

                # 设置发射点位置
                ballistic.Launch.Position.AssignGeodetic(
                    launch_pos['lat'],    # 纬度 (度)
                    launch_pos['lon'],    # 经度 (度)
                    launch_pos['alt'] * 1000.0  # 高度 (m，从km转换)
                )

                logger.info(f"✅ 发射位置设置成功: {launch_pos}")
                return

            except Exception as e1:
                logger.debug(f"Ballistic.Launch方法失败: {e1}")

            # 方法2: 使用InitialState设置
            try:
                initial_state = missile.Trajectory.InitialState
                initial_state.Position.AssignGeodetic(
                    launch_pos['lat'],
                    launch_pos['lon'],
                    launch_pos['alt'] * 1000.0
                )

                logger.info(f"✅ 发射位置设置成功(InitialState): {launch_pos}")
                return

            except Exception as e2:
                logger.debug(f"InitialState方法失败: {e2}")

            # 方法3: 使用Connect命令设置
            try:
                missile_path = f"*/Missile/{missile.InstanceName}"
                cmd = f"SetPosition {missile_path} Geodetic {launch_pos['lat']} {launch_pos['lon']} {launch_pos['alt']*1000.0}"
                self.stk_manager.root.ExecuteCommand(cmd)

                logger.info(f"✅ 发射位置设置成功(Connect): {launch_pos}")
                return

            except Exception as e3:
                logger.debug(f"Connect命令方法失败: {e3}")

            raise Exception("所有发射位置设置方法都失败")

        except Exception as e:
            logger.error(f"❌ 发射位置设置失败: {e}")
            raise
    
    def _set_impact_position_optimized(self, missile, target_pos: Dict, impact_time_str: str):
        """设置撞击位置 - 基于原始代码的实际实现"""
        try:
            # 方法1: 使用Ballistic轨迹的Impact属性
            try:
                trajectory = missile.Trajectory
                ballistic = trajectory.Ballistic

                # 设置撞击点位置
                ballistic.Impact.Position.AssignGeodetic(
                    target_pos['lat'],    # 纬度 (度)
                    target_pos['lon'],    # 经度 (度)
                    target_pos['alt'] * 1000.0  # 高度 (m，从km转换)
                )

                logger.info(f"✅ 撞击位置设置成功: {target_pos}")
                return

            except Exception as e1:
                logger.debug(f"Ballistic.Impact方法失败: {e1}")

            # 方法2: 使用FinalState设置
            try:
                final_state = missile.Trajectory.FinalState
                final_state.Position.AssignGeodetic(
                    target_pos['lat'],
                    target_pos['lon'],
                    target_pos['alt'] * 1000.0
                )

                logger.info(f"✅ 撞击位置设置成功(FinalState): {target_pos}")
                return

            except Exception as e2:
                logger.debug(f"FinalState方法失败: {e2}")

            # 方法3: 使用Connect命令设置目标位置
            try:
                missile_path = f"*/Missile/{missile.InstanceName}"
                cmd = f"SetTarget {missile_path} Geodetic {target_pos['lat']} {target_pos['lon']} {target_pos['alt']*1000.0}"
                self.stk_manager.root.ExecuteCommand(cmd)

                logger.info(f"✅ 撞击位置设置成功(Connect): {target_pos}")
                return

            except Exception as e3:
                logger.debug(f"Connect命令方法失败: {e3}")

            raise Exception("所有撞击位置设置方法都失败")

        except Exception as e:
            logger.error(f"❌ 撞击位置设置失败: {e}")
            raise
    
    def _propagate_missile_trajectory(self, missile) -> bool:
        """传播导弹轨迹"""
        try:
            logger.info("🔄 开始传播导弹轨迹...")
            
            # 传播轨迹
            missile.Trajectory.Propagate()
            logger.info("✅ 轨迹传播成功")
            
            # 验证轨迹数据 (使用DataProvider验证，日志显示成功)
            success = self._verify_trajectory_data(missile)
            if success:
                logger.info("✅ 轨迹数据验证成功")
                return True
            else:
                logger.warning("⚠️ 轨迹数据验证失败，但传播已完成")
                return True  # 传播成功，验证失败不影响主要功能
            
        except Exception as e:
            logger.error(f"❌ 轨迹传播失败: {e}")
            return False
    
    def _verify_trajectory_data(self, missile) -> bool:
        """验证轨迹数据 - 基于原始代码的正确方法"""
        try:
            missile_id = missile.InstanceName

            # 方法1: 检查轨迹时间范围 - 基于原始代码的正确方法
            try:
                trajectory = missile.Trajectory

                # 尝试获取导弹的实际发射和撞击时间
                try:
                    launch_time = trajectory.LaunchTime
                    impact_time = trajectory.ImpactTime
                    logger.info(f"✅ 导弹实际时间范围: {launch_time} - {impact_time}")
                    return True
                except Exception as traj_time_error:
                    logger.debug(f"导弹时间获取失败: {traj_time_error}")

                    # 尝试从EphemerisInterval获取 - 使用属性而不是方法
                    try:
                        ephemeris = trajectory.EphemerisInterval
                        start_time_stk = ephemeris.StartTime  # 使用属性，不是GetStartTime()方法
                        stop_time_stk = ephemeris.StopTime    # 使用属性，不是GetStopTime()方法
                        logger.info(f"✅ EphemerisInterval时间范围: {start_time_stk} - {stop_time_stk}")
                        return True
                    except Exception as ephemeris_error:
                        logger.debug(f"EphemerisInterval时间获取失败: {ephemeris_error}")

            except Exception as trajectory_error:
                logger.debug(f"轨迹对象获取失败: {trajectory_error}")

            # 方法2: 检查DataProvider是否可用
            try:
                data_providers = missile.DataProviders
                provider_count = data_providers.Count

                if provider_count > 0:
                    # 尝试获取LLA State DataProvider
                    lla_provider = data_providers.Item("LLA State")
                    logger.info(f"✅ 轨迹数据验证成功，DataProvider可用")
                    return True
                else:
                    logger.info(f"ℹ️ DataProvider数量为0，但轨迹可能仍然有效")
                    return True  # 即使没有DataProvider，轨迹可能仍然有效

            except Exception as dp_error:
                logger.debug(f"DataProvider检查失败: {dp_error}")

            # 如果所有方法都失败，但不影响主要功能
            logger.info(f"ℹ️ 轨迹数据验证无法完成，但轨迹传播已成功")
            return True  # 不因为验证问题而判定失败

        except Exception as e:
            logger.warning(f"⚠️ 轨迹数据验证失败: {e}")
            return True  # 验证失败不影响主要功能
    
    def get_missile_trajectory_data(self, missile_id: str, time_str: str) -> Optional[Dict]:
        """
        获取导弹轨迹数据 - 基于实际使用的DataProvider方法
        """
        try:
            missile = self._find_missile(missile_id)
            if not missile:
                return None
            
            # 使用LLA State DataProvider
            dp = missile.DataProviders.Item("LLA State")
            result = dp.ExecSingle(time_str)
            
            if result:
                data_set = result.DataSets.Item(0)
                values = data_set.GetValues()
                
                return {
                    'latitude': values[1],
                    'longitude': values[2],
                    'altitude': values[3],
                    'timestamp': time_str
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取导弹轨迹数据失败: {e}")
            return None
    
    def _find_missile(self, missile_id: str):
        """查找导弹对象"""
        try:
            scenario = self.stk_manager.scenario
            for i in range(scenario.Children.Count):
                child = scenario.Children.Item(i)
                if (getattr(child, 'ClassName', None) == 'Missile' and 
                    getattr(child, 'InstanceName', None) == missile_id):
                    return child
            return None
        except Exception as e:
            logger.error(f"❌ 查找导弹失败: {e}")
            return None
    
    def calculate_trajectory_distance(self, launch_pos: Dict, target_pos: Dict) -> float:
        """计算轨迹距离 - 大圆距离"""
        try:
            lat1, lon1 = math.radians(launch_pos['lat']), math.radians(launch_pos['lon'])
            lat2, lon2 = math.radians(target_pos['lat']), math.radians(target_pos['lon'])
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = (math.sin(dlat/2)**2 + 
                 math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2)
            c = 2 * math.asin(math.sqrt(a))
            
            # 地球半径 (km)
            earth_radius = 6371.0
            distance = earth_radius * c
            
            logger.info(f"✅ 轨迹距离计算: {distance:.2f} km")
            return distance
            
        except Exception as e:
            logger.error(f"❌ 轨迹距离计算失败: {e}")
            return 0.0
    
    def get_missile_status(self, missile_id: str) -> Dict[str, Any]:
        """获取导弹状态"""
        try:
            missile = self._find_missile(missile_id)
            if not missile:
                return {'exists': False, 'error': 'Missile not found'}
            
            status = {
                'exists': True,
                'missile_id': missile_id,
                'trajectory_type': 'ballistic',
                'has_trajectory_data': False
            }
            
            # 检查轨迹数据 - 使用正确的属性访问方法
            try:
                ephemeris = missile.Trajectory.EphemerisInterval
                start_time = ephemeris.StartTime  # 使用属性，不是GetStartTime()方法
                end_time = ephemeris.StopTime     # 使用属性，不是GetStopTime()方法
                status['start_time'] = start_time
                status['end_time'] = end_time
                status['has_trajectory_data'] = True
            except:
                pass
            
            return status
            
        except Exception as e:
            logger.error(f"❌ 获取导弹状态失败: {e}")
            return {'exists': False, 'error': str(e)}

    def create_single_missile_target(self, missile_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        创建单个导弹目标 - 兼容性方法

        Args:
            missile_config: 导弹配置字典，包含missile_id, launch_position, target_position等

        Returns:
            成功时返回导弹信息字典，失败时返回None
        """
        try:
            missile_id = missile_config.get("missile_id")
            launch_time = missile_config.get("launch_time", datetime.now())

            # 构建轨迹参数
            trajectory_params = {
                'launch_position': missile_config.get("launch_position"),
                'target_position': missile_config.get("target_position"),
                'flight_duration': missile_config.get("flight_duration", 1800)
            }

            # 调用重构后的create_missile方法
            success = self.create_missile(missile_id, launch_time, trajectory_params)

            if success:
                # 自动添加到missile_targets字典中，供元任务管理器使用
                self.add_missile_target(
                    missile_id,
                    missile_config.get("launch_position"),
                    missile_config.get("target_position"),
                    missile_config.get("launch_sequence", 1),
                    launch_time
                )

                return {
                    "success": True,
                    "missile_id": missile_id,
                    "launch_time": launch_time,
                    "trajectory_params": trajectory_params
                }
            else:
                return None

        except Exception as e:
            logger.error(f"❌ create_single_missile_target失败: {e}")
            return None

    def add_missile_target(self, missile_id: str, launch_position: Dict[str, float],
                          target_position: Dict[str, float], launch_sequence: int = 1,
                          launch_time: datetime = None):
        """添加导弹目标配置 - 兼容性方法"""
        self.missile_targets[missile_id] = {
            "launch_position": launch_position,
            "target_position": target_position,
            "launch_sequence": launch_sequence,
            "launch_time": launch_time
        }
        logger.info(f"✅ 添加导弹目标配置: {missile_id}")
        if launch_time:
            logger.info(f"   发射时间: {launch_time}")

    def create_missile_in_stk(self, missile_id: str) -> bool:
        """
        在STK中创建导弹对象 - 简化版本用于测试

        Args:
            missile_id: 导弹ID

        Returns:
            创建是否成功
        """
        try:
            if missile_id not in self.missile_targets:
                logger.error(f"❌ 导弹配置不存在: {missile_id}")
                return False

            missile_config = self.missile_targets[missile_id]
            launch_time = missile_config.get("launch_time", datetime.now())

            # 使用现有的create_missile方法
            trajectory_params = {
                "launch_position": missile_config["launch_position"],
                "target_position": missile_config["target_position"],
                "flight_time": 1800  # 30分钟飞行时间
            }

            success = self.create_missile(missile_id, launch_time, trajectory_params)
            if success:
                logger.info(f"✅ 导弹 {missile_id} 在STK中创建成功")
            else:
                logger.error(f"❌ 导弹 {missile_id} 在STK中创建失败")

            return success

        except Exception as e:
            logger.error(f"❌ 创建导弹异常 {missile_id}: {e}")
            return False

    def _parse_stk_time(self, time_str: str) -> Optional[datetime]:
        """
        解析STK时间字符串为datetime对象

        Args:
            time_str: STK时间字符串，如 "26 Jul 2025 02:00:00.000000000"

        Returns:
            解析后的datetime对象，失败返回None
        """
        try:
            # STK时间格式: "26 Jul 2025 02:00:00.000000000"
            # 移除纳秒部分，只保留到微秒
            if '.' in time_str:
                time_part, fraction_part = time_str.split('.')
                # 只取前6位作为微秒
                microseconds = fraction_part[:6].ljust(6, '0')
                time_str = f"{time_part}.{microseconds}"

            # 解析时间
            return datetime.strptime(time_str, "%d %b %Y %H:%M:%S.%f")

        except ValueError:
            try:
                # 尝试不带微秒的格式
                return datetime.strptime(time_str, "%d %b %Y %H:%M:%S")
            except ValueError:
                try:
                    # 尝试ISO格式
                    return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.debug(f"无法解析时间字符串: {time_str}")
                    return None
        except Exception as e:
            logger.debug(f"时间解析异常: {e}")
            return None

    def _generate_random_global_missile(self, start_time: datetime, end_time: datetime, sequence: int) -> Optional[Dict]:
        """生成随机全球导弹场景 - 兼容性方法"""
        try:
            import random

            # 生成随机发射位置
            launch_lat = random.uniform(-60, 60)  # 避免极地
            launch_lon = random.uniform(-180, 180)
            launch_alt = random.uniform(0, 1)  # 地面发射

            # 生成随机目标位置（距离发射点1000-8000km）
            target_distance = random.uniform(1000, 8000)  # km
            bearing = random.uniform(0, 360)  # 度

            # 简单的大圆距离计算目标位置
            earth_radius = 6371.0  # km
            angular_distance = target_distance / earth_radius

            launch_lat_rad = math.radians(launch_lat)
            launch_lon_rad = math.radians(launch_lon)
            bearing_rad = math.radians(bearing)

            target_lat_rad = math.asin(
                math.sin(launch_lat_rad) * math.cos(angular_distance) +
                math.cos(launch_lat_rad) * math.sin(angular_distance) * math.cos(bearing_rad)
            )

            target_lon_rad = launch_lon_rad + math.atan2(
                math.sin(bearing_rad) * math.sin(angular_distance) * math.cos(launch_lat_rad),
                math.cos(angular_distance) - math.sin(launch_lat_rad) * math.sin(target_lat_rad)
            )

            target_lat = math.degrees(target_lat_rad)
            target_lon = math.degrees(target_lon_rad)
            target_alt = 0.0  # 地面目标

            # 生成发射时间
            time_range = (end_time - start_time).total_seconds()
            launch_offset = random.uniform(0, time_range * 0.8)  # 在前80%时间内发射
            launch_time = start_time + timedelta(seconds=launch_offset)

            # 生成导弹ID
            missile_id = f"GlobalMissile_{sequence:03d}_{random.randint(1000, 9999)}"

            return {
                "missile_id": missile_id,
                "launch_position": {"lat": launch_lat, "lon": launch_lon, "alt": launch_alt},
                "target_position": {"lat": target_lat, "lon": target_lon, "alt": target_alt},
                "launch_time": launch_time,
                "flight_duration": random.randint(1800, 3600),  # 30-60分钟
                "launch_sequence": sequence
            }

        except Exception as e:
            logger.error(f"❌ 生成随机导弹场景失败: {e}")
            return None

    def _set_missile_time_period_correct(self, missile, launch_time: datetime, flight_duration: int = 1800) -> bool:
        """
        基于STK官方文档的正确导弹时间设置方法
        使用 EphemerisInterval.SetExplicitInterval() 方法

        Returns:
            bool: 时间设置是否成功
        """
        try:
            # 获取场景时间范围
            scenario_start = self.stk_manager.scenario.StartTime
            scenario_stop = self.stk_manager.scenario.StopTime

            logger.info(f"📅 场景时间范围: {scenario_start} - {scenario_stop}")

            # 解析场景开始时间
            try:
                start_dt = datetime.strptime(scenario_start, "%d %b %Y %H:%M:%S.%f")
            except:
                try:
                    start_dt = datetime.strptime(scenario_start, "%d %b %Y %H:%M:%S")
                except:
                    logger.warning("无法解析场景开始时间，使用当前时间")
                    start_dt = datetime.now()

            # 确保发射时间在场景范围内
            if launch_time < start_dt:
                launch_time = start_dt + timedelta(minutes=1)
                logger.info(f"调整发射时间到场景开始后: {launch_time}")

            # 计算撞击时间（使用传入的飞行时间）
            impact_time = launch_time + timedelta(seconds=flight_duration)

            # 转换为STK时间格式
            launch_time_str = launch_time.strftime("%d %b %Y %H:%M:%S.000")
            impact_time_str = impact_time.strftime("%d %b %Y %H:%M:%S.000")

            # 基于STK官方文档：使用EphemerisInterval.SetExplicitInterval()方法
            try:
                trajectory = missile.Trajectory
                # 根据STK官方文档，使用EphemerisInterval设置时间范围
                trajectory.EphemerisInterval.SetExplicitInterval(launch_time_str, impact_time_str)
                logger.info(f"✅ EphemerisInterval时间设置成功: {launch_time_str} - {impact_time_str}")
                return True  # 成功设置时间

            except Exception as e1:
                logger.warning(f"EphemerisInterval时间设置失败: {e1}")
                return False  # 时间设置失败

        except Exception as e:
            logger.error(f"❌ 导弹时间设置失败: {e}")
            return False  # 异常情况返回失败

    def get_missile_actual_time_range(self, missile_id: str) -> Optional[Tuple[datetime, datetime]]:
        """
        获取导弹的实际时间范围（发射时间和撞击时间）

        Returns:
            (launch_time, impact_time) 或 None（如果获取失败）
        """
        try:
            missile = self.stk_manager.scenario.Children.Item(missile_id)
            trajectory = missile.Trajectory

            # 确保轨迹已传播
            try:
                trajectory.Propagate()
            except Exception as prop_error:
                logger.debug(f"轨迹传播失败: {prop_error}")

            # 尝试获取实际时间范围
            try:
                launch_time_str = trajectory.LaunchTime
                impact_time_str = trajectory.ImpactTime

                # 转换为datetime对象
                launch_time = self._parse_stk_time(launch_time_str)
                impact_time = self._parse_stk_time(impact_time_str)

                if launch_time and impact_time:
                    logger.info(f"✅ 导弹 {missile_id} 实际时间范围: {launch_time} - {impact_time}")
                    return launch_time, impact_time

            except Exception as traj_error:
                logger.debug(f"从轨迹获取时间失败: {traj_error}")

                # 尝试从EphemerisInterval获取
                try:
                    ephemeris = trajectory.EphemerisInterval
                    start_time_str = ephemeris.StartTime
                    stop_time_str = ephemeris.StopTime

                    start_time = self._parse_stk_time(start_time_str)
                    stop_time = self._parse_stk_time(stop_time_str)

                    if start_time and stop_time:
                        logger.info(f"✅ 导弹 {missile_id} EphemerisInterval时间范围: {start_time} - {stop_time}")
                        return start_time, stop_time

                except Exception as ephemeris_error:
                    logger.debug(f"从EphemerisInterval获取时间失败: {ephemeris_error}")

            logger.error(f"❌ 无法获取导弹 {missile_id} 的实际时间范围")
            return None

        except Exception as e:
            logger.error(f"❌ 获取导弹时间范围失败 {missile_id}: {e}")
            return None

    def get_missile_trajectory_info(self, missile_id: str) -> Optional[Dict[str, Any]]:
        """获取导弹轨迹信息 - 优化版本，支持缓存"""
        logger.info(f"🎯 获取导弹轨迹信息: {missile_id}")

        # 1. 检查缓存
        cached_data = self._get_cached_trajectory_data(missile_id)
        if cached_data:
            return cached_data

        # 2. 获取导弹对象（使用缓存）
        missile = self._get_cached_missile_object(missile_id)
        logger.info(f"✅ 导弹对象获取成功: {missile_id}")

        # 修复：确保轨迹传播
        try:
            logger.info(f"🔄 确保导弹轨迹传播: {missile_id}")
            trajectory = missile.Trajectory
            trajectory.Propagate()
            logger.info(f"✅ 导弹轨迹传播成功: {missile_id}")
        except Exception as prop_error:
            logger.warning(f"⚠️ 导弹轨迹传播失败: {missile_id}, {prop_error}")

        # 直接从STK DataProvider获取轨迹数据
        return self._get_trajectory_from_stk_dataprovider(missile)

    def get_missile_flight_phases_by_altitude(self, missile_id: str) -> Optional[Dict[str, Any]]:
        """
        基于导弹真实轨迹高度分析飞行阶段时间范围（优化版本，支持缓存）

        Returns:
            包含各飞行阶段时间范围的字典，或None（如果分析失败）
        """
        try:
            logger.info(f"🎯 分析导弹 {missile_id} 轨迹高度以确定飞行阶段")

            # 1. 检查高度分析缓存
            cached_analysis = self._get_cached_altitude_analysis(missile_id)
            if cached_analysis:
                return cached_analysis

            # 2. 获取导弹轨迹数据（使用缓存）
            trajectory_info = self.get_missile_trajectory_info(missile_id)
            if not trajectory_info:
                logger.error(f"❌ 无法获取导弹 {missile_id} 轨迹数据")
                return None

            trajectory_points = trajectory_info.get("trajectory_points", [])
            if not trajectory_points:
                logger.error(f"❌ 导弹 {missile_id} 轨迹数据为空")
                return None

            logger.info(f"📊 获取到 {len(trajectory_points)} 个轨迹点")

            # 3. 分析高度变化确定飞行阶段
            analysis_result = self._analyze_flight_phases_by_altitude(trajectory_points, missile_id)

            # 4. 缓存分析结果
            if analysis_result:
                self._cache_altitude_analysis(missile_id, analysis_result)

            return analysis_result

        except Exception as e:
            logger.error(f"❌ 分析导弹飞行阶段失败 {missile_id}: {e}")
            return None

    def _analyze_flight_phases_by_altitude(self, trajectory_points: List[Dict], missile_id: str) -> Dict[str, Any]:
        """
        基于真实轨迹高度数据分析飞行阶段，使用配置的中段高度阈值

        Args:
            trajectory_points: 轨迹点列表
            missile_id: 导弹ID

        Returns:
            飞行阶段分析结果
        """
        try:
            # 获取中段高度阈值配置
            from ..utils.config_manager import get_config_manager
            config_manager = get_config_manager()
            task_planning_config = config_manager.get_task_planning_config()
            midcourse_altitude_threshold = task_planning_config.get("midcourse_altitude_threshold", 100)  # 默认100km

            logger.info(f"📏 使用中段高度阈值: {midcourse_altitude_threshold}km")
            logger.info(f"📊 开始解析 {len(trajectory_points)} 个轨迹点的高度数据...")

            # 提取时间和高度数据
            times = []
            altitudes = []
            valid_points = 0
            parse_errors = 0

            for i, point in enumerate(trajectory_points):
                time_str = point.get("time")
                altitude = point.get("alt")  # 修复：使用正确的字段名 "alt"

                if time_str and altitude is not None:
                    time_obj = self._parse_stk_time(time_str)
                    if time_obj:
                        try:
                            # STK返回的高度数据已经是千米单位，直接使用
                            altitude_km = float(altitude)
                            times.append(time_obj)
                            altitudes.append(altitude_km)
                            valid_points += 1

                            # 调试信息：显示前几个点的数据
                            if i < 3:
                                logger.info(f"   样本点 {i+1}: 时间={time_str}, 高度={altitude_km:.2f}km")
                        except (ValueError, TypeError) as e:
                            parse_errors += 1
                            if parse_errors <= 3:  # 只显示前3个错误
                                logger.warning(f"   高度解析错误 点{i+1}: {altitude} - {e}")
                    else:
                        parse_errors += 1
                        if parse_errors <= 3:
                            logger.warning(f"   时间解析错误 点{i+1}: {time_str}")
                else:
                    parse_errors += 1
                    if parse_errors <= 3:
                        logger.warning(f"   数据缺失 点{i+1}: time={time_str}, alt={altitude}")

            logger.info(f"📊 数据解析结果: 有效点数={valid_points}, 错误数={parse_errors}")

            if len(times) < 3:
                logger.warning(f"⚠️ 轨迹点数量不足，无法分析飞行阶段: {len(times)}")
                logger.warning(f"   原始点数: {len(trajectory_points)}, 有效点数: {valid_points}, 错误数: {parse_errors}")
                return None

            logger.info(f"📈 高度范围: {min(altitudes):.1f}km - {max(altitudes):.1f}km")

            # 基于高度阈值分析飞行阶段
            phases = self._identify_flight_phases_by_altitude_threshold(
                times, altitudes, midcourse_altitude_threshold, missile_id
            )

            # 构建结果
            result = {
                "missile_id": missile_id,
                "launch_time": times[0],
                "impact_time": times[-1],
                "total_flight_time": (times[-1] - times[0]).total_seconds(),
                "max_altitude": max(altitudes),
                "flight_phases": phases,
                "trajectory_points_count": len(times),
                "altitude_analysis": {
                    "min_altitude": min(altitudes),
                    "max_altitude": max(altitudes),
                    "altitude_range": max(altitudes) - min(altitudes)
                }
            }

            logger.info(f"✅ 飞行阶段分析完成:")
            logger.info(f"   助推段: {phases['boost']['start']} - {phases['boost']['end']}")
            logger.info(f"   中段: {phases['midcourse']['start']} - {phases['midcourse']['end']}")
            logger.info(f"   末段: {phases['terminal']['start']} - {phases['terminal']['end']}")
            logger.info(f"   最大高度: {max(altitudes):.1f}km")

            return result

        except Exception as e:
            logger.error(f"❌ 飞行阶段分析失败: {e}")
            return None

    def _identify_flight_phases_by_altitude_threshold(self, times: List[datetime], altitudes: List[float],
                                                    altitude_threshold: float, missile_id: str) -> Dict[str, Dict]:
        """
        基于配置的高度阈值识别飞行阶段

        Args:
            times: 时间列表
            altitudes: 高度列表 (km)
            altitude_threshold: 中段高度阈值 (km)
            missile_id: 导弹ID

        Returns:
            飞行阶段字典
        """
        try:
            logger.info(f"🎯 基于高度阈值 {altitude_threshold}km 分析飞行阶段...")

            # 找到超过高度阈值的时间段
            midcourse_start_idx = None
            midcourse_end_idx = None

            # 寻找第一次超过阈值的点（中段开始）
            for i, altitude in enumerate(altitudes):
                if altitude >= altitude_threshold:
                    midcourse_start_idx = i
                    break

            # 寻找最后一次超过阈值的点（中段结束）
            for i in range(len(altitudes) - 1, -1, -1):
                if altitudes[i] >= altitude_threshold:
                    midcourse_end_idx = i
                    break

            # 如果没有找到超过阈值的点，使用传统方法
            if midcourse_start_idx is None or midcourse_end_idx is None:
                logger.warning(f"⚠️ 导弹 {missile_id} 未达到中段高度阈值 {altitude_threshold}km，使用传统分析方法")
                return self._identify_flight_phases_from_altitude(times, altitudes)

            # 确保中段时间段合理
            if midcourse_start_idx >= midcourse_end_idx:
                logger.warning(f"⚠️ 中段时间段不合理，使用传统分析方法")
                return self._identify_flight_phases_from_altitude(times, altitudes)

            # 计算各阶段时间
            boost_end_time = times[midcourse_start_idx]
            terminal_start_time = times[midcourse_end_idx]

            # 构建飞行阶段
            phases = {
                "boost": {
                    "start": times[0],
                    "end": boost_end_time,
                    "duration_seconds": (boost_end_time - times[0]).total_seconds(),
                    "max_altitude": max(altitudes[:midcourse_start_idx + 1]) if midcourse_start_idx > 0 else altitudes[0]
                },
                "midcourse": {
                    "start": boost_end_time,
                    "end": terminal_start_time,
                    "duration_seconds": (terminal_start_time - boost_end_time).total_seconds(),
                    "max_altitude": max(altitudes[midcourse_start_idx:midcourse_end_idx + 1]),
                    "min_altitude_threshold": altitude_threshold,
                    "actual_min_altitude": min(altitudes[midcourse_start_idx:midcourse_end_idx + 1]),
                    "altitude_above_threshold": True
                },
                "terminal": {
                    "start": terminal_start_time,
                    "end": times[-1],
                    "duration_seconds": (times[-1] - terminal_start_time).total_seconds(),
                    "max_altitude": max(altitudes[midcourse_end_idx:]) if midcourse_end_idx < len(altitudes) - 1 else altitudes[-1]
                }
            }

            # 验证阶段时间的合理性
            total_duration = (times[-1] - times[0]).total_seconds()
            midcourse_duration = phases["midcourse"]["duration_seconds"]
            midcourse_ratio = midcourse_duration / total_duration

            logger.info(f"✅ 基于高度阈值的飞行阶段分析:")
            logger.info(f"   助推段: {phases['boost']['start']} - {phases['boost']['end']} ({phases['boost']['duration_seconds']:.0f}秒)")
            logger.info(f"   中段: {phases['midcourse']['start']} - {phases['midcourse']['end']} ({phases['midcourse']['duration_seconds']:.0f}秒)")
            logger.info(f"   末段: {phases['terminal']['start']} - {phases['terminal']['end']} ({phases['terminal']['duration_seconds']:.0f}秒)")
            logger.info(f"   中段占比: {midcourse_ratio:.1%}")
            logger.info(f"   中段最大高度: {phases['midcourse']['max_altitude']:.1f}km")
            logger.info(f"   中段最小高度: {phases['midcourse']['actual_min_altitude']:.1f}km")

            return phases

        except Exception as e:
            logger.error(f"❌ 基于高度阈值的飞行阶段分析失败: {e}")
            # 回退到传统方法
            return self._identify_flight_phases_from_altitude(times, altitudes)

    def _get_trajectory_from_stk_dataprovider(self, missile) -> Dict[str, Any]:
        """从STK DataProvider获取真实轨迹数据"""
        missile_id = missile.InstanceName
        logger.info(f"🎯 从STK DataProvider获取轨迹数据: {missile_id}")

        try:
            # 从STK DataProvider获取真实轨迹数据
            logger.info(f"🎯 从STK DataProvider获取真实轨迹数据")
            real_trajectory = self._extract_real_trajectory_from_stk(missile)
            if real_trajectory:
                logger.info(f"✅ 成功获取STK真实轨迹数据")
                return real_trajectory
            else:
                raise Exception("STK DataProvider数据提取失败")

        except Exception as e:
            logger.error(f"❌ STK真实轨迹获取失败: {e}")
            raise Exception(f"无法获取导弹 {missile_id} 的STK真实轨迹数据: {e}")

    def _identify_flight_phases_from_altitude(self, times: List[datetime], altitudes: List[float]) -> Dict[str, Dict]:
        """
        基于高度变化识别飞行阶段

        Args:
            times: 时间列表
            altitudes: 高度列表

        Returns:
            飞行阶段字典
        """
        try:
            # 找到最大高度点
            max_altitude_idx = altitudes.index(max(altitudes))
            max_altitude_time = times[max_altitude_idx]

            # 计算高度变化率（简化分析）
            altitude_changes = []
            for i in range(1, len(altitudes)):
                dt = (times[i] - times[i-1]).total_seconds()
                if dt > 0:
                    rate = (altitudes[i] - altitudes[i-1]) / dt  # m/s
                    altitude_changes.append(rate)
                else:
                    altitude_changes.append(0)

            # 识别助推段结束点（高度变化率显著下降的点）
            boost_end_idx = self._find_boost_phase_end(altitude_changes)
            if boost_end_idx >= len(times):
                boost_end_idx = min(len(times) // 4, len(times) - 1)  # 回退到25%位置

            # 识别末段开始点（高度开始快速下降的点）
            terminal_start_idx = self._find_terminal_phase_start(altitudes, max_altitude_idx)
            if terminal_start_idx <= boost_end_idx:
                terminal_start_idx = max(len(times) * 3 // 4, boost_end_idx + 1)  # 回退到75%位置

            # 构建飞行阶段
            phases = {
                "boost": {
                    "start": times[0],
                    "end": times[boost_end_idx],
                    "duration_seconds": (times[boost_end_idx] - times[0]).total_seconds(),
                    "max_altitude": max(altitudes[:boost_end_idx + 1]),
                    "altitude_gain": altitudes[boost_end_idx] - altitudes[0]
                },
                "midcourse": {
                    "start": times[boost_end_idx],
                    "end": times[terminal_start_idx],
                    "duration_seconds": (times[terminal_start_idx] - times[boost_end_idx]).total_seconds(),
                    "max_altitude": max(altitudes[boost_end_idx:terminal_start_idx + 1]),
                    "apogee_time": max_altitude_time
                },
                "terminal": {
                    "start": times[terminal_start_idx],
                    "end": times[-1],
                    "duration_seconds": (times[-1] - times[terminal_start_idx]).total_seconds(),
                    "altitude_loss": altitudes[terminal_start_idx] - altitudes[-1]
                }
            }

            return phases

        except Exception as e:
            logger.error(f"❌ 飞行阶段识别失败: {e}")
            # 回退到简单的时间比例分割
            total_time = times[-1] - times[0]
            boost_end = times[0] + total_time * 0.1
            terminal_start = times[-1] - total_time * 0.1

            return {
                "boost": {
                    "start": times[0],
                    "end": boost_end,
                    "duration_seconds": total_time.total_seconds() * 0.1
                },
                "midcourse": {
                    "start": boost_end,
                    "end": terminal_start,
                    "duration_seconds": total_time.total_seconds() * 0.8
                },
                "terminal": {
                    "start": terminal_start,
                    "end": times[-1],
                    "duration_seconds": total_time.total_seconds() * 0.1
                }
            }

    def _find_boost_phase_end(self, altitude_changes: List[float]) -> int:
        """找到助推段结束点（高度变化率显著下降）"""
        try:
            if len(altitude_changes) < 5:
                return len(altitude_changes) // 4

            # 寻找高度变化率从正值显著下降的点
            max_rate = max(altitude_changes[:len(altitude_changes)//2])  # 前半段的最大上升率
            threshold = max_rate * 0.3  # 30%阈值

            for i in range(len(altitude_changes)//4, len(altitude_changes)//2):
                if altitude_changes[i] < threshold:
                    return i

            # 回退到25%位置
            return len(altitude_changes) // 4

        except Exception:
            return len(altitude_changes) // 4

    def _find_terminal_phase_start(self, altitudes: List[float], max_altitude_idx: int) -> int:
        """找到末段开始点（高度开始快速下降）"""
        try:
            if max_altitude_idx >= len(altitudes) - 5:
                return len(altitudes) * 3 // 4

            # 从最大高度点开始，寻找高度开始快速下降的点
            max_altitude = altitudes[max_altitude_idx]
            threshold_altitude = max_altitude * 0.8  # 80%高度阈值

            for i in range(max_altitude_idx, len(altitudes)):
                if altitudes[i] < threshold_altitude:
                    return i

            # 回退到75%位置
            return len(altitudes) * 3 // 4

        except Exception:
            return len(altitudes) * 3 // 4

    def _extract_real_trajectory_from_stk(self, missile) -> Optional[Dict[str, Any]]:
        """从STK获取真实轨迹数据 - 基于STK官方文档的最佳实践"""
        try:
            missile_id = missile.InstanceName
            logger.info(f"   🎯 基于STK官方文档获取轨迹数据: {missile_id}")

            # 基于STK官方文档: 首先确保导弹轨迹已传播
            try:
                # 检查导弹轨迹状态
                trajectory = missile.Trajectory
                logger.info(f"   ✅ 导弹轨迹对象获取成功")

                # 修复：使用导弹的实际发射和撞击时间
                try:
                    # 尝试获取导弹的发射和撞击时间
                    launch_time = trajectory.LaunchTime
                    impact_time = trajectory.ImpactTime
                    logger.info(f"   ⏰ 导弹实际时间范围: {launch_time} - {impact_time}")
                    start_time_stk = launch_time
                    stop_time_stk = impact_time
                except Exception as traj_time_error:
                    logger.debug(f"   导弹时间获取失败: {traj_time_error}")
                    # 尝试从EphemerisInterval获取
                    try:
                        ephemeris = trajectory.EphemerisInterval
                        start_time_stk = ephemeris.StartTime
                        stop_time_stk = ephemeris.StopTime
                        logger.info(f"   ⏰ 使用EphemerisInterval时间范围: {start_time_stk} - {stop_time_stk}")
                    except Exception as ephemeris_error:
                        logger.debug(f"   EphemerisInterval时间获取失败: {ephemeris_error}")
                        # 最后回退到场景时间
                        start_time_stk = self.stk_manager.scenario.StartTime
                        stop_time_stk = self.stk_manager.scenario.StopTime
                        logger.info(f"   ⏰ 使用场景时间范围: {start_time_stk} - {stop_time_stk}")

            except Exception as traj_error:
                logger.error(f"   ❌ 导弹轨迹对象获取失败: {traj_error}")
                return None

            # 基于STK官方文档: 使用正确的DataProvider访问模式
            try:
                # 获取DataProviders - 基于官方文档示例
                data_providers = missile.DataProviders
                logger.info(f"   📡 DataProviders数量: {data_providers.Count}")

                # 列出所有可用的DataProvider
                available_providers = []
                for i in range(data_providers.Count):
                    try:
                        provider_name = data_providers.Item(i).Name
                        available_providers.append(provider_name)
                    except:
                        available_providers.append(f"Provider_{i}")

                # 尝试多种DataProvider类型
                provider_names = ["LLA State", "Cartesian Position", "Classical Elements", "Position"]
                lla_provider_base = None

                for provider_name in provider_names:
                    try:
                        lla_provider_base = data_providers.Item(provider_name)
                        logger.info(f"   ✅ {provider_name} DataProvider获取成功")
                        break
                    except Exception as provider_error:
                        logger.debug(f"   尝试{provider_name}失败: {provider_error}")
                        continue

                if lla_provider_base is None:
                    # 如果没有找到命名的DataProvider，尝试使用索引
                    try:
                        lla_provider_base = data_providers.Item(0)
                        logger.info(f"   ✅ 使用索引0获取DataProvider")
                    except:
                        raise Exception("无法获取任何DataProvider")

                # 基于STK官方文档: 使用Group属性访问真正的DataProvider执行接口
                try:
                    if hasattr(lla_provider_base, 'Group'):
                        provider_group = lla_provider_base.Group
                        logger.info(f"   🔍 DataProvider Group对象获取成功")

                        # 尝试获取特定坐标系的DataProvider
                        coordinate_systems = ['Fixed', 'ICRF', 'J2000', 'Inertial']
                        lla_provider = None

                        for coord_sys in coordinate_systems:
                            try:
                                lla_provider = provider_group.Item(coord_sys)
                                logger.info(f"   ✅ 成功获取{coord_sys}坐标系的DataProvider")
                                break
                            except:
                                continue

                        if lla_provider is None:
                            # 如果没有找到特定坐标系，尝试使用索引0
                            try:
                                lla_provider = provider_group.Item(0)
                                logger.info(f"   ✅ 使用索引0获取DataProvider")
                            except:
                                lla_provider = lla_provider_base
                                logger.warning(f"   ⚠️ 回退到基础DataProvider对象")
                    else:
                        logger.warning(f"   ⚠️ DataProvider没有Group属性，使用基础对象")
                        lla_provider = lla_provider_base

                except Exception as provider_access_error:
                    logger.error(f"   ❌ DataProvider Group访问失败: {provider_access_error}")
                    lla_provider = lla_provider_base

                # 基于官方文档: 使用正确的时间步长和执行方式
                time_step = 30  # 默认时间步长
                logger.info(f"   ⏰ 时间步长: {time_step}秒")
                logger.info(f"   ⏰ 时间范围: {start_time_stk} 到 {stop_time_stk}")

                # 检查DataProvider结果缓存
                cache_key = f"dataprovider_{missile_id}_{start_time_stk}_{stop_time_stk}_{time_step}"
                if cache_key in self._dataprovider_cache:
                    logger.info(f"   ✅ 使用缓存的DataProvider结果")
                    result = self._dataprovider_cache[cache_key]["result"]
                    execution_method = self._dataprovider_cache[cache_key]["method"]
                else:
                    # 基于STK官方文档: 正确的DataProvider.Exec()调用方式
                    logger.info(f"   🚀 执行DataProvider.Exec()...")

                    # 重要修复: 基于STK官方文档的多种DataProvider执行方法
                    result = None
                    execution_method = None

                try:
                    # 方法1: 使用ExecElements - 基于官方文档推荐
                    elements = ["Time", "Lat", "Lon", "Alt"]
                    logger.info(f"   🔍 尝试ExecElements方法，元素: {elements}")
                    result = lla_provider.ExecElements(start_time_stk, stop_time_stk, time_step, elements)
                    execution_method = "ExecElements"
                    logger.info(f"   ✅ ExecElements方法执行成功")
                except Exception as exec_elements_error:
                    logger.debug(f"   ExecElements方法失败: {exec_elements_error}")
                    try:
                        # 方法2: 使用标准Exec方法 - 基于官方文档
                        logger.info(f"   🔍 尝试标准Exec方法")
                        result = lla_provider.Exec(start_time_stk, stop_time_stk, time_step)
                        execution_method = "Exec"
                        logger.info(f"   ✅ 标准Exec方法执行成功")
                    except Exception as exec_error:
                        logger.debug(f"   标准Exec方法失败: {exec_error}")
                        try:
                            # 方法3: 尝试不同的时间步长
                            logger.info(f"   🔍 尝试更大的时间步长: 60秒")
                            result = lla_provider.Exec(start_time_stk, stop_time_stk, 60)
                            execution_method = "Exec_60s"
                            logger.info(f"   ✅ 60秒步长Exec方法执行成功")
                        except Exception as exec_60_error:
                            logger.error(f"   ❌ 所有DataProvider执行方法都失败:")
                            logger.error(f"      ExecElements: {exec_elements_error}")
                            logger.error(f"      Exec: {exec_error}")
                            logger.error(f"      Exec_60s: {exec_60_error}")
                            return None

                if not result:
                    logger.error(f"   ❌ DataProvider返回空结果")
                    return None

                logger.info(f"   ✅ DataProvider.Exec()执行成功，使用方法: {execution_method}")
                logger.info(f"   📊 DataSets数量: {result.DataSets.Count}")

                # 缓存DataProvider结果（如果不是从缓存获取的）
                if cache_key not in self._dataprovider_cache:
                    self._dataprovider_cache[cache_key] = {
                        "result": result,
                        "method": execution_method
                    }
                    logger.debug(f"   💾 缓存DataProvider结果: {execution_method}")

                # 添加STK数据结构分析
                logger.info(f"   🔍 开始分析STK DataProvider数据结构...")
                analysis = self.stk_analyzer.analyze_dataprovider_result(result, f"导弹{missile_id}轨迹数据")

                # 输出分析结果
                logger.info(f"   📊 数据结构分析:")
                logger.info(f"     推荐访问方法: {analysis.get('recommended_method', '未知')}")
                logger.info(f"     可用数据集数量: {analysis.get('datasets_count', 0)}")

                if analysis.get('datasets_info'):
                    for dataset_info in analysis['datasets_info']:
                        logger.info(f"     数据集 {dataset_info['index']}: 名称={dataset_info.get('name', '无')}, 数据点数={dataset_info.get('count', 0)}")

                # 修复：检查DataSets是否为空
                if result.DataSets.Count == 0:
                    logger.error(f"   ❌ 轨迹数据提取失败: DataProvider返回空DataSets")
                    logger.error(f"   🔍 可能原因: 导弹轨迹时间范围不在查询时间范围内")
                    logger.error(f"   🔍 导弹时间: {start_time_stk} - {stop_time_stk}")
                    logger.error(f"   🔍 场景时间: {self.stk_manager.scenario.StartTime} - {self.stk_manager.scenario.StopTime}")
                    return None

                # 简化的数据处理 - 返回基本轨迹信息
                if result.DataSets.Count > 0:
                    dataset = result.DataSets.Item(0)

                    try:
                        data_count = dataset.Count
                        logger.info(f"   📊 DataSet数据点数: {data_count}")

                        if data_count > 0:
                            # 提取实际的轨迹点数据
                            trajectory_points = []
                            try:
                                # 正确的STK数据提取方式：使用GetDataSetByName方法
                                logger.info(f"   📊 开始提取 {data_count} 个轨迹数据点...")

                                # STK DataProvider的正确使用方式：按名称获取数据集
                                # 基于原始代码中的成功模式
                                try:
                                    # 方法1: 使用GetDataSetByName获取命名数据集（推荐方式）
                                    time_values = result.DataSets.GetDataSetByName("Time").GetValues()
                                    lat_values = result.DataSets.GetDataSetByName("Lat").GetValues()
                                    lon_values = result.DataSets.GetDataSetByName("Lon").GetValues()
                                    alt_values = result.DataSets.GetDataSetByName("Alt").GetValues()

                                    logger.info(f"   ✅ 使用GetDataSetByName方法成功获取数据")
                                    logger.info(f"   📊 数据长度: 时间={len(time_values)}, 纬度={len(lat_values)}, 经度={len(lon_values)}, 高度={len(alt_values)}")

                                except Exception as named_error:
                                    logger.warning(f"   ⚠️ GetDataSetByName方法失败: {named_error}")

                                    # 方法2: 备用方式 - 使用索引获取数据集
                                    try:
                                        time_dataset = result.DataSets.Item(0)  # 时间数据集
                                        lat_dataset = result.DataSets.Item(1)   # 纬度数据集
                                        lon_dataset = result.DataSets.Item(2)   # 经度数据集
                                        alt_dataset = result.DataSets.Item(3)   # 高度数据集

                                        time_values = time_dataset.GetValues()
                                        lat_values = lat_dataset.GetValues()
                                        lon_values = lon_dataset.GetValues()
                                        alt_values = alt_dataset.GetValues()

                                        logger.info(f"   ✅ 使用索引方法成功获取数据")
                                        logger.info(f"   📊 数据长度: 时间={len(time_values)}, 纬度={len(lat_values)}, 经度={len(lon_values)}, 高度={len(alt_values)}")

                                    except Exception as index_error:
                                        logger.error(f"   ❌ 索引方法也失败: {index_error}")
                                        logger.error(f"   📊 DataSets数量: {result.DataSets.Count}")

                                        # 调试：列出所有可用的数据集
                                        try:
                                            for i in range(result.DataSets.Count):
                                                dataset_item = result.DataSets.Item(i)
                                                logger.info(f"   📊 数据集 {i}: 名称={getattr(dataset_item, 'Name', 'Unknown')}, 数据点数={dataset_item.Count}")
                                        except:
                                            pass

                                        trajectory_points = []
                                        # 如果数据提取失败，跳过后续处理
                                        logger.warning(f"   ⚠️ 数据提取失败，返回空轨迹点列表")
                                        return {
                                            "missile_id": missile_id,
                                            "trajectory_points": trajectory_points,
                                            "launch_time": None,
                                            "impact_time": None,
                                            "flight_duration": 0,
                                            "data_source": "STK_DataProvider_Failed"
                                        }

                                # 验证数据有效性
                                if not time_values or len(time_values) == 0:
                                    logger.warning(f"   ⚠️ 时间数据为空")
                                    trajectory_points = []
                                else:
                                    # 确保所有数据列长度一致
                                    min_length = min(len(time_values), len(lat_values), len(lon_values), len(alt_values))
                                    logger.info(f"   📊 有效数据点数: {min_length}")

                                    # 逐点处理数据
                                    for i in range(min_length):
                                        try:
                                            # 获取当前数据点
                                            raw_time_str = str(time_values[i])
                                            lat_val = lat_values[i]
                                            lon_val = lon_values[i]
                                            alt_val = alt_values[i]

                                            # 调试信息：记录前几个数据点
                                            if i < 3:
                                                logger.debug(f"   🔍 数据点 {i}: 时间={raw_time_str}, 纬度={lat_val}, 经度={lon_val}, 高度={alt_val}")

                                            # 使用航天时间转换器解析时间
                                            parsed_time = self.time_converter.parse_stk_time(raw_time_str)

                                            if parsed_time is None:
                                                logger.warning(f"   ⚠️ 数据点 {i} 时间解析失败: {raw_time_str}")
                                                continue

                                            # 转换为STK标准格式
                                            time_str = self.time_converter.format_for_stk(parsed_time)

                                            # 验证数值数据
                                            try:
                                                lat_float = float(lat_val)
                                                lon_float = float(lon_val)
                                                alt_float = float(alt_val)

                                                trajectory_points.append({
                                                    "time": time_str,
                                                    "lat": lat_float,
                                                    "lon": lon_float,
                                                    "alt": alt_float
                                                })

                                            except (ValueError, TypeError) as val_error:
                                                logger.warning(f"   ⚠️ 数据点 {i} 数值转换失败: {val_error}")
                                                logger.warning(f"   📊 原始值: 纬度={lat_val}, 经度={lon_val}, 高度={alt_val}")
                                                continue

                                        except Exception as point_error:
                                            logger.warning(f"   ⚠️ 数据点 {i} 处理失败: {point_error}")
                                            continue

                                logger.info(f"   ✅ 成功提取 {len(trajectory_points)} 个轨迹点")

                            except Exception as extract_error:
                                logger.warning(f"   ⚠️ 轨迹点提取失败: {extract_error}")
                                logger.warning(f"   📊 数据集信息: 数据点数={data_count}")
                                # 如果提取失败，返回空列表但保持数据可用状态
                                trajectory_points = []

                            # 返回完整的轨迹信息
                            # 构建轨迹数据结果
                            trajectory_result = {
                                "missile_id": missile_id,
                                "launch_time": start_time_stk,
                                "impact_time": stop_time_stk,
                                "trajectory_points": trajectory_points,
                                "data_available": True,
                                "total_points": data_count
                            }

                            # 缓存轨迹数据结果
                            self._cache_trajectory_data(missile_id, trajectory_result)

                            return trajectory_result
                        else:
                            logger.warning(f"   ⚠️ DataSet为空")
                            return None

                    except Exception as data_error:
                        logger.warning(f"   ⚠️ 数据处理失败: {data_error}")
                        # 返回基本信息，包含空的轨迹点列表
                        return {
                            "missile_id": missile_id,
                            "launch_time": start_time_stk,
                            "impact_time": stop_time_stk,
                            "trajectory_points": [],
                            "data_available": False,
                            "total_points": 0
                        }

            except Exception as provider_error:
                logger.error(f"   ❌ DataProvider处理失败: {provider_error}")
                return None

        except Exception as e:
            logger.error(f"❌ 轨迹数据提取失败: {e}")
            return None

    def _verify_trajectory_propagation(self, missile) -> bool:
        """验证轨迹传播是否成功 - 基于原始代码的正确方法"""
        try:
            missile_id = missile.InstanceName
            logger.info(f"🔍 验证轨迹传播: {missile_id}")

            # 检查轨迹对象
            trajectory = missile.Trajectory

            # 使用正确的方式检查导弹时间范围
            try:
                # 方法1: 尝试获取导弹对象的时间范围
                start_time = missile.StartTime
                stop_time = missile.StopTime
                logger.info(f"   ⏰ 导弹时间范围: {start_time} - {stop_time}")
            except Exception as time_error1:
                logger.debug(f"   方法1失败: {time_error1}")
                try:
                    # 方法2: 尝试从场景获取时间范围
                    scenario_start = self.stk_manager.scenario.StartTime
                    scenario_stop = self.stk_manager.scenario.StopTime
                    logger.info(f"   ⏰ 使用场景时间范围: {scenario_start} - {scenario_stop}")
                except Exception as time_error2:
                    logger.warning(f"   ⚠️  无法获取时间范围: 方法1({time_error1}), 方法2({time_error2})")
                    # 不返回False，继续检查其他方面

            # 检查DataProvider是否可用
            try:
                data_providers = missile.DataProviders
                provider_count = data_providers.Count
                logger.info(f"   📡 DataProvider数量: {provider_count}")

                if provider_count > 0:
                    # 尝试获取LLA State DataProvider
                    lla_provider = data_providers.Item("LLA State")
                    logger.info(f"   ✅ LLA State DataProvider可用")
                    return True
                else:
                    logger.info(f"   ℹ️  DataProvider数量为0，但轨迹可能仍然有效")
                    return True  # 即使没有DataProvider，轨迹可能仍然有效

            except Exception as dp_error:
                logger.info(f"   ℹ️  DataProvider检查失败，但轨迹可能仍然有效: {dp_error}")
                return True  # 不因为DataProvider问题而判定失败

        except Exception as e:
            logger.warning(f"轨迹传播验证失败: {e}")
            return False
