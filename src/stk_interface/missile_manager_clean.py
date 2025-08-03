#!/usr/bin/env python3
"""
导弹管理器模块 - 清理版
负责导弹目标生成和管理，只保留真正使用的方法
基于实际运行验证，删除了所有未使用的方法
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class MissileManager:
    """导弹管理器 - 清理版，只保留核心功能"""
    
    def __init__(self, stk_manager):
        """初始化导弹管理器"""
        self.stk_manager = stk_manager
        self.missile_targets = {}
        
        # 获取配置
        from src.utils.config_manager import get_config_manager
        self.config_manager = get_config_manager()
        
        # 获取导弹配置
        self.missile_config = self.config_manager.get_missile_config()
        self.midcourse_altitude_threshold = self.missile_config.get("midcourse_altitude_threshold", 100)
        
        # 获取导弹管理配置
        self.missile_mgmt_config = self.config_manager.get_missile_management_config()

        logger.info(f"导弹管理器初始化完成，中段高度阈值: {self.midcourse_altitude_threshold}km")
        
    def add_missile_target(self, missile_id: str, launch_position: Dict[str, float], 
                          target_position: Dict[str, float], launch_sequence: int = 1):
        """添加导弹目标配置 - 被使用的方法"""
        self.missile_targets[missile_id] = {
            "launch_position": launch_position,
            "target_position": target_position,
            "launch_sequence": launch_sequence
        }
        logger.info(f"✅ 添加导弹目标配置: {missile_id}")
        
    def create_missile(self, missile_id: str, launch_time: datetime) -> bool:
        """创建导弹对象 - 被使用的方法"""
        try:
            logger.info(f"🚀 创建导弹对象: {missile_id}")
            
            # 获取导弹配置
            if missile_id not in self.missile_targets:
                logger.error(f"❌ 导弹配置不存在: {missile_id}")
                return False
            
            missile_config = self.missile_targets[missile_id]
            launch_pos = missile_config["launch_position"]
            target_pos = missile_config["target_position"]
            
            # 创建STK导弹对象
            missile = self.stk_manager.root.CurrentScenario.Children.New(18, missile_id)  # eMissile
            
            # 设置导弹轨迹
            missile.SetRouteType(0)  # ePropagatorBallistic
            
            # 设置发射点
            missile.Trajectory.LaunchLatitude = launch_pos["latitude"]
            missile.Trajectory.LaunchLongitude = launch_pos["longitude"]
            missile.Trajectory.LaunchAltitude = launch_pos.get("altitude", 0)
            
            # 设置目标点
            missile.Trajectory.ImpactLatitude = target_pos["latitude"]
            missile.Trajectory.ImpactLongitude = target_pos["longitude"]
            missile.Trajectory.ImpactAltitude = target_pos.get("altitude", 0)
            
            # 设置发射时间
            missile.Trajectory.LaunchTime = launch_time.strftime("%d %b %Y %H:%M:%S.000")
            
            # 传播轨道
            missile.Propagate()
            
            logger.info(f"✅ 导弹对象创建成功: {missile_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 导弹对象创建失败 {missile_id}: {e}")
            return False

    def create_single_missile_target(self, missile_scenario: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建单个导弹目标 - 被使用的主要接口方法"""
        try:
            missile_id = missile_scenario.get("missile_id")
            logger.info(f"🚀 创建单个导弹目标: {missile_id}")
            
            # 生成随机发射和目标位置
            launch_position = self._generate_random_launch_position()
            target_position = self._generate_random_target_position()
            
            # 添加导弹目标配置
            self.add_missile_target(missile_id, launch_position, target_position)
            
            # 生成发射时间
            launch_time = self._generate_launch_time()
            
            # 创建导弹对象
            success = self.create_missile(missile_id, launch_time)
            
            if success:
                result = {
                    "missile_id": missile_id,
                    "launch_position": launch_position,
                    "target_position": target_position,
                    "launch_time": launch_time.isoformat(),
                    "success": True
                }
                logger.info(f"✅ 导弹目标创建成功: {missile_id}")
                return result
            else:
                logger.error(f"❌ 导弹目标创建失败: {missile_id}")
                return None
                
        except Exception as e:
            logger.error(f"❌ 创建单个导弹目标失败: {e}")
            return None

    def _generate_random_launch_position(self) -> Dict[str, float]:
        """生成随机发射位置"""
        # 基于配置生成随机发射位置
        launch_config = self.missile_mgmt_config.get("launch_area", {})
        
        lat_min = launch_config.get("latitude_min", 30.0)
        lat_max = launch_config.get("latitude_max", 50.0)
        lon_min = launch_config.get("longitude_min", 100.0)
        lon_max = launch_config.get("longitude_max", 140.0)
        
        return {
            "latitude": random.uniform(lat_min, lat_max),
            "longitude": random.uniform(lon_min, lon_max),
            "altitude": 0.0
        }

    def _generate_random_target_position(self) -> Dict[str, float]:
        """生成随机目标位置"""
        # 基于配置生成随机目标位置
        target_config = self.missile_mgmt_config.get("target_area", {})
        
        lat_min = target_config.get("latitude_min", 35.0)
        lat_max = target_config.get("latitude_max", 45.0)
        lon_min = target_config.get("longitude_min", -125.0)
        lon_max = target_config.get("longitude_max", -70.0)
        
        return {
            "latitude": random.uniform(lat_min, lat_max),
            "longitude": random.uniform(lon_min, lon_max),
            "altitude": 0.0
        }

    def _generate_launch_time(self) -> datetime:
        """生成发射时间"""
        # 基于场景开始时间生成发射时间
        scenario_start = self.stk_manager.scenario.StartTime
        
        # 解析STK时间格式
        try:
            from datetime import datetime
            # STK时间格式: "23 Jul 2025 04:00:00.000"
            start_dt = datetime.strptime(scenario_start.split('.')[0], "%d %b %Y %H:%M:%S")
            
            # 在场景开始后的随机时间发射
            launch_delay_minutes = random.randint(5, 60)
            launch_time = start_dt + timedelta(minutes=launch_delay_minutes)
            
            return launch_time
            
        except Exception as e:
            logger.warning(f"时间解析失败，使用默认时间: {e}")
            return datetime.now() + timedelta(minutes=10)
