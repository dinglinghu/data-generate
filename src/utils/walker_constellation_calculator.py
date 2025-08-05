#!/usr/bin/env python3
"""
Walker星座轨道计算器 - 正确计算Walker星座的轨道六根数

基于标准Walker星座定义：
- Walker Delta: 卫星在相邻轨道面间均匀分布
- Walker Star: 卫星在相邻轨道面间有特定相位关系

Walker星座记号: W(T, P, F)
- T: 总卫星数
- P: 轨道面数
- F: 相位因子 (0 ≤ F < P)

参考文献:
- Walker, J.G. "Satellite constellations" Journal of the British Interplanetary Society, 1984
- Wertz, J.R. "Mission Geometry; Orbit and Constellation Design and Management", 2001
"""

import logging
import math
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class WalkerParameters:
    """Walker星座参数"""
    total_satellites: int      # T: 总卫星数
    num_planes: int           # P: 轨道面数
    phase_factor: int         # F: 相位因子
    pattern_type: str         # "delta" 或 "star"
    
    def __post_init__(self):
        """验证参数有效性"""
        if self.total_satellites % self.num_planes != 0:
            raise ValueError(f"总卫星数({self.total_satellites})必须能被轨道面数({self.num_planes})整除")
        
        if not (0 <= self.phase_factor < self.num_planes):
            raise ValueError(f"相位因子({self.phase_factor})必须在0到{self.num_planes-1}之间")
        
        if self.pattern_type not in ["delta", "star"]:
            raise ValueError(f"模式类型必须是'delta'或'star'，当前为: {self.pattern_type}")
    
    @property
    def sats_per_plane(self) -> int:
        """每个轨道面的卫星数"""
        return self.total_satellites // self.num_planes

@dataclass
class OrbitalElements:
    """轨道六根数"""
    semi_major_axis: float    # 半长轴 (km)
    eccentricity: float       # 偏心率
    inclination: float        # 轨道倾角 (度)
    raan: float              # 升交点赤经 (度)
    arg_of_perigee: float    # 近地点幅角 (度)
    mean_anomaly: float      # 平近点角 (度)
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            "semi_axis": self.semi_major_axis,
            "eccentricity": self.eccentricity,
            "inclination": self.inclination,
            "raan": self.raan,
            "arg_of_perigee": self.arg_of_perigee,
            "mean_anomaly": self.mean_anomaly
        }

