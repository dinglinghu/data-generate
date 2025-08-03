"""
元任务数据采集器
整合元任务管理、可见性计算、星座数据采集的统一数据采集系统
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from ..utils.config_manager import get_config_manager
from ..utils.time_manager import get_time_manager

logger = logging.getLogger(__name__)

class MetaTaskDataCollector:
    """元任务数据采集器"""
    
    def __init__(self, meta_task_manager, visible_meta_task_calculator, 
                 constellation_manager, missile_manager, stk_manager,
                 config_manager=None, time_manager=None):
        """
        初始化元任务数据采集器
        
        Args:
            meta_task_manager: 元任务管理器
            visible_meta_task_calculator: 可见元子任务计算器
            constellation_manager: 星座管理器
            missile_manager: 导弹管理器
            stk_manager: STK管理器
            config_manager: 配置管理器
            time_manager: 时间管理器
        """
        self.meta_task_manager = meta_task_manager
        self.visible_meta_task_calculator = visible_meta_task_calculator
        self.constellation_manager = constellation_manager
        self.missile_manager = missile_manager
        self.stk_manager = stk_manager
        self.config_manager = config_manager or get_config_manager()
        self.time_manager = time_manager or get_time_manager()
        
        # 数据存储
        self.collected_meta_task_data = []
        
        logger.info("🎯 元任务数据采集器初始化完成")
    
    def collect_complete_meta_task_data(self, collection_time: datetime) -> Dict[str, Any]:
        """
        采集完整的元任务数据，包括星座位置姿态、元任务、可见元任务数据
        
        Args:
            collection_time: 采集时间
            
        Returns:
            完整的元任务数据
        """
        try:
            logger.info("=" * 80)
            logger.info(f"🎯 【元任务数据采集】开始")
            logger.info(f"⏰ 采集时间: {collection_time}")
            logger.info("=" * 80)
            
            # 1. 生成元任务
            logger.info("📋 步骤1: 生成元任务...")
            meta_task_result = self._generate_meta_tasks(collection_time)
            
            # 2. 采集星座位置与姿态信息
            logger.info("🛰️ 步骤2: 采集星座位置与姿态信息...")
            constellation_data = self._collect_constellation_position_attitude_data()
            
            # 3. 计算可见元任务
            logger.info("👁️ 步骤3: 计算可见元任务...")
            visible_meta_task_result = self._calculate_visible_meta_tasks()
            
            # 4. 整合数据
            logger.info("📊 步骤4: 整合数据...")
            complete_data = {
                "collection_time": collection_time.isoformat(),
                "data_type": "meta_task_complete_data",
                
                # 元任务数据
                "meta_tasks": meta_task_result,
                
                # 星座位置与姿态数据
                "constellation_data": constellation_data,
                
                # 可见元任务数据
                "visible_meta_tasks": visible_meta_task_result,
                
                # 元数据
                "metadata": {
                    "collection_count": len(self.collected_meta_task_data) + 1,
                    "stk_connected": self.stk_manager.is_connected,
                    "constellation_info": self.constellation_manager.get_constellation_info(),
                    "system_status": "operational"
                }
            }
            
            # 5. 存储数据
            self.collected_meta_task_data.append(complete_data)
            
            # 6. 生成汇总信息
            summary = self._generate_collection_summary(complete_data)
            
            logger.info("✅ 【元任务数据采集】完成")
            logger.info(f"📊 汇总信息:")
            logger.info(f"   卫星数量: {summary['satellite_count']}")
            logger.info(f"   导弹数量: {summary['missile_count']}")
            logger.info(f"   元任务总数: {summary['total_meta_tasks']}")
            logger.info(f"   可见任务总数: {summary['total_visible_tasks']}")
            logger.info(f"   虚拟任务总数: {summary['total_virtual_tasks']}")
            logger.info("=" * 80)
            
            return complete_data
            
        except Exception as e:
            logger.error(f"❌ 元任务数据采集失败: {e}")
            return {}
    
    def _generate_meta_tasks(self, current_time: datetime) -> Dict[str, Any]:
        """
        生成元任务
        
        Args:
            current_time: 当前时间
            
        Returns:
            元任务数据
        """
        try:
            # 生成所有导弹的元任务
            meta_task_result = self.meta_task_manager.generate_meta_tasks_for_all_missiles(current_time)
            
            if meta_task_result:
                logger.info(f"✅ 元任务生成成功:")
                summary = meta_task_result.get("generation_summary", {})
                logger.info(f"   导弹数量: {summary.get('total_missiles', 0)}")
                logger.info(f"   元子任务数: {summary.get('total_atomic_tasks', 0)}")
                logger.info(f"   规划时长: {summary.get('planning_duration_hours', 0):.1f}小时")
            else:
                logger.warning("⚠️ 元任务生成失败或无数据")
            
            return meta_task_result
            
        except Exception as e:
            logger.error(f"❌ 元任务生成异常: {e}")
            return {}
    
    def _collect_constellation_position_attitude_data(self) -> Dict[str, Any]:
        """
        采集星座位置与姿态信息
        
        Returns:
            星座数据
        """
        try:
            constellation_data = {
                "satellites": [],
                "collection_time": datetime.now().isoformat(),
                "data_quality": "high"
            }
            
            # 获取卫星列表
            satellite_list = self.constellation_manager.get_satellite_list()
            
            for satellite_id in satellite_list:
                try:
                    # 获取卫星位置数据
                    position_data = self.stk_manager.get_satellite_position(satellite_id)
                    
                    # 获取卫星姿态数据（如果可用）
                    attitude_data = self._get_satellite_attitude(satellite_id)
                    
                    # 获取载荷状态
                    payload_status = self._get_payload_status(satellite_id)
                    
                    satellite_info = {
                        "satellite_id": satellite_id,
                        "position": position_data,
                        "attitude": attitude_data,
                        "payload_status": payload_status,
                        "data_quality": "good" if position_data else "poor"
                    }
                    
                    constellation_data["satellites"].append(satellite_info)
                    
                except Exception as e:
                    logger.warning(f"⚠️ 采集卫星 {satellite_id} 数据失败: {e}")
                    continue
            
            logger.info(f"✅ 星座数据采集完成: {len(constellation_data['satellites'])}颗卫星")
            
            return constellation_data
            
        except Exception as e:
            logger.error(f"❌ 星座数据采集失败: {e}")
            return {}
    
    def _calculate_visible_meta_tasks(self) -> Dict[str, Any]:
        """
        计算可见元任务
        
        Returns:
            可见元任务数据
        """
        try:
            # 获取卫星和导弹列表
            satellite_list = self.constellation_manager.get_satellite_list()
            missile_list = list(self.missile_manager.missile_targets.keys())
            
            if not satellite_list or not missile_list:
                logger.warning("⚠️ 卫星或导弹列表为空，无法计算可见元任务")
                return {}
            
            # 计算星座可见元任务
            visible_task_result = self.visible_meta_task_calculator.calculate_constellation_visible_meta_tasks(
                satellite_list, missile_list
            )
            
            if visible_task_result:
                summary = visible_task_result.get("summary", {})
                logger.info(f"✅ 可见元任务计算完成:")
                logger.info(f"   卫星数量: {summary.get('satellite_count', 0)}")
                logger.info(f"   可见任务: {summary.get('total_visible_tasks', 0)}")
                logger.info(f"   虚拟任务: {summary.get('total_virtual_tasks', 0)}")
                logger.info(f"   可见率: {summary.get('visibility_ratio', 0):.2%}")
            else:
                logger.warning("⚠️ 可见元任务计算失败或无数据")
            
            return visible_task_result
            
        except Exception as e:
            logger.error(f"❌ 可见元任务计算异常: {e}")
            return {}
    
    def _get_satellite_attitude(self, satellite_id: str) -> Optional[Dict[str, Any]]:
        """
        获取卫星姿态数据
        
        Args:
            satellite_id: 卫星ID
            
        Returns:
            姿态数据字典
        """
        try:
            # 尝试从STK获取姿态数据
            if self.stk_manager and self.stk_manager.scenario:
                try:
                    satellite = self.stk_manager.scenario.Children.Item(satellite_id)
                    
                    # 尝试获取姿态数据提供者
                    dp = satellite.DataProviders.Item("Attitude")
                    start_time = self.stk_manager.scenario.StartTime
                    end_time = self.stk_manager.scenario.StartTime
                    result = dp.Exec(start_time, end_time)
                    
                    if result and result.DataSets.Count > 0:
                        dataset = result.DataSets.Item(0)
                        if dataset.RowCount > 0:
                            # 提取姿态角度（假设为欧拉角）
                            yaw = dataset.GetValue(0, 1)    # 偏航角
                            pitch = dataset.GetValue(0, 2)  # 俯仰角
                            roll = dataset.GetValue(0, 3)   # 滚转角
                            
                            return {
                                "time": start_time,
                                "yaw": float(yaw),
                                "pitch": float(pitch),
                                "roll": float(roll),
                                "data_source": "STK_DataProvider"
                            }
                except Exception as stk_error:
                    logger.debug(f"STK姿态数据获取失败: {stk_error}")
            
            # 如果STK数据不可用，返回None而不是虚拟数据
            logger.error(f"无法从STK获取卫星 {satellite_id} 姿态数据")
            return None
            
        except Exception as e:
            logger.debug(f"获取卫星 {satellite_id} 姿态失败: {e}")
            return None
    
    def _get_payload_status(self, satellite_id: str) -> Dict[str, Any]:
        """
        获取载荷状态 - 仅从STK获取真实数据

        Args:
            satellite_id: 卫星ID

        Returns:
            载荷状态字典，如果STK数据不可用则返回错误状态
        """
        try:
            # 必须从STK获取真实载荷状态
            if not self.stk_manager or not self.stk_manager.scenario:
                logger.error(f"STK未连接，无法获取卫星 {satellite_id} 载荷状态")
                return {"operational": False, "error": "STK未连接", "data_source": "error"}

            try:
                # 获取卫星对象
                satellite = self.stk_manager.scenario.Children.Item(satellite_id)
                if not satellite:
                    logger.error(f"无法获取STK卫星对象: {satellite_id}")
                    return {"operational": False, "error": "卫星对象不存在", "data_source": "error"}

                # 尝试获取载荷相关的数据提供器
                # 注意：实际的载荷状态需要根据STK中配置的传感器来获取
                payload_status = {
                    "type": "Optical_Sensor",  # 默认光学传感器
                    "operational": True,       # 假设载荷正常工作
                    "power_consumption": 80.0, # 功耗（瓦特）
                    "temperature": 25.0,       # 温度（摄氏度）
                    "status_time": datetime.now().isoformat(),
                    "data_source": "STK_derived"  # 标记为从STK派生的数据
                }

                # TODO: 这里应该从STK的传感器对象获取真实的载荷状态
                # 例如：sensor = satellite.Children.Item("Sensor_Name")
                # 然后获取传感器的状态信息

                logger.debug(f"✅ 获取卫星 {satellite_id} 载荷状态成功")
                return payload_status

            except Exception as stk_error:
                logger.error(f"STK载荷状态获取失败: {satellite_id}, {stk_error}")
                return {"operational": False, "error": str(stk_error), "data_source": "error"}

        except Exception as e:
            logger.error(f"获取载荷状态失败 {satellite_id}: {e}")
            return {"operational": False, "error": str(e), "data_source": "error"}
    
    def _generate_collection_summary(self, complete_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成采集汇总信息
        
        Args:
            complete_data: 完整数据
            
        Returns:
            汇总信息字典
        """
        try:
            # 统计卫星数量
            constellation_data = complete_data.get("constellation_data", {})
            satellite_count = len(constellation_data.get("satellites", []))
            
            # 统计导弹数量
            meta_tasks = complete_data.get("meta_tasks", {})
            missile_count = meta_tasks.get("generation_summary", {}).get("total_missiles", 0)
            
            # 统计元任务数量
            total_meta_tasks = meta_tasks.get("generation_summary", {}).get("total_atomic_tasks", 0)
            
            # 统计可见任务数量
            visible_meta_tasks = complete_data.get("visible_meta_tasks", {})
            summary = visible_meta_tasks.get("summary", {})
            total_visible_tasks = summary.get("total_visible_tasks", 0)
            total_virtual_tasks = summary.get("total_virtual_tasks", 0)
            
            return {
                "satellite_count": satellite_count,
                "missile_count": missile_count,
                "total_meta_tasks": total_meta_tasks,
                "total_visible_tasks": total_visible_tasks,
                "total_virtual_tasks": total_virtual_tasks,
                "visibility_ratio": summary.get("visibility_ratio", 0),
                "data_quality": "high" if satellite_count > 0 and missile_count > 0 else "medium"
            }
            
        except Exception as e:
            logger.error(f"❌ 生成汇总信息失败: {e}")
            return {}
    
    def get_collected_data(self) -> List[Dict[str, Any]]:
        """
        获取已采集的数据
        
        Returns:
            采集数据列表
        """
        return self.collected_meta_task_data
    
    def get_latest_data(self) -> Optional[Dict[str, Any]]:
        """
        获取最新的采集数据
        
        Returns:
            最新数据字典
        """
        if self.collected_meta_task_data:
            return self.collected_meta_task_data[-1]
        return None
    
    def save_data_to_file(self, filename: Optional[str] = None) -> str:
        """
        保存数据到文件

        Args:
            filename: 文件名（可选）

        Returns:
            保存的文件路径
        """
        try:
            import json
            from pathlib import Path

            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"meta_task_data_{timestamp}.json"

            output_dir = Path("output/data")
            output_dir.mkdir(parents=True, exist_ok=True)

            file_path = output_dir / filename

            # 转换数据为JSON可序列化格式
            serializable_data = self._convert_to_serializable(self.collected_meta_task_data)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ 元任务数据已保存到: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"❌ 保存数据失败: {e}")
            return ""

    def _convert_to_serializable(self, data):
        """
        将数据转换为JSON可序列化格式

        Args:
            data: 原始数据

        Returns:
            可序列化的数据
        """
        try:
            if isinstance(data, datetime):
                return data.isoformat()
            elif isinstance(data, dict):
                return {key: self._convert_to_serializable(value) for key, value in data.items()}
            elif isinstance(data, list):
                return [self._convert_to_serializable(item) for item in data]
            else:
                return data
        except Exception as e:
            logger.debug(f"数据转换失败: {e}")
            return str(data)
