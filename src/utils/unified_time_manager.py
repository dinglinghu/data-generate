#!/usr/bin/env python3
"""
统一时间管理器 - 整合所有时间转换和管理功能

这个模块提供了系统中所有时间相关操作的统一接口，包括：
- 时间格式转换
- 时间范围管理
- STK时间接口
- 航天时间计算
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union
import random

from .aerospace_time_converter import AerospaceTimeConverter

logger = logging.getLogger(__name__)

class UnifiedTimeManager:
    """统一时间管理器"""
    
    def __init__(self, config_manager=None):
        """
        初始化统一时间管理器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 初始化航天时间转换器
        self.time_converter = AerospaceTimeConverter()
        
        # 时间配置
        self.start_time = None
        self.end_time = None
        self.epoch_time = None
        self.current_simulation_time = None
        
        # 时间间隔配置
        self.collection_interval_range = (300, 1800)  # 5-30分钟
        self.missile_launch_interval_range = (60, 300)  # 1-5分钟
        
        # 加载配置
        if config_manager:
            self._load_time_config()
    
    def _load_time_config(self):
        """加载时间配置"""
        try:
            sim_config = self.config_manager.get_simulation_config()
            
            # 获取时间格式
            time_format = sim_config.get("time_format", "%Y/%m/%d %H:%M:%S")
            
            # 解析仿真时间
            start_time_str = sim_config.get("start_time")
            end_time_str = sim_config.get("end_time")
            epoch_time_str = sim_config.get("epoch_time")
            
            if not all([start_time_str, end_time_str, epoch_time_str]):
                self.logger.error("❌ 配置文件中缺少必要的时间配置项")
                raise ValueError("仿真时间配置不完整")
            
            # 使用统一时间转换器解析配置时间
            self.start_time = self._parse_config_time(start_time_str, time_format)
            self.end_time = self._parse_config_time(end_time_str, time_format)
            self.epoch_time = self._parse_config_time(epoch_time_str, time_format)
            
            # 验证时间逻辑
            if self.start_time >= self.end_time:
                raise ValueError("开始时间必须早于结束时间")
            
            # 初始化当前仿真时间
            self.current_simulation_time = self.start_time
            
            # 加载间隔配置
            self._load_interval_config(sim_config)
            
            self.logger.info(f"⏰ 统一时间管理器初始化成功:")
            self.logger.info(f"   开始时间: {self.start_time}")
            self.logger.info(f"   结束时间: {self.end_time}")
            self.logger.info(f"   基准时间: {self.epoch_time}")
            self.logger.info(f"   场景时长: {self.end_time - self.start_time}")
            
        except Exception as e:
            self.logger.error(f"❌ 时间配置加载失败: {e}")
            raise
    
    def _parse_config_time(self, time_str: str, time_format: str) -> datetime:
        """
        解析配置文件中的时间字符串
        
        Args:
            time_str: 时间字符串
            time_format: 时间格式
            
        Returns:
            UTC时区的datetime对象
        """
        try:
            # 首先尝试使用配置格式解析
            dt = datetime.strptime(time_str, time_format)
            # 设置为UTC时区
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            # 如果配置格式失败，使用航天时间转换器
            dt = self.time_converter.parse_aerospace_time(time_str)
            if dt:
                return dt
            else:
                raise ValueError(f"无法解析时间字符串: {time_str}")
    
    def _load_interval_config(self, sim_config: Dict):
        """加载时间间隔配置"""
        try:
            # 数据采集间隔
            collection_config = sim_config.get("data_collection", {})
            interval_range = collection_config.get("interval_range", [300, 1800])
            self.collection_interval_range = tuple(interval_range)
            
            # 导弹发射间隔
            missile_config = sim_config.get("missile", {})
            launch_interval = missile_config.get("launch_interval_range", [60, 300])
            self.missile_launch_interval_range = tuple(launch_interval)
            
            self.logger.info(f"   采集间隔: {self.collection_interval_range[0]}-{self.collection_interval_range[1]}秒")
            self.logger.info(f"   发射间隔: {self.missile_launch_interval_range[0]}-{self.missile_launch_interval_range[1]}秒")
            
        except Exception as e:
            self.logger.warning(f"⚠️ 间隔配置加载失败，使用默认值: {e}")
    
    # ==================== 时间格式转换接口 ====================
    
    def to_stk_format(self, dt: datetime) -> str:
        """转换为STK格式"""
        return self.time_converter.format_for_stk(dt)
    
    def from_stk_format(self, stk_time_str: str) -> Optional[datetime]:
        """从STK格式解析"""
        return self.time_converter.parse_stk_time(stk_time_str)
    
    def to_iso_format(self, dt: datetime) -> str:
        """转换为ISO格式"""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    
    def from_iso_format(self, iso_str: str) -> Optional[datetime]:
        """从ISO格式解析"""
        return self.time_converter.parse_aerospace_time(iso_str)
    
    def to_julian_date(self, dt: datetime) -> float:
        """转换为Julian Date"""
        return self.time_converter.to_julian_date(dt)
    
    def from_julian_date(self, jd: float) -> datetime:
        """从Julian Date转换"""
        return self.time_converter.from_julian_date(jd)
    
    # ==================== STK接口 ====================
    
    def get_stk_time_range(self) -> Tuple[str, str, str]:
        """
        获取STK格式的时间范围
        
        Returns:
            (start_time_stk, end_time_stk, epoch_time_stk)
        """
        start_time_stk = self.to_stk_format(self.start_time)
        end_time_stk = self.to_stk_format(self.end_time)
        epoch_time_stk = self.to_stk_format(self.epoch_time)
        
        return start_time_stk, end_time_stk, epoch_time_stk
    
    def get_stk_current_time(self) -> str:
        """获取当前仿真时间的STK格式"""
        return self.to_stk_format(self.current_simulation_time)
    
    # ==================== 时间管理接口 ====================
    
    def advance_simulation_time(self, target_time: datetime):
        """推进仿真时间"""
        if target_time <= self.end_time:
            self.current_simulation_time = target_time
            self.logger.debug(f"🕐 仿真时间推进到: {self.current_simulation_time}")
        else:
            self.logger.warning(f"⚠️ 目标时间超出仿真范围: {target_time}")
    
    def get_next_collection_time(self) -> datetime:
        """获取下一次数据采集时间"""
        interval = random.randint(*self.collection_interval_range)
        next_time = self.current_simulation_time + timedelta(seconds=interval)
        
        if next_time > self.end_time:
            next_time = self.end_time
            
        self.logger.debug(f"🕐 下一次数据采集时间: {next_time} (间隔: {interval}秒)")
        return next_time
    
    def calculate_missile_launch_time(self, launch_sequence: int) -> Tuple[datetime, str]:
        """
        计算导弹发射时间
        
        Args:
            launch_sequence: 发射序号
            
        Returns:
            (发射时间datetime, 发射时间STK格式)
        """
        base_interval = random.randint(*self.missile_launch_interval_range)
        launch_offset = (launch_sequence - 1) * base_interval + random.randint(0, 300)
        
        launch_time = self.start_time + timedelta(seconds=launch_offset)
        
        if launch_time > self.end_time:
            launch_time = self.end_time - timedelta(minutes=30)
            
        launch_time_stk = self.to_stk_format(launch_time)
        
        self.logger.info(f"🚀 计算导弹发射时间: 序号{launch_sequence}, 时间{launch_time}")
        return launch_time, launch_time_stk
    
    # ==================== 时间验证接口 ====================
    
    def is_time_in_range(self, check_time: datetime) -> bool:
        """检查时间是否在仿真范围内"""
        return self.start_time <= check_time <= self.end_time
    
    def get_simulation_duration(self) -> timedelta:
        """获取仿真总时长"""
        return self.end_time - self.start_time
    
    def get_remaining_time(self) -> timedelta:
        """获取剩余仿真时间"""
        return max(timedelta(0), self.end_time - self.current_simulation_time)
    
    # ==================== 数据文件命名接口 ====================
    
    def get_data_filename(self, prefix: str = "data", extension: str = "json") -> str:
        """生成数据文件名"""
        timestamp = self.current_simulation_time.strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}.{extension}"
    
    def get_session_name(self, prefix: str = "session") -> str:
        """生成会话名称"""
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}"
    
    # ==================== 调试和信息接口 ====================
    
    def get_time_info(self) -> Dict:
        """获取时间管理器的详细信息"""
        return {
            "start_time": {
                "datetime": self.start_time,
                "stk_format": self.to_stk_format(self.start_time),
                "iso_format": self.to_iso_format(self.start_time),
                "julian_date": self.to_julian_date(self.start_time)
            },
            "end_time": {
                "datetime": self.end_time,
                "stk_format": self.to_stk_format(self.end_time),
                "iso_format": self.to_iso_format(self.end_time),
                "julian_date": self.to_julian_date(self.end_time)
            },
            "current_time": {
                "datetime": self.current_simulation_time,
                "stk_format": self.to_stk_format(self.current_simulation_time),
                "iso_format": self.to_iso_format(self.current_simulation_time),
                "julian_date": self.to_julian_date(self.current_simulation_time)
            },
            "duration": {
                "total_seconds": self.get_simulation_duration().total_seconds(),
                "total_hours": self.get_simulation_duration().total_seconds() / 3600,
                "remaining_seconds": self.get_remaining_time().total_seconds()
            },
            "intervals": {
                "collection_range": self.collection_interval_range,
                "missile_launch_range": self.missile_launch_interval_range
            }
        }


# 全局实例管理
_unified_time_manager_instance = None

def get_unified_time_manager(config_manager=None) -> UnifiedTimeManager:
    """获取统一时间管理器的全局实例"""
    global _unified_time_manager_instance
    
    if _unified_time_manager_instance is None:
        _unified_time_manager_instance = UnifiedTimeManager(config_manager)
    
    return _unified_time_manager_instance

def reset_unified_time_manager():
    """重置统一时间管理器实例"""
    global _unified_time_manager_instance
    _unified_time_manager_instance = None
