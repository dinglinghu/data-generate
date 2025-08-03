#!/usr/bin/env python3
"""
STK管理器模块 - 清理版
负责STK软件连接和对象管理，只保留真正使用的方法
基于实际运行验证，删除了所有未使用的方法
"""

import logging
import win32com.client
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class STKManager:
    """STK管理器 - 清理版，只保留核心功能"""
    
    def __init__(self):
        """初始化STK管理器"""
        self.root = None
        self.scenario = None
        self.app = None
        self.skip_creation = False
        
        # 获取配置
        from src.utils.config_manager import get_config_manager
        config_manager = get_config_manager()

        # STK配置
        self.stk_config = config_manager.get_stk_config()
        self.scenario_name = self.stk_config.get('scenario_name', 'MetaTaskScenario')
        self.scenario_start_time = self.stk_config.get('scenario_start_time', '23 Jul 2025 04:00:00.000')
        self.scenario_duration_hours = self.stk_config.get('scenario_duration_hours', 24)
        self.connection_timeout = self.stk_config.get('connection_timeout', 30)
        
        logger.info("STK管理器初始化完成")
        
    def connect(self) -> bool:
        """连接到STK - 被使用的方法"""
        try:
            logger.info("🔗 连接STK...")
            
            # 连接到STK应用程序
            self.app = win32com.client.Dispatch("STK12.Application")
            self.app.Visible = True
            self.app.UserControl = True
            
            # 获取根对象
            self.root = self.app.Personality2
            
            # 创建或获取场景
            self._setup_scenario()
            
            logger.info("✅ STK连接成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ STK连接失败: {e}")
            return False

    def should_skip_creation(self) -> bool:
        """检查是否应该跳过创建步骤 - 被使用的方法"""
        return self.skip_creation

    def create_satellite(self, satellite_id: str, orbital_params: Dict) -> bool:
        """创建卫星 - 被使用的方法"""
        try:
            logger.info(f"🛰️ 创建卫星: {satellite_id}")
            
            # 创建卫星对象
            satellite = self.scenario.Children.New(18, satellite_id)  # eSatellite
            
            # 设置轨道参数
            self._set_orbital_parameters(satellite, orbital_params)
            
            # 传播轨道
            satellite.Propagate()
            
            logger.info(f"✅ 卫星创建成功: {satellite_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 卫星创建失败 {satellite_id}: {e}")
            return False

    def create_sensor(self, satellite_id: str, sensor_params: Dict) -> bool:
        """为卫星创建载荷（传感器）- 被使用的方法"""
        try:
            logger.info(f"📡 为卫星 {satellite_id} 创建传感器")
            
            # 获取卫星对象
            satellite = self.root.GetObjectFromPath(f"Satellite/{satellite_id}")
            
            # 创建传感器
            sensor_name = sensor_params.get("name", f"{satellite_id}_Sensor")
            sensor = satellite.Children.New(20, sensor_name)  # eSensor
            
            # 设置传感器参数
            sensor.CommonTasks.SetPatternSimpleConic(
                sensor_params.get("cone_angle", 30.0),  # 锥角
                sensor_params.get("clock_angle", 0.0)   # 时钟角
            )
            
            logger.info(f"✅ 传感器创建成功: {sensor_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 传感器创建失败 {satellite_id}: {e}")
            return False

    def get_satellite_position(self, satellite_id: str, time_shift: float = 0) -> Optional[Dict]:
        """获取卫星位置 - 被使用的方法"""
        try:
            logger.debug(f"📍 获取卫星位置: {satellite_id}")
            
            # 获取卫星对象
            satellite = self.root.GetObjectFromPath(f"Satellite/{satellite_id}")
            
            # 计算查询时间
            scenario_start = self.scenario.StartTime
            query_time = self._calculate_query_time(scenario_start, time_shift)
            
            # 获取位置数据
            position_provider = satellite.DataProviders.Item("Cartesian Position")
            position_data = position_provider.Exec(query_time, query_time)
            
            if position_data.DataSets.Count > 0:
                dataset = position_data.DataSets.Item(0)
                if dataset.RowCount > 0:
                    x = dataset.GetValue(0, 1)  # X坐标
                    y = dataset.GetValue(0, 2)  # Y坐标
                    z = dataset.GetValue(0, 3)  # Z坐标
                    
                    return {
                        "satellite_id": satellite_id,
                        "time": query_time,
                        "position": {"x": x, "y": y, "z": z},
                        "success": True
                    }
            
            logger.warning(f"❌ 无法获取卫星位置: {satellite_id}")
            return None
            
        except Exception as e:
            logger.error(f"❌ 获取卫星位置失败 {satellite_id}: {e}")
            return None

    def _setup_scenario(self):
        """设置场景"""
        try:
            # 创建新场景
            self.scenario = self.root.Children.New(1, self.scenario_name)  # eScenario
            
            # 设置场景时间
            self.scenario.SetTimePeriod(
                self.scenario_start_time,
                self._calculate_end_time()
            )
            
            logger.info(f"✅ 场景创建成功: {self.scenario_name}")
            
        except Exception as e:
            logger.error(f"❌ 场景设置失败: {e}")
            raise

    def _calculate_end_time(self) -> str:
        """计算场景结束时间"""
        try:
            start_dt = datetime.strptime(self.scenario_start_time.split('.')[0], "%d %b %Y %H:%M:%S")
            end_dt = start_dt + timedelta(hours=self.scenario_duration_hours)
            return end_dt.strftime("%d %b %Y %H:%M:%S.000")
        except Exception as e:
            logger.error(f"时间计算失败: {e}")
            return self.scenario_start_time

    def _set_orbital_parameters(self, satellite, orbital_params: Dict):
        """设置轨道参数"""
        try:
            # 设置轨道类型为J2摄动
            satellite.SetPropagatorType(0)  # ePropagatorJ2Perturbation
            
            # 获取轨道参数
            semi_major_axis = orbital_params.get("semi_major_axis", 7000)  # km
            eccentricity = orbital_params.get("eccentricity", 0.0)
            inclination = orbital_params.get("inclination", 55.0)  # 度
            raan = orbital_params.get("raan", 0.0)  # 升交点赤经
            arg_perigee = orbital_params.get("argument_of_perigee", 0.0)  # 近地点幅角
            true_anomaly = orbital_params.get("true_anomaly", 0.0)  # 真近点角
            
            # 设置轨道要素
            keplerian = satellite.Propagator.InitialState.Representation.ConvertTo(0)  # eOrbitStateClassical
            keplerian.SizeShapeType = 0  # eSizeShapeSemimajorAxis
            keplerian.SemimajorAxis = semi_major_axis * 1000  # 转换为米
            keplerian.Eccentricity = eccentricity
            keplerian.Inclination = inclination
            keplerian.ArgOfPerigee = arg_perigee
            keplerian.RAAN = raan
            keplerian.TrueAnomaly = true_anomaly
            
            # 应用轨道参数
            satellite.Propagator.InitialState.Representation.Assign(keplerian)
            
        except Exception as e:
            logger.error(f"设置轨道参数失败: {e}")
            raise

    def _calculate_query_time(self, scenario_start: str, time_shift: float) -> str:
        """计算查询时间"""
        try:
            # 解析场景开始时间
            start_dt = datetime.strptime(scenario_start.split('.')[0], "%d %b %Y %H:%M:%S")
            
            # 添加时间偏移
            query_dt = start_dt + timedelta(hours=time_shift)
            
            # 转换回STK格式
            return query_dt.strftime("%d %b %Y %H:%M:%S.000")
            
        except Exception as e:
            logger.error(f"时间计算失败: {e}")
            return scenario_start
