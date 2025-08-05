"""
星座管理器
负责Walker星座的创建与参数配置，包括卫星轨道参数设置和载荷配置
"""

import logging
import math
from typing import Dict, List, Any, Optional
from ..utils.config_manager import get_config_manager
from ..utils.walker_constellation_calculator import get_walker_calculator, WalkerParameters

logger = logging.getLogger(__name__)

class ConstellationManager:
    """Walker星座管理器"""
    
    def __init__(self, stk_manager, config_manager=None):
        """
        初始化星座管理器
        
        Args:
            stk_manager: STK管理器实例
            config_manager: 配置管理器实例
        """
        self.stk_manager = stk_manager
        self.config_manager = config_manager or get_config_manager()
        self.constellation_config = self.config_manager.get_constellation_config()
        self.payload_config = self.config_manager.get_payload_config()
        self.satellite_list = []

        # 初始化Walker星座计算器
        self.walker_calculator = get_walker_calculator()

        logger.info("🌟 星座管理器初始化完成")
        
    def create_walker_constellation(self) -> bool:
        """
        创建Walker星座
        
        Returns:
            创建是否成功
        """
        try:
            logger.info("🌟 开始创建Walker星座...")
            
            # 检查STK连接
            if not self.stk_manager.is_connected:
                logger.error("❌ STK未连接，无法创建星座")
                return False
            
            # 检查是否跳过创建（现有项目检测）
            if self.stk_manager.should_skip_creation():
                logger.info("🔍 检测到现有项目，跳过星座创建")
                return True
            
            # 获取星座参数
            constellation_type = self.constellation_config.get("type", "Walker")
            planes = self.constellation_config.get("planes", 3)
            sats_per_plane = self.constellation_config.get("satellites_per_plane", 3)
            total_satellites = self.constellation_config.get("total_satellites", 9)
            
            logger.info(f"📊 星座配置: {constellation_type}, {planes}个轨道面, 每面{sats_per_plane}颗卫星")
            
            # 创建Walker星座
            success = self._create_walker_satellites(planes, sats_per_plane)
            
            if success:
                logger.info(f"✅ Walker星座创建成功，共{total_satellites}颗卫星")
                return True
            else:
                logger.error("❌ Walker星座创建失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 创建Walker星座异常: {e}")
            return False
    
    def _create_walker_satellites(self, planes: int, sats_per_plane: int) -> bool:
        """
        创建Walker星座中的所有卫星

        Args:
            planes: 轨道面数量
            sats_per_plane: 每个轨道面的卫星数量

        Returns:
            创建是否成功
        """
        try:
            # 获取Walker星座参数
            total_satellites = planes * sats_per_plane
            walker_params_config = self.constellation_config.get("walker_parameters", {})
            phase_factor = walker_params_config.get("phase_factor", 1)
            pattern_type = walker_params_config.get("pattern_type", "delta")

            # 创建Walker参数对象
            walker_params = WalkerParameters(
                total_satellites=total_satellites,
                num_planes=planes,
                phase_factor=phase_factor,
                pattern_type=pattern_type
            )

            # 验证Walker参数
            if not self.walker_calculator.validate_walker_parameters(
                total_satellites, planes, phase_factor):
                logger.error("❌ Walker星座参数验证失败")
                return False

            # 获取参考轨道参数
            reference_params = self.constellation_config.get("reference_satellite", {})

            # 使用Walker计算器计算所有卫星的轨道参数
            satellites_orbital_data = self.walker_calculator.calculate_constellation(
                walker_params, reference_params)

            logger.info(f"📊 Walker星座计算完成:")
            constellation_info = self.walker_calculator.get_constellation_info(walker_params)
            logger.info(f"   星座记号: {constellation_info['notation']}")
            logger.info(f"   模式类型: {constellation_info['pattern_type']}")
            logger.info(f"   RAAN间隔: {constellation_info['raan_spacing']:.1f}°")
            logger.info(f"   平近点角间隔: {constellation_info['mean_anomaly_spacing']:.1f}°")
            logger.info(f"   相位偏移: {constellation_info['phase_offset_per_plane']:.1f}°/面")

            satellite_count = 0
            
            # 使用计算好的轨道数据创建卫星
            for satellite_id, orbital_elements in satellites_orbital_data:
                satellite_count += 1

                # 转换为STK需要的格式
                orbital_params = orbital_elements.to_dict()

                # 创建卫星
                success = self.stk_manager.create_satellite(satellite_id, orbital_params)
                if not success:
                    logger.error(f"❌ 卫星创建失败: {satellite_id}")
                    return False

                # 为卫星创建载荷
                payload_success = self.stk_manager.create_sensor(satellite_id, self.payload_config)
                if not payload_success:
                    logger.warning(f"⚠️ 载荷创建失败: {satellite_id}")

                # 计算轨道面和位置信息用于日志
                plane_idx = (satellite_count - 1) // sats_per_plane
                sat_idx = (satellite_count - 1) % sats_per_plane

                logger.info(f"✅ 卫星创建成功: {satellite_id} (轨道面{plane_idx+1}, 位置{sat_idx+1})")
                logger.debug(f"   轨道参数: RAAN={orbital_elements.raan:.1f}°, 平近点角={orbital_elements.mean_anomaly:.1f}°")

                # 添加到卫星列表
                self.satellite_list.append(satellite_id)
            
            logger.info(f"🌟 Walker星座创建完成，共创建{satellite_count}颗卫星")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建Walker卫星失败: {e}")
            return False
    
    # 旧的轨道参数计算方法已被Walker星座计算器替代
    # 保留此方法以防向后兼容需要，但建议使用walker_constellation_calculator
    
    def get_satellite_list(self) -> List[str]:
        """
        获取星座中的卫星列表

        Returns:
            卫星ID列表
        """
        # 如果已经有卫星列表，直接返回
        if self.satellite_list:
            return self.satellite_list.copy()

        # 否则根据配置生成列表
        try:
            total_satellites = self.constellation_config.get("total_satellites", 9)
            satellite_list = []

            for i in range(1, total_satellites + 1):
                satellite_id = f"Satellite{i:02d}"
                satellite_list.append(satellite_id)

            return satellite_list
            
        except Exception as e:
            logger.error(f"❌ 获取卫星列表失败: {e}")
            return []
    
    def get_constellation_info(self) -> Dict[str, Any]:
        """
        获取星座信息
        
        Returns:
            星座信息字典
        """
        return {
            "type": self.constellation_config.get("type", "Walker"),
            "planes": self.constellation_config.get("planes", 3),
            "satellites_per_plane": self.constellation_config.get("satellites_per_plane", 3),
            "total_satellites": self.constellation_config.get("total_satellites", 9),
            "satellite_list": self.get_satellite_list(),
            "reference_satellite": self.constellation_config.get("reference_satellite", {}),
            "payload_config": self.payload_config
        }
    
    def validate_constellation_parameters(self) -> bool:
        """
        验证星座参数的有效性
        
        Returns:
            参数是否有效
        """
        try:
            # 检查基本参数
            planes = self.constellation_config.get("planes", 0)
            sats_per_plane = self.constellation_config.get("satellites_per_plane", 0)
            total_satellites = self.constellation_config.get("total_satellites", 0)
            
            if planes <= 0 or sats_per_plane <= 0:
                logger.error("❌ 星座参数无效: 轨道面数或每面卫星数必须大于0")
                return False
            
            if total_satellites != planes * sats_per_plane:
                logger.warning(f"⚠️ 总卫星数({total_satellites})与计算值({planes * sats_per_plane})不匹配")
            
            # 检查轨道参数
            ref_sat = self.constellation_config.get("reference_satellite", {})
            altitude = ref_sat.get("altitude", 0)
            inclination = ref_sat.get("inclination", 0)
            
            if altitude < 200 or altitude > 50000:
                logger.error(f"❌ 轨道高度无效: {altitude} km (应在200-50000 km范围内)")
                return False
            
            if inclination < 0 or inclination > 180:
                logger.error(f"❌ 轨道倾角无效: {inclination}° (应在0-180°范围内)")
                return False
            
            logger.info("✅ 星座参数验证通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 星座参数验证失败: {e}")
            return False
