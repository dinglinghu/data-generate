#!/usr/bin/env python3
"""
STK管理器重构版本
基于运行日志分析，保留实际使用的方法，删除无效分支
"""

import logging
import math
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class STKManager:
    """STK管理器重构版本 - 基于实际使用情况优化"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化STK管理器"""
        self.config = config
        self.stk = None
        self.root = None
        self.scenario = None
        self.is_connected = False
        
        # 从配置获取STK枚举和等待时间
        from src.utils.config_manager import get_config_manager
        config_manager = get_config_manager()
        stk_config = config_manager.get_stk_config()
        
        self.object_types = stk_config.get("object_types", {
            "satellite": 18, "sensor": 20, "target": 20, "missile": 19
        })
        self.propagator_types = stk_config.get("propagator_types", {
            "j2_perturbation": 1
        })
        self.wait_times = stk_config.get("wait_times", {
            "object_creation": 2.0, "sensor_creation": 1.0
        })
    
    def connect(self) -> bool:
        """连接到STK"""
        try:
            import win32com.client

            # 尝试连接到现有STK实例
            try:
                self.stk = win32com.client.GetActiveObject("STK12.Application")
                logger.info("✅ 连接到现有STK实例")
            except:
                # 创建新的STK实例
                self.stk = win32com.client.Dispatch("STK12.Application")
                self.stk.Visible = True
                logger.info("✅ 创建新的STK实例")

            self.root = self.stk.Personality2
            self.scenario = self.root.CurrentScenario

            # 如果没有当前场景，创建一个新场景
            if not self.scenario:
                logger.info("🔧 当前无场景，创建新场景...")
                success = self._create_new_scenario()
                if not success:
                    logger.error("❌ 场景创建失败")
                    return False

            self.is_connected = True

            logger.info(f"✅ STK连接成功，场景: {self.scenario.InstanceName}")
            return True

        except Exception as e:
            logger.error(f"❌ STK连接失败: {e}")
            return False

    def _create_new_scenario(self) -> bool:
        """创建新场景"""
        try:
            # 获取时间管理器
            from src.utils.time_manager import get_time_manager
            from src.utils.config_manager import get_config_manager

            config_manager = get_config_manager()
            time_manager = get_time_manager(config_manager)

            # 获取STK格式的时间
            start_time_stk, end_time_stk, epoch_time_stk = time_manager.get_stk_time_range()

            # 使用STK的NewScenario方法创建场景
            scenario_name = "RefactoredScenario"
            self.root.NewScenario(scenario_name)
            logger.info(f"✅ 创建新场景: {scenario_name}")

            # 获取新创建的场景
            self.scenario = self.root.CurrentScenario

            # 设置场景时间
            self.scenario.SetTimePeriod(start_time_stk, end_time_stk)
            logger.info(f"✅ 场景时间设置: {start_time_stk} - {end_time_stk}")

            return True

        except Exception as e:
            logger.error(f"❌ 创建场景失败: {e}")
            return False

    def should_skip_creation(self) -> bool:
        """检查是否应该跳过创建 - 检测已存在的卫星"""
        try:
            if not self.scenario:
                return False

            # 检查场景中是否已有卫星
            satellite_count = 0
            for i in range(self.scenario.Children.Count):
                child = self.scenario.Children.Item(i)
                if getattr(child, 'ClassName', '') == 'Satellite':
                    satellite_count += 1

            # 如果已有卫星，跳过创建
            if satellite_count > 0:
                logger.info(f"🔍 检测到场景中已有 {satellite_count} 颗卫星，跳过星座创建")
                return True

            return False

        except Exception as e:
            logger.warning(f"⚠️ 检查现有卫星失败: {e}")
            return False

    def set_scenario_time(self, start_time: str, end_time: str) -> bool:
        """设置场景时间 - 兼容性方法"""
        try:
            if self.scenario:
                self.scenario.SetTimePeriod(start_time, end_time)
                logger.info(f"✅ 场景时间更新: {start_time} - {end_time}")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ 设置场景时间失败: {e}")
            return False
    
    def create_satellite(self, satellite_id: str, orbital_params: Dict) -> bool:
        """
        创建卫星 - 重构版本，基于实际使用的方法
        """
        if not self.scenario or not self.is_connected:
            logger.error("STK未连接")
            return False
        
        try:
            # 创建卫星对象
            self.scenario.Children.New(self.object_types["satellite"], satellite_id)
            logger.info(f"🛰️ 创建卫星对象: {satellite_id}")
            
            # 等待对象创建
            time.sleep(self.wait_times["object_creation"])
            
            # 获取卫星对象
            satellite = self.scenario.Children.Item(satellite_id)
            
            # 设置传播器类型
            satellite.SetPropagatorType(self.propagator_types["j2_perturbation"])
            logger.info("✅ 传播器类型设置成功")
            
            # 设置轨道参数
            if orbital_params:
                success = self._set_satellite_orbit_optimized(satellite, orbital_params)
                if not success:
                    logger.error(f"❌ 轨道参数设置失败: {satellite_id}")
                    return False
            
            # 设置地面轨迹显示
            self._configure_ground_track(satellite)
            
            logger.info(f"✅ 卫星创建成功: {satellite_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建卫星失败 {satellite_id}: {e}")
            return False
    
    def _set_satellite_orbit_optimized(self, satellite, orbital_params: Dict) -> bool:
        """
        优化的轨道设置方法 - 基于日志分析的实际成功方法
        """
        try:
            # 验证参数
            validated_params = self._validate_orbital_parameters(orbital_params)
            if not validated_params:
                return False
            
            # 提取参数
            semi_axis = validated_params.get('semi_axis') or validated_params.get('semi_major_axis')
            eccentricity = validated_params.get('eccentricity', 0.0)
            inclination = validated_params.get('inclination')
            raan = validated_params.get('raan')
            arg_of_perigee = validated_params.get('arg_of_perigee', validated_params.get('argument_of_perigee'))
            mean_anomaly = validated_params.get('mean_anomaly')
            
            # 方法1: Keplerian高度方法 (日志显示最常成功)
            try:
                logger.info("🔄 使用Keplerian高度方法...")
                keplerian = satellite.Propagator.InitialState.Representation.ConvertTo(1)
                
                # 设置参数类型
                keplerian.SizeShapeType = 0  # eSizeShapeAltitude
                keplerian.LocationType = 5   # eLocationTrueAnomaly
                keplerian.Orientation.AscNodeType = 0  # eAscNodeLAN
                
                # 设置轨道参数
                keplerian.SizeShape.PerigeeAltitude = semi_axis - 6371.0
                keplerian.SizeShape.ApogeeAltitude = semi_axis - 6371.0
                keplerian.Orientation.Inclination = inclination
                keplerian.Orientation.ArgOfPerigee = arg_of_perigee
                keplerian.Orientation.AscNode.Value = raan
                keplerian.Location.Value = mean_anomaly
                
                # 应用设置
                satellite.Propagator.InitialState.Representation.Assign(keplerian)
                satellite.SetPropagatorType(1)  # J2摄动
                satellite.Propagator.Propagate()
                
                logger.info("✅ Keplerian高度方法成功")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ Keplerian方法失败: {e}")
            
            # 方法2: AssignClassical备用方法 (日志显示在except中使用)
            try:
                logger.info("🔄 使用AssignClassical备用方法...")
                satellite.SetPropagatorType(1)
                
                # 转换单位
                semi_major_axis_m = semi_axis * 1000.0
                inclination_rad = math.radians(inclination)
                raan_rad = math.radians(raan)
                arg_of_perigee_rad = math.radians(arg_of_perigee)
                mean_anomaly_rad = math.radians(mean_anomaly)
                
                # 使用AssignClassical
                representation = satellite.Propagator.InitialState.Representation
                representation.AssignClassical(
                    3, semi_major_axis_m, eccentricity, inclination_rad,
                    raan_rad, arg_of_perigee_rad, mean_anomaly_rad
                )
                
                satellite.Propagator.Propagate()
                logger.info("✅ AssignClassical备用方法成功")
                return True
                
            except Exception as e:
                logger.warning(f"⚠️ AssignClassical方法失败: {e}")
            
            # 方法3: 基本传播 (最后备用)
            try:
                logger.info("🔄 使用基本传播...")
                satellite.Propagator.Propagate()
                logger.warning("⚠️ 使用默认参数完成传播")
                return True
            except Exception as e:
                logger.error(f"❌ 基本传播失败: {e}")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ 轨道设置失败: {e}")
            return False
    
    def _validate_orbital_parameters(self, orbital_params: Dict) -> Optional[Dict]:
        """验证轨道参数"""
        THRESHOLDS = {
            'semi_axis': {'min': 6371.0, 'max': 50000.0},
            'semi_major_axis': {'min': 6371.0, 'max': 50000.0},
            'eccentricity': {'min': 0.0, 'max': 0.999},
            'inclination': {'min': 0.0, 'max': 180.0},
            'arg_of_perigee': {'min': 0.0, 'max': 360.0},
            'argument_of_perigee': {'min': 0.0, 'max': 360.0},
            'raan': {'min': 0.0, 'max': 360.0},
            'mean_anomaly': {'min': 0.0, 'max': 360.0}
        }
        
        validated = {}
        for name, value in orbital_params.items():
            if name in THRESHOLDS:
                threshold = THRESHOLDS[name]
                if threshold['min'] <= value <= threshold['max']:
                    validated[name] = value
                    logger.info(f"✅ 参数 {name} = {value} 验证通过")
                else:
                    logger.warning(f"⚠️ 参数 {name} = {value} 超出范围 [{threshold['min']}, {threshold['max']}]")
                    validated[name] = value  # 仍然使用，但记录警告
            else:
                validated[name] = value
        
        return validated
    
    def _configure_ground_track(self, satellite):
        """配置地面轨迹显示"""
        try:
            passdata = satellite.Graphics.PassData
            groundTrack = passdata.GroundTrack
            groundTrack.SetLeadDataType(1)  # eDataAll
            groundTrack.SetTrailSameAsLead()
            logger.info("✅ 地面轨迹配置成功")
        except Exception as e:
            logger.warning(f"⚠️ 地面轨迹配置失败: {e}")
    
    def create_sensor(self, satellite_id: str, sensor_params: Dict) -> bool:
        """
        创建传感器 - 重构版本，基于实际使用的方法
        """
        if not self.scenario or not self.is_connected:
            logger.error("STK未连接")
            return False
        
        try:
            # 获取卫星对象
            satellite = self._find_satellite(satellite_id)
            if not satellite:
                logger.error(f"❌ 卫星 {satellite_id} 不存在")
                return False
            
            # 创建传感器
            sensor_id = f"{satellite_id}_Payload"
            sensor = satellite.Children.New(self.object_types["sensor"], sensor_id)
            logger.info(f"🔭 创建传感器: {sensor_id}")
            
            # 等待创建完成
            time.sleep(self.wait_times["sensor_creation"])
            
            # 配置传感器参数
            success = self._configure_sensor_optimized(sensor, sensor_params)
            if success:
                logger.info(f"✅ 传感器创建成功: {sensor_id}")
                return True
            else:
                logger.warning(f"⚠️ 传感器配置部分失败，但对象已创建: {sensor_id}")
                return True  # 对象已创建，返回成功
            
        except Exception as e:
            logger.error(f"❌ 创建传感器失败: {e}")
            return False
    
    def _find_satellite(self, satellite_id: str):
        """查找卫星对象"""
        try:
            # 兼容带 "Satellite/" 前缀的卫星ID
            if satellite_id.startswith("Satellite/"):
                target_name = satellite_id.split("/", 1)[1]
            else:
                target_name = satellite_id

            # 列出所有卫星对象进行调试
            satellites_found = []
            for i in range(self.scenario.Children.Count):
                child = self.scenario.Children.Item(i)
                child_class = getattr(child, 'ClassName', None)
                child_name = getattr(child, 'InstanceName', None)

                if child_class == 'Satellite':
                    satellites_found.append(child_name)
                    if child_name == target_name:
                        logger.debug(f"✅ 找到匹配的卫星: {target_name}")
                        return child

            logger.warning(f"⚠️ 未找到卫星 {satellite_id} (目标名称: {target_name})")
            logger.warning(f"   可用卫星: {satellites_found}")
            return None
        except Exception as e:
            logger.error(f"❌ 查找卫星失败 {satellite_id}: {e}")
            return None
    
    def _configure_sensor_optimized(self, sensor, sensor_params: Dict) -> bool:
        """
        优化的传感器配置 - 基于实际使用的方法
        """
        success_count = 0
        total_configs = 3
        
        # 1. 配置圆锥视场
        try:
            self._configure_conic_pattern_optimized(sensor, sensor_params)
            success_count += 1
            logger.info("✅ 圆锥视场配置成功")
        except Exception as e:
            logger.warning(f"⚠️ 圆锥视场配置失败: {e}")
        
        # 2. 配置指向参数
        try:
            self._configure_pointing_optimized(sensor, sensor_params)
            success_count += 1
            logger.info("✅ 指向参数配置成功")
        except Exception as e:
            logger.warning(f"⚠️ 指向参数配置失败: {e}")
        
        # 3. 配置约束参数
        try:
            self._configure_constraints_optimized(sensor, sensor_params)
            success_count += 1
            logger.info("✅ 约束参数配置成功")
        except Exception as e:
            logger.warning(f"⚠️ 约束参数配置失败: {e}")
        
        return success_count >= 2  # 至少2/3成功才算成功
    
    def _configure_conic_pattern_optimized(self, sensor, params: Dict):
        """配置圆锥视场参数 - 基于原始代码的正确方法"""

        # 获取参数
        inner_cone_half_angle = params.get("inner_cone_half_angle", 0.0)
        outer_cone_half_angle = params.get("outer_cone_half_angle", 45.0)
        clockwise_angle_min = params.get("clockwise_angle_min", 0.0)
        clockwise_angle_max = params.get("clockwise_angle_max", 360.0)

        try:
            # 设置传感器模式为圆锥
            sensor.SetPatternType(0)  # eSnCone
            logger.info("✓ 传感器模式设置为圆锥")

            # 等待模式设置完成
            time.sleep(0.2)

            # 获取Pattern对象
            pattern = sensor.Pattern
            logger.info(f"✓ 获取Pattern对象成功，类型: {type(pattern)}")

            # 设置圆锥参数 - 使用原始代码的正确属性名
            try:
                # 设置外锥角
                pattern.OuterConeHalfAngle = outer_cone_half_angle
                logger.info(f"✓ 设置外锥角成功: {outer_cone_half_angle}°")

                # 设置内锥角
                pattern.InnerConeHalfAngle = inner_cone_half_angle
                logger.info(f"✓ 设置内锥角成功: {inner_cone_half_angle}°")

                # 设置时钟角约束
                pattern.MinimumClockAngle = clockwise_angle_min
                pattern.MaximumClockAngle = clockwise_angle_max
                logger.info(f"✓ 设置时钟角约束成功: {clockwise_angle_min}° - {clockwise_angle_max}°")

            except Exception as param_error:
                logger.warning(f"⚠️ 设置圆锥参数失败: {param_error}")
                # 尝试只设置外锥角
                try:
                    pattern.OuterConeHalfAngle = outer_cone_half_angle
                    logger.info(f"✓ 单独设置外锥角成功: {outer_cone_half_angle}°")
                except Exception as outer_error:
                    logger.error(f"❌ 设置外锥角失败: {outer_error}")
                    # 尝试备用方法
                    if hasattr(sensor, 'ConeAngle'):
                        sensor.ConeAngle = outer_cone_half_angle
                        logger.info(f"✓ 使用基本ConeAngle设置成功: {outer_cone_half_angle}°")
                    else:
                        raise Exception("所有圆锥角设置方法都失败")

        except Exception as e:
            logger.error(f"❌ 圆锥视场参数设置异常: {e}")
            raise
    
    def _configure_pointing_optimized(self, sensor, params: Dict):
        """配置指向参数 - 基于实际使用的方法"""
        pointing = params.get('pointing', {})
        azimuth = pointing.get('azimuth', 0.0)
        elevation = pointing.get('elevation', 90.0)
        
        # 使用STK官方推荐方法
        sensor.CommonTasks.SetPointingFixedAzEl(azimuth, elevation, 1)
    
    def _configure_constraints_optimized(self, sensor, params: Dict):
        """配置约束参数 - 基于实际使用的方法"""
        time.sleep(0.5)  # 等待传感器初始化

        try:
            constraints = sensor.AccessConstraints

            # 支持两种约束参数格式
            constraint_params = params.get('constraints', {})
            constraints_range = params.get('constraints_range', {})

            # 合并两种格式的约束参数
            if constraints_range:
                constraint_params.update({
                    'min_range_km': constraints_range.get('min_range', 0),
                    'max_range_km': constraints_range.get('max_range', 5000)
                })

            # 距离约束
            if 'min_range_km' in constraint_params and 'max_range_km' in constraint_params:
                try:
                    range_constraint = constraints.AddConstraint(34)  # eCstrRange
                    range_constraint.EnableMin = True
                    range_constraint.EnableMax = True
                    range_constraint.Min = constraint_params['min_range_km']
                    range_constraint.Max = constraint_params['max_range_km']
                    logger.info(f"✓ 距离约束设置成功: {constraint_params['min_range_km']}-{constraint_params['max_range_km']}km")
                except Exception as range_error:
                    logger.warning(f"⚠️ 距离约束设置失败: {range_error}")

        except Exception as e:
            logger.warning(f"⚠️ 约束配置失败: {e}")



    # def get_satellite_position(self, satellite_id: str, time_str: str, timeout: int = 30) -> Optional[Dict]:
    #     """
    #     获取卫星位置 - 基于原始成功实现的多方法尝试

    #     Args:
    #         satellite_id: 卫星ID
    #         time_str: 时间字符串
    #         timeout: 超时时间(秒)，默认30秒
    #     """
    #     try:
    #         logger.info(f"🛰️ 开始获取卫星 {satellite_id} 在时间 {time_str} 的位置")

    #         satellite = self._find_satellite(satellite_id)
    #         if not satellite:
    #             logger.error(f"❌ 未找到卫星 {satellite_id}")
    #             return None

    #         logger.info(f"✅ 找到卫星对象 {satellite_id}")

    #         # 检查传播器状态并传播
    #         try:
    #             propagator = satellite.Propagator
    #             logger.info(f"📡 卫星 {satellite_id} 获取到传播器对象")

    #             # 尝试获取传播器名称（可选）
    #             try:
    #                 propagator_name = propagator.PropagatorName
    #                 logger.info(f"📡 卫星 {satellite_id} 传播器类型: {propagator_name}")
    #             except:
    #                 logger.info(f"📡 卫星 {satellite_id} 传播器类型: 未知")

    #             # 执行传播
    #             propagator.Propagate()
    #             logger.info(f"✅ 卫星 {satellite_id} 传播完成")
    #         except Exception as prop_e:
    #             logger.error(f"❌ 卫星 {satellite_id} 传播失败: {prop_e}")
    #             # 尝试不传播直接获取位置
    #             logger.info(f"🔄 尝试不传播直接获取位置...")
    #             pass  # 继续尝试获取位置

    #         # 使用传入的时间参数，正确处理时间偏移
    #         try:
    #             # 尝试将时间字符串转换为数字（时间偏移）
    #             time_offset_seconds = float(time_str)
    #             # 如果是时间偏移（秒），需要转换为STK时间格式
    #             from src.utils.time_manager import get_time_manager
    #             time_manager = get_time_manager()
    #             target_time = time_manager.start_time + timedelta(seconds=time_offset_seconds)
    #             # 转换为STK时间格式
    #             stk_time = target_time.strftime("%d %b %Y %H:%M:%S.000")
    #             logger.info(f"⏰ 时间偏移 {time_offset_seconds}s -> STK时间: {stk_time}")
    #             logger.info(f"📅 场景时间范围: {time_manager.start_time} - {time_manager.end_time}")

    #             # 检查时间是否在场景范围内
    #             if target_time < time_manager.start_time or target_time > time_manager.end_time:
    #                 logger.warning(f"⚠️ 目标时间 {target_time} 超出场景时间范围")

    #         except (ValueError, TypeError):
    #             # 如果不是数字，假设已经是STK时间格式
    #             stk_time = str(time_str)
    #             logger.info(f"⏰ 使用直接时间格式: {stk_time}")

    #         # 方法1：使用Cartesian Position数据提供者
    #         position_data = None
    #         logger.info(f"🔍 方法1: 尝试使用Cartesian Position获取卫星 {satellite_id} 位置")
    #         try:
    #             dp = satellite.DataProviders.Item("Cartesian Position")
    #             logger.info(f"📊 获取到Cartesian Position数据提供者")
    #             result = dp.Exec(stk_time, stk_time)
    #             logger.info(f"📊 执行数据提供者查询完成")

    #             if result and result.DataSets.Count > 0:
    #                 dataset = result.DataSets.Item(0)
    #                 logger.info(f"📊 数据集数量: {result.DataSets.Count}, 行数: {dataset.RowCount}")
    #                 if dataset.RowCount > 0:
    #                     x = dataset.GetValue(0, 1)
    #                     y = dataset.GetValue(0, 2)
    #                     z = dataset.GetValue(0, 3)
    #                     position_data = {
    #                         'time': stk_time,
    #                         'x': float(x),
    #                         'y': float(y),
    #                         'z': float(z)
    #                     }
    #                     logger.info(f"✅ 方法1成功获取卫星 {satellite_id} 位置: x={x:.2f}, y={y:.2f}, z={z:.2f}")
    #                 else:
    #                     logger.warning(f"⚠️ 方法1: 数据集为空")
    #             else:
    #                 logger.warning(f"⚠️ 方法1: 无数据集或数据集数量为0")
    #         except Exception as e1:
    #             logger.error(f"❌ 方法1失败: {e1}")

    #         # 方法2：如果方法1失败，尝试使用LLA Position
    #         if position_data is None:
    #             logger.info(f"🔍 方法2: 尝试使用LLA Position获取卫星 {satellite_id} 位置")
    #             try:
    #                 dp = satellite.DataProviders.Item("LLA Position")
    #                 logger.info(f"📊 获取到LLA Position数据提供者")
    #                 result = dp.Exec(stk_time, stk_time)
    #                 logger.info(f"📊 执行LLA数据提供者查询完成")

    #                 if result and result.DataSets.Count > 0:
    #                     dataset = result.DataSets.Item(0)
    #                     logger.info(f"📊 LLA数据集数量: {result.DataSets.Count}, 行数: {dataset.RowCount}")
    #                     if dataset.RowCount > 0:
    #                         lat = dataset.GetValue(0, 1)
    #                         lon = dataset.GetValue(0, 2)
    #                         alt = dataset.GetValue(0, 3)
    #                         position_data = {
    #                             'time': stk_time,
    #                             'latitude': float(lat),
    #                             'longitude': float(lon),
    #                             'altitude': float(alt)
    #                         }
    #                         logger.info(f"✅ 方法2成功获取卫星 {satellite_id} 位置: lat={lat:.6f}°, lon={lon:.6f}°, alt={alt:.2f}km")
    #                     else:
    #                         logger.warning(f"⚠️ 方法2: LLA数据集为空")
    #                 else:
    #                     logger.warning(f"⚠️ 方法2: 无LLA数据集或数据集数量为0")
    #             except Exception as e2:
    #                 logger.error(f"❌ 方法2失败: {e2}")

    #         # 方法3：如果前两种方法都失败，使用传感器位置（如果存在）
    #         if position_data is None:
    #             logger.info(f"🔍 方法3: 尝试使用传感器位置获取卫星 {satellite_id} 位置")
    #             try:
    #                 sensor = None
    #                 logger.info(f"🔍 搜索卫星 {satellite_id} 的传感器，子对象数量: {satellite.Children.Count}")
    #                 for i in range(satellite.Children.Count):
    #                     child = satellite.Children.Item(i)
    #                     if hasattr(child, 'ClassName') and child.ClassName == 'Sensor':
    #                         sensor = child
    #                         logger.info(f"✅ 找到传感器: {child.InstanceName}")
    #                         break

    #                 if sensor:
    #                     logger.info(f"📊 使用传感器获取位置数据")
    #                     dp = sensor.DataProviders.Item("Points(ICRF)").Group('Center')
    #                     result = dp.Exec(stk_time, stk_time, 60)
    #                     logger.info(f"📊 传感器数据查询完成")

    #                     if result.DataSets.Count > 0:
    #                         times = result.DataSets.GetDataSetByName("Time").GetValues()
    #                         x_pos = result.DataSets.GetDataSetByName("x").GetValues()
    #                         y_pos = result.DataSets.GetDataSetByName("y").GetValues()
    #                         z_pos = result.DataSets.GetDataSetByName("z").GetValues()
    #                         logger.info(f"📊 传感器数据集: 时间点数={len(times) if times else 0}")
    #                         if times and x_pos and y_pos and z_pos and len(times) > 0:
    #                             position_data = {
    #                                 'time': stk_time,
    #                                 'x': float(x_pos[0]),
    #                                 'y': float(y_pos[0]),
    #                                 'z': float(z_pos[0])
    #                             }
    #                             logger.info(f"✅ 方法3成功获取卫星 {satellite_id} 位置: x={x_pos[0]:.2f}, y={y_pos[0]:.2f}, z={z_pos[0]:.2f}")
    #                         else:
    #                             logger.warning(f"⚠️ 方法3: 传感器数据不完整")
    #                     else:
    #                         logger.warning(f"⚠️ 方法3: 传感器无数据集")
    #                 else:
    #                     logger.warning(f"⚠️ 方法3: 卫星 {satellite_id} 没有传感器")
    #             except Exception as e3:
    #                 logger.error(f"❌ 方法3失败: {e3}")

    #         # 最终结果
    #         if position_data:
    #             logger.info(f"🎉 成功获取卫星 {satellite_id} 位置数据: {position_data}")
    #             return position_data
    #         else:
    #             logger.error(f"❌ 所有方法都无法获取卫星 {satellite_id} 的位置数据")
    #             logger.error(f"❌ 位置获取失败详情:")
    #             logger.error(f"   - 卫星ID: {satellite_id}")
    #             logger.error(f"   - 请求时间: {time_str}")
    #             logger.error(f"   - STK时间: {stk_time}")
    #             logger.error(f"   - 传播器状态: 已检查")
    #             return None

    #     except Exception as e:
    #         logger.error(f"❌ 获取卫星位置失败: {e}")
    #         return None

    def get_satellite_position(self, satellite_id: str, time_str: str, timeout: int = 30) -> Optional[Dict]:
        """
        获取卫星位置 - 基于原始成功实现的多方法尝试

        Args:
            satellite_id: 卫星ID
            time_str: 时间字符串
            timeout: 超时时间(秒)，默认30秒
        """
        try:
            logger.info(f"🛰️ 开始获取卫星 {satellite_id} 在时间 {time_str} 的位置")

            satellite = self._find_satellite(satellite_id)
            if not satellite:
                logger.error(f"❌ 未找到卫星 {satellite_id}")
                return None

            logger.info(f"✅ 找到卫星对象 {satellite_id}")

            # 检查传播器状态并传播
            try:
                propagator = satellite.Propagator
                logger.info(f"📡 卫星 {satellite_id} 获取到传播器对象")

                # 尝试获取传播器名称（可选）
                try:
                    propagator_name = propagator.PropagatorName
                    logger.info(f"📡 卫星 {satellite_id} 传播器类型: {propagator_name}")
                except:
                    logger.info(f"📡 卫星 {satellite_id} 传播器类型: 未知")

                # 执行传播
                propagator.Propagate()
                logger.info(f"✅ 卫星 {satellite_id} 传播完成")
            except Exception as prop_e:
                logger.error(f"❌ 卫星 {satellite_id} 传播失败: {prop_e}")
                # 尝试不传播直接获取位置
                logger.info(f"🔄 尝试不传播直接获取位置...")
                pass  # 继续尝试获取位置

            # 使用传入的时间参数，正确处理时间偏移
            try:
                # 尝试将时间字符串转换为数字（时间偏移）
                time_offset_seconds = float(time_str)
                # 如果是时间偏移（秒），需要转换为STK时间格式
                from src.utils.time_manager import get_time_manager
                time_manager = get_time_manager()
                target_time = time_manager.start_time + timedelta(seconds=time_offset_seconds)
                # 转换为STK时间格式
                stk_time = target_time.strftime("%d %b %Y %H:%M:%S.000")
                logger.info(f"⏰ 时间偏移 {time_offset_seconds}s -> STK时间: {stk_time}")
                logger.info(f"📅 场景时间范围: {time_manager.start_time} - {time_manager.end_time}")

                # 检查时间是否在场景范围内
                if target_time < time_manager.start_time or target_time > time_manager.end_time:
                    logger.warning(f"⚠️ 目标时间 {target_time} 超出场景时间范围")

            except (ValueError, TypeError):
                # 如果不是数字，假设已经是STK时间格式
                stk_time = str(time_str)
                logger.info(f"⏰ 使用直接时间格式: {stk_time}")
            position_data = None
            # 方法3：如果前两种方法都失败，使用传感器位置（如果存在）
            if position_data is None:
                logger.info(f"🔍 方法3: 尝试使用传感器位置获取卫星 {satellite_id} 位置")
                try:
                    sensor = None
                    logger.info(f"🔍 搜索卫星 {satellite_id} 的传感器，子对象数量: {satellite.Children.Count}")
                    for i in range(satellite.Children.Count):
                        child = satellite.Children.Item(i)
                        if hasattr(child, 'ClassName') and child.ClassName == 'Sensor':
                            sensor = child
                            logger.info(f"✅ 找到传感器: {child.InstanceName}")
                            break

                    if sensor:
                        logger.info(f"📊 使用传感器获取位置数据")
                        dp = sensor.DataProviders.Item("Points(ICRF)").Group('Center')
                        result = dp.Exec(stk_time, stk_time, 60)
                        logger.info(f"📊 传感器数据查询完成")

                        if result.DataSets.Count > 0:
                            times = result.DataSets.GetDataSetByName("Time").GetValues()
                            x_pos = result.DataSets.GetDataSetByName("x").GetValues()
                            y_pos = result.DataSets.GetDataSetByName("y").GetValues()
                            z_pos = result.DataSets.GetDataSetByName("z").GetValues()
                            logger.info(f"📊 传感器数据集: 时间点数={len(times) if times else 0}")
                            if times and x_pos and y_pos and z_pos and len(times) > 0:
                                position_data = {
                                    'time': stk_time,
                                    'x': float(x_pos[0]),
                                    'y': float(y_pos[0]),
                                    'z': float(z_pos[0])
                                }
                                logger.info(f"✅ 方法3成功获取卫星 {satellite_id} 位置: x={x_pos[0]:.2f}, y={y_pos[0]:.2f}, z={z_pos[0]:.2f}")
                            else:
                                logger.warning(f"⚠️ 方法3: 传感器数据不完整")
                        else:
                            logger.warning(f"⚠️ 方法3: 传感器无数据集")
                    else:
                        logger.warning(f"⚠️ 方法3: 卫星 {satellite_id} 没有传感器")
                except Exception as e3:
                    logger.error(f"❌ 方法3失败: {e3}")

            # 最终结果
            if position_data:
                logger.info(f"🎉 成功获取卫星 {satellite_id} 位置数据: {position_data}")
                return position_data
            else:
                logger.error(f"❌ 所有方法都无法获取卫星 {satellite_id} 的位置数据")
                logger.error(f"❌ 位置获取失败详情:")
                logger.error(f"   - 卫星ID: {satellite_id}")
                logger.error(f"   - 请求时间: {time_str}")
                logger.error(f"   - STK时间: {stk_time}")
                logger.error(f"   - 传播器状态: 已检查")
                return None

        except Exception as e:
            logger.error(f"❌ 获取卫星位置失败: {e}")
            return None

    def check_stk_server_status(self) -> bool:
        """
        检查STK服务器状态 - 基于实际大量使用的方法
        """
        try:
            if not self.stk or not self.root:
                return False

            # 尝试访问场景信息
            scenario_name = self.scenario.InstanceName
            logger.debug(f"STK服务器状态正常，场景: {scenario_name}")
            return True

        except Exception as e:
            logger.warning(f"⚠️ STK服务器状态检查失败: {e}")
            return False

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            status = {
                'connection_status': self.is_connected,
                'stk_available': self.check_stk_server_status(),
                'scenario_name': self.scenario.InstanceName if self.scenario else None,
                'satellite_count': 0,
                'sensor_count': 0
            }

            if self.scenario:
                # 统计对象数量
                for i in range(self.scenario.Children.Count):
                    child = self.scenario.Children.Item(i)
                    class_name = getattr(child, 'ClassName', '')
                    if class_name == 'Satellite':
                        status['satellite_count'] += 1
                        # 统计传感器
                        for j in range(child.Children.Count):
                            sensor_child = child.Children.Item(j)
                            if getattr(sensor_child, 'ClassName', '') == 'Sensor':
                                status['sensor_count'] += 1

            return status

        except Exception as e:
            logger.error(f"❌ 获取系统状态失败: {e}")
            return {'connection_status': False, 'error': str(e)}

    def shutdown(self) -> bool:
        """关闭STK连接"""
        try:
            if self.stk:
                logger.info("🔌 关闭STK连接...")
                self.stk = None
                self.root = None
                self.scenario = None
                self.is_connected = False
                logger.info("✅ STK连接已关闭")
            return True
        except Exception as e:
            logger.error(f"❌ 关闭STK连接失败: {e}")
            return False