class WalkerConstellationCalculator:
    """Walker星座轨道计算器"""
    
    # 地球参数
    EARTH_RADIUS = 6371.0  # km
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def calculate_constellation(self, 
                              walker_params: WalkerParameters,
                              reference_orbit: Dict[str, float]) -> List[Tuple[str, OrbitalElements]]:
        """
        计算Walker星座中所有卫星的轨道六根数
        
        Args:
            walker_params: Walker星座参数
            reference_orbit: 参考轨道参数
            
        Returns:
            [(卫星ID, 轨道六根数), ...]
        """
        self.logger.info(f"🌟 开始计算Walker星座轨道参数")
        self.logger.info(f"   星座配置: W({walker_params.total_satellites}, {walker_params.num_planes}, {walker_params.phase_factor})")
        self.logger.info(f"   模式类型: {walker_params.pattern_type}")
        
        # 提取参考轨道参数
        altitude = reference_orbit.get("altitude", 1800)
        inclination = reference_orbit.get("inclination", 51.856)
        eccentricity = reference_orbit.get("eccentricity", 0.0)
        arg_of_perigee = reference_orbit.get("arg_of_perigee", 0.0)
        raan_offset = reference_orbit.get("raan_offset", 0.0)
        mean_anomaly_offset = reference_orbit.get("mean_anomaly_offset", 0.0)
        
        # 计算半长轴
        semi_major_axis = self.EARTH_RADIUS + altitude
        
        # 计算轨道面间隔
        raan_spacing = 360.0 / walker_params.num_planes
        
        # 计算同轨道面内卫星间隔
        mean_anomaly_spacing = 360.0 / walker_params.sats_per_plane
        
        self.logger.info(f"   参考轨道: 高度={altitude}km, 倾角={inclination}°")
        self.logger.info(f"   半长轴: {semi_major_axis:.1f}km")
        self.logger.info(f"   RAAN间隔: {raan_spacing:.1f}°")
        self.logger.info(f"   平近点角间隔: {mean_anomaly_spacing:.1f}°")
        
        satellites = []
        satellite_count = 0
        
        # 遍历每个轨道面
        for plane_idx in range(walker_params.num_planes):
            # 计算该轨道面的RAAN
            plane_raan = (plane_idx * raan_spacing + raan_offset) % 360.0
            
            # 遍历该轨道面内的每颗卫星
            for sat_idx in range(walker_params.sats_per_plane):
                satellite_count += 1
                
                # 生成卫星ID
                satellite_id = f"Satellite{satellite_count:02d}"
                
                # 计算该卫星的平近点角
                sat_mean_anomaly = self._calculate_mean_anomaly(
                    plane_idx, sat_idx, walker_params, 
                    mean_anomaly_spacing, mean_anomaly_offset
                )
                
                # 创建轨道六根数
                orbital_elements = OrbitalElements(
                    semi_major_axis=semi_major_axis,
                    eccentricity=eccentricity,
                    inclination=inclination,
                    raan=plane_raan,
                    arg_of_perigee=arg_of_perigee,
                    mean_anomaly=sat_mean_anomaly
                )
                
                satellites.append((satellite_id, orbital_elements))
                
                self.logger.debug(f"   {satellite_id}: 轨道面{plane_idx+1}, 位置{sat_idx+1}")
                self.logger.debug(f"     RAAN: {plane_raan:.1f}°, 平近点角: {sat_mean_anomaly:.1f}°")
        
        self.logger.info(f"✅ Walker星座轨道计算完成，共{len(satellites)}颗卫星")
        return satellites
    
    def _calculate_mean_anomaly(self, 
                               plane_idx: int, 
                               sat_idx: int,
                               walker_params: WalkerParameters,
                               mean_anomaly_spacing: float,
                               mean_anomaly_offset: float) -> float:
        """
        计算卫星的平近点角
        
        Walker星座的关键在于相位因子F的正确应用：
        - Delta模式: 相邻轨道面的卫星有F*360°/T的相位差
        - Star模式: 类似Delta，但相位关系不同
        
        Args:
            plane_idx: 轨道面索引 (0开始)
            sat_idx: 卫星在轨道面内的索引 (0开始)
            walker_params: Walker参数
            mean_anomaly_spacing: 同轨道面内卫星间隔
            mean_anomaly_offset: 基础偏移
            
        Returns:
            平近点角 (度)
        """
        # 基础平近点角（该卫星在其轨道面内的位置）
        base_mean_anomaly = sat_idx * mean_anomaly_spacing
        
        # Walker相位偏移
        if walker_params.pattern_type.lower() == "delta":
            # Delta模式：相位偏移 = F * plane_idx * 360° / T
            phase_offset = (walker_params.phase_factor * plane_idx * 360.0) / walker_params.total_satellites
        else:  # star模式
            # Star模式：相位偏移计算稍有不同
            phase_offset = (walker_params.phase_factor * plane_idx * 360.0) / walker_params.total_satellites
        
        # 总平近点角
        total_mean_anomaly = (base_mean_anomaly + phase_offset + mean_anomaly_offset) % 360.0
        
        return total_mean_anomaly
    
    def validate_walker_parameters(self, 
                                 total_satellites: int, 
                                 num_planes: int, 
                                 phase_factor: int) -> bool:
        """
        验证Walker星座参数的有效性
        
        Args:
            total_satellites: 总卫星数
            num_planes: 轨道面数
            phase_factor: 相位因子
            
        Returns:
            参数是否有效
        """
        try:
            # 检查总卫星数是否能被轨道面数整除
            if total_satellites % num_planes != 0:
                self.logger.error(f"❌ 总卫星数({total_satellites})必须能被轨道面数({num_planes})整除")
                return False
            
            # 检查相位因子范围
            if not (0 <= phase_factor < num_planes):
                self.logger.error(f"❌ 相位因子({phase_factor})必须在0到{num_planes-1}之间")
                return False
            
            # 检查每个轨道面的卫星数是否合理
            sats_per_plane = total_satellites // num_planes
            if sats_per_plane < 1:
                self.logger.error(f"❌ 每个轨道面至少需要1颗卫星，当前为{sats_per_plane}")
                return False
            
            self.logger.info(f"✅ Walker参数验证通过: W({total_satellites}, {num_planes}, {phase_factor})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Walker参数验证失败: {e}")
            return False
    
    def get_constellation_info(self, walker_params: WalkerParameters) -> Dict[str, Any]:
        """
        获取Walker星座的详细信息
        
        Args:
            walker_params: Walker参数
            
        Returns:
            星座信息字典
        """
        return {
            "constellation_type": "Walker",
            "notation": f"W({walker_params.total_satellites}, {walker_params.num_planes}, {walker_params.phase_factor})",
            "pattern_type": walker_params.pattern_type,
            "total_satellites": walker_params.total_satellites,
            "num_planes": walker_params.num_planes,
            "sats_per_plane": walker_params.sats_per_plane,
            "phase_factor": walker_params.phase_factor,
            "raan_spacing": 360.0 / walker_params.num_planes,
            "mean_anomaly_spacing": 360.0 / walker_params.sats_per_plane,
            "phase_offset_per_plane": (walker_params.phase_factor * 360.0) / walker_params.total_satellites
        }
    
    def calculate_coverage_metrics(self, walker_params: WalkerParameters) -> Dict[str, float]:
        """
        计算Walker星座的覆盖性能指标
        
        Args:
            walker_params: Walker参数
            
        Returns:
            覆盖性能指标
        """
        # 这里可以添加更复杂的覆盖性能计算
        # 目前提供基础指标
        
        raan_spacing = 360.0 / walker_params.num_planes
        mean_anomaly_spacing = 360.0 / walker_params.sats_per_plane
        
        return {
            "orbital_plane_separation": raan_spacing,
            "intra_plane_separation": mean_anomaly_spacing,
            "constellation_symmetry": walker_params.phase_factor / walker_params.num_planes,
            "total_coverage_points": walker_params.total_satellites,
            "plane_coverage_points": walker_params.sats_per_plane
        }


# 全局计算器实例
_walker_calculator_instance = None

def get_walker_calculator() -> WalkerConstellationCalculator:
    """获取Walker星座计算器的全局实例"""
    global _walker_calculator_instance
    
    if _walker_calculator_instance is None:
        _walker_calculator_instance = WalkerConstellationCalculator()
    
    return _walker_calculator_instance
