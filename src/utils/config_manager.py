"""
配置管理器
统一管理项目的所有配置参数，包括星座、载荷、导弹、时间等配置
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ConfigManager:
    """统一配置管理器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为config/config.yaml
        """
        self.config_path = config_path or "config/config.yaml"
        self.config = {}
        self._load_config()
        
    def _load_config(self):
        """加载配置文件"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                logger.info(f"✅ 配置文件加载成功: {self.config_path}")
            else:
                logger.warning(f"⚠️ 配置文件不存在: {self.config_path}，使用默认配置")
                self.config = self._get_default_config()
                self._save_default_config()
        except Exception as e:
            logger.error(f"❌ 配置文件加载失败: {e}")
            self.config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "constellation": {
                "type": "Walker",
                "planes": 3,
                "satellites_per_plane": 3,
                "total_satellites": 9,
                "reference_satellite": {
                    "altitude": 1800,
                    "inclination": 51.856,
                    "eccentricity": 0.0,
                    "arg_of_perigee": 12,
                    "raan_offset": 24,
                    "mean_anomaly_offset": 180
                }
            },
            "payload": {
                "type": "Optical_Sensor",
                "mounting": "Nadir",
                "sensor_pattern": "Conic",
                "inner_cone_half_angle": 66.1,
                "outer_cone_half_angle": 85.0,
                "clockwise_angle_min": 0.0,
                "clockwise_angle_max": 360.0,
                "pointing": {
                    "azimuth": 0.0,
                    "elevation": 90.0
                },
                "constraints_range": {
                    "min_range": 0,
                    "max_range": 5000,
                    "active": True
                }
            },
            "missile": {
                "max_concurrent_missiles": 5,
                "launch_interval_range": [300, 1800],
                "global_launch_positions": {
                    "lat_range": [-60, 60],
                    "lon_range": [-180, 180],
                    "alt_range": [0, 100]
                },
                "global_target_positions": {
                    "lat_range": [-60, 60], 
                    "lon_range": [-180, 180],
                    "alt_range": [0, 100]
                },
                "trajectory_params": {
                    "max_altitude_range": [300, 1500],
                    "flight_time_range": [600, 1800]
                }
            },
            "simulation": {
                # 注意：这些是备用默认值，应该在配置文件中明确设置
                "start_time": "2025/07/26 04:00:00",
                "end_time": "2025/07/26 08:00:00",
                "epoch_time": "2025/07/26 04:00:00",
                "time_step": 60,
                "time_format": "%Y/%m/%d %H:%M:%S",
                "data_collection": {
                    "interval_range": [60, 300],
                    "save_frequency": 10,
                    "output_format": "json"
                }
            },
            "stk": {
                "detect_existing_project": True,
                "existing_project_wait_time": 5,
                "max_connections": 5,
                "connection_timeout": 30
            }
        }
    
    def _save_default_config(self):
        """保存默认配置到文件"""
        try:
            config_file = Path(self.config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, indent=2)
            logger.info(f"✅ 默认配置已保存: {self.config_path}")
        except Exception as e:
            logger.error(f"❌ 保存默认配置失败: {e}")
    
    def get_constellation_config(self) -> Dict[str, Any]:
        """获取星座配置"""
        return self.config.get("constellation", {})
    
    def get_payload_config(self) -> Dict[str, Any]:
        """获取载荷配置"""
        return self.config.get("payload", {})
    
    def get_missile_config(self) -> Dict[str, Any]:
        """获取导弹配置"""
        return self.config.get("missile", {})
    
    def get_simulation_config(self) -> Dict[str, Any]:
        """获取仿真配置"""
        return self.config.get("simulation", {})
    
    def get_stk_config(self) -> Dict[str, Any]:
        """获取STK配置"""
        return self.config.get("stk", {})
    
    def get_data_collection_config(self) -> Dict[str, Any]:
        """获取数据采集配置"""
        sim_config = self.get_simulation_config()
        return sim_config.get("data_collection", {})
    
    def get_task_planning_config(self) -> Dict[str, Any]:
        """获取任务规划配置"""
        return self.config.get("task_planning", {
            "midcourse_altitude_threshold": 100,
            "atomic_task_duration": 300
        })

    def get_physics_config(self) -> Dict[str, Any]:
        """获取物理常数配置"""
        return self.config.get("physics", {
            "earth_radius": 6371
        })

    def get_visibility_config(self) -> Dict[str, Any]:
        """获取可见性配置"""
        return self.config.get("visibility", {
            "random_windows": {
                "count_range": [1, 3],
                "start_offset_range": [300, 900],
                "duration_range": [180, 600],
                "interval_multiplier": 600
            },
            "access_constraints": {
                "min_altitude": 20.0,
                "sun_elevation_min": -10.0
            },
            "cache": {
                "timeout": 300
            }
        })

    def get_missile_management_config(self) -> Dict[str, Any]:
        """获取导弹管理配置"""
        return self.config.get("missile_management", {
            "position_generation": {
                "min_distance_deg": 10,
                "max_attempts": 10,
                "id_range": [1000, 9999]
            },
            "flight_time": {
                "default_minutes": 30
            }
        })

    def get_data_simulation_config(self) -> Dict[str, Any]:
        """获取数据模拟配置"""
        return self.config.get("data_simulation", {
            "payload_status": {
                "power_consumption": 80.0,
                "temperature": 25.0,
                "operational_default": True
            }
        })

    def get_system_config(self) -> Dict[str, Any]:
        """获取系统配置"""
        return self.config.get("system", {
            "testing": {
                "initial_missile_count": 3,
                "missile_add_probability": 0.3
            },
            "missile_management_range": {
                "target_min": 5,
                "target_max": 20
            },
            "delays": {
                "collection_loop": 0.2
            }
        })

    def get_missile_pool_config(self) -> Dict[str, Any]:
        """获取导弹池配置"""
        return self.config.get("missile_pool", {
            "enable": True,
            "pool_size": 30,
            "active_limit": 5,
            "default_flight_duration": 1800,
            "id_random_range": [1000, 9999]
        })

    def get_output_config(self) -> Dict[str, Any]:
        """获取输出配置"""
        return self.config.get("output", {
            "base_directory": "output",
            "data_directory": "output/data",
            "log_directory": "logs",
            "visualization_directory": "output/visualization",
            "charts_directory": "output/charts",
            "rolling_collections": {
                "base_directory": "output/rolling_collections",
                "default_fallback": "output/data"
            },
            "file_naming": {
                "session_prefix": "session_",
                "collection_prefix": "collection_",
                "log_prefix": "rolling_collection_",
                "data_filename": "meta_task_data.json",
                "gantt_filename_template": "collection_{:02d}_aerospace_meta_task_gantt.png"
            }
        })
    
    def update_config(self, section: str, new_config: Dict[str, Any]):
        """更新配置"""
        if section in self.config:
            self.config[section].update(new_config)
            logger.info(f"✅ 配置更新成功: {section}")
        else:
            logger.warning(f"⚠️ 配置节不存在: {section}")
    
    def save_config(self):
        """保存当前配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, indent=2)
            logger.info(f"✅ 配置已保存: {self.config_path}")
        except Exception as e:
            logger.error(f"❌ 保存配置失败: {e}")

# 全局配置管理器实例
_config_manager = None

def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager
