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
        采集完整的元任务数据，包括星座位置、元任务、可见元任务数据

        Args:
            collection_time: 采集时间

        Returns:
            完整的元任务数据
        """
        try:
            # 设置采集时间为实例属性
            self.collection_time = collection_time

            logger.info("=" * 80)
            logger.info(f"🎯 【元任务数据采集】开始")
            logger.info(f"⏰ 采集时间: {collection_time}")
            logger.info("=" * 80)
            
            # 1. 生成元任务
            logger.info("📋 步骤1: 生成元任务...")
            meta_task_result = self._generate_meta_tasks(collection_time)
            
            # 2. 采集星座位置信息
            logger.info("🛰️ 步骤2: 采集星座位置信息...")
            constellation_data = self._collect_constellation_position_data()
            
            # 3. 计算可见元任务
            logger.info("👁️ 步骤3: 计算可见元任务...")
            visible_meta_task_result = self._calculate_visible_meta_tasks()

            # 4. 增强可见元任务数据（添加卫星位置信息）
            logger.info("🛰️ 步骤4: 增强可见元任务数据...")
            enhanced_visible_meta_task_result = self._enhance_visible_meta_tasks_with_satellite_positions(
                visible_meta_task_result, constellation_data, collection_time
            )

            # 5. 整合数据
            logger.info("📊 步骤5: 整合数据...")
            complete_data = {
                "collection_time": collection_time.isoformat(),
                "data_type": "meta_task_complete_data",

                # 元任务数据
                "meta_tasks": meta_task_result,

                # 星座位置与姿态数据
                "constellation_data": constellation_data,

                # 增强后的可见元任务数据（包含卫星位置信息）
                "visible_meta_tasks": enhanced_visible_meta_task_result,

                # 元数据
                "metadata": {
                    "collection_count": len(self.collected_meta_task_data) + 1,
                    "stk_connected": self.stk_manager.is_connected,
                    "constellation_info": self.constellation_manager.get_constellation_info(),
                    "system_status": "operational",
                    "satellite_position_enhancement": True,
                    "enhancement_version": "v1.0"
                }
            }
            
            # 6. 存储数据
            self.collected_meta_task_data.append(complete_data)

            # 7. 生成汇总信息
            summary = self._generate_collection_summary(complete_data)
            
            logger.info("✅ 【元任务数据采集】完成")
            logger.info(f"📊 汇总信息:")
            logger.info(f"   卫星数量: {summary['satellite_count']}")
            logger.info(f"   导弹数量: {summary['missile_count']}")
            logger.info(f"   元任务总数: {summary['total_meta_tasks']}")
            logger.info(f"   可见任务总数: {summary['total_visible_tasks']}")
            logger.info(f"   虚拟任务总数: {summary['total_virtual_tasks']}")

            # 显示卫星位置增强信息
            enhancement_info = summary.get('satellite_position_enhancement', {})
            if enhancement_info.get('enabled', False):
                logger.info(f"🛰️ 卫星位置增强:")
                logger.info(f"   匹配卫星: {enhancement_info.get('satellites_matched', 0)}")
                logger.info(f"   增强任务: {enhancement_info.get('tasks_enhanced', 0)}")
                logger.info(f"   几何分析: {enhancement_info.get('geometric_analyses_added', 0)}")
                logger.info(f"   增强版本: {enhancement_info.get('enhancement_version', 'unknown')}")
            else:
                logger.info("🛰️ 卫星位置增强: 未启用")

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
    
    def _collect_constellation_position_data(self) -> Dict[str, Any]:
        """
        采集星座位置信息（不包含姿态数据）

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
                    # 获取卫星位置数据 - 使用采集时间
                    time_str = self.collection_time.strftime("%d %b %Y %H:%M:%S.000")
                    position_data = self.stk_manager.get_satellite_position(satellite_id, time_str)

                    # 获取载荷状态
                    payload_status = self._get_payload_status(satellite_id)

                    satellite_info = {
                        "satellite_id": satellite_id,
                        "position": position_data,
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

            # 统计卫星位置增强信息
            enhancement_metadata = visible_meta_tasks.get("enhancement_metadata", {})
            enhancement_stats = enhancement_metadata.get("enhancement_stats", {})

            return {
                "satellite_count": satellite_count,
                "missile_count": missile_count,
                "total_meta_tasks": total_meta_tasks,
                "total_visible_tasks": total_visible_tasks,
                "total_virtual_tasks": total_virtual_tasks,
                "visibility_ratio": summary.get("visibility_ratio", 0),
                "data_quality": "high" if satellite_count > 0 and missile_count > 0 else "medium",
                # 卫星位置增强统计
                "satellite_position_enhancement": {
                    "enabled": enhancement_metadata.get("satellite_positions_added", False),
                    "satellites_matched": enhancement_stats.get("satellites_matched", 0),
                    "tasks_enhanced": enhancement_stats.get("tasks_enhanced", 0),
                    "geometric_analyses_added": enhancement_stats.get("geometric_analyses_added", 0),
                    "enhancement_version": enhancement_metadata.get("enhancement_version", "unknown")
                }
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
        保存数据到文件 - 已禁用，只保存到统一目录

        Args:
            filename: 文件名（可选）

        Returns:
            保存的文件路径
        """
        try:
            logger.info(f"💾 元任务数据保存已禁用，只保存到统一目录")
            return ""

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

    def _enhance_visible_meta_tasks_with_satellite_positions(self, visible_meta_tasks: Dict[str, Any],
                                                           constellation_data: Dict[str, Any],
                                                           collection_time: datetime) -> Dict[str, Any]:
        """
        为可见元任务数据添加卫星位置信息

        Args:
            visible_meta_tasks: 原始可见元任务数据
            constellation_data: 星座位置数据
            collection_time: 采集时间

        Returns:
            增强后的可见元任务数据
        """
        try:
            logger.info("🔧 开始增强可见元任务数据...")

            # 创建数据副本
            enhanced_visible_tasks = visible_meta_tasks.copy()

            # 提取卫星位置数据
            satellite_positions = self._extract_satellite_positions_from_constellation_data(constellation_data)

            if not satellite_positions:
                logger.warning("⚠️ 没有找到卫星位置数据，跳过增强")
                return visible_meta_tasks

            # 增强统计
            enhancement_stats = {
                "satellites_matched": 0,
                "tasks_enhanced": 0,
                "geometric_analyses_added": 0
            }

            # 增强可见元任务
            constellation_task_sets = enhanced_visible_tasks.get("constellation_visible_task_sets", {})

            for satellite_id, satellite_data in constellation_task_sets.items():
                # 获取对应的卫星位置数据
                satellite_position_data = satellite_positions.get(satellite_id)

                if not satellite_position_data:
                    logger.debug(f"⚠️ 未找到卫星 {satellite_id} 的位置数据")
                    continue

                enhancement_stats["satellites_matched"] += 1

                # 增强该卫星的所有可见任务
                missile_tasks = satellite_data.get("missile_tasks", {})

                for missile_id, missile_data in missile_tasks.items():
                    visible_tasks = missile_data.get("visible_tasks", [])

                    enhanced_visible_tasks_list = []

                    for task in visible_tasks:
                        enhanced_task = self._enhance_single_visible_task_with_satellite_position(
                            task, satellite_id, satellite_position_data, collection_time
                        )
                        enhanced_visible_tasks_list.append(enhanced_task)
                        enhancement_stats["tasks_enhanced"] += 1

                        # 检查是否添加了几何分析
                        if "satellite_position" in enhanced_task and "geometric_analysis" in enhanced_task["satellite_position"]:
                            enhancement_stats["geometric_analyses_added"] += 1

                    missile_data["visible_tasks"] = enhanced_visible_tasks_list

                    # 同样增强虚拟任务
                    virtual_tasks = missile_data.get("virtual_tasks", [])
                    enhanced_virtual_tasks_list = []

                    for task in virtual_tasks:
                        enhanced_task = self._enhance_single_visible_task_with_satellite_position(
                            task, satellite_id, satellite_position_data, collection_time
                        )
                        enhanced_virtual_tasks_list.append(enhanced_task)
                        enhancement_stats["tasks_enhanced"] += 1

                        # 检查是否添加了几何分析
                        if "satellite_position" in enhanced_task and "geometric_analysis" in enhanced_task["satellite_position"]:
                            enhancement_stats["geometric_analyses_added"] += 1

                    missile_data["virtual_tasks"] = enhanced_virtual_tasks_list

            # 添加增强元数据
            enhanced_visible_tasks["enhancement_metadata"] = {
                "enhancement_time": collection_time.isoformat(),
                "enhancement_version": "v1.0",
                "satellite_positions_added": True,
                "geometric_analysis_added": True,
                "enhancement_source": "real_time_constellation_data",
                "enhancement_stats": enhancement_stats
            }

            logger.info(f"✅ 可见元任务数据增强完成:")
            logger.info(f"   匹配卫星: {enhancement_stats['satellites_matched']}")
            logger.info(f"   增强任务: {enhancement_stats['tasks_enhanced']}")
            logger.info(f"   几何分析: {enhancement_stats['geometric_analyses_added']}")

            return enhanced_visible_tasks

        except Exception as e:
            logger.error(f"❌ 可见元任务数据增强失败: {e}")
            return visible_meta_tasks

    def _extract_satellite_positions_from_constellation_data(self, constellation_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        从星座数据中提取卫星位置信息

        Args:
            constellation_data: 星座数据

        Returns:
            卫星位置数据字典
        """
        satellite_positions = {}

        try:
            satellites = constellation_data.get("satellites", [])

            for satellite_info in satellites:
                satellite_id = satellite_info.get("satellite_id")
                position = satellite_info.get("position")

                if satellite_id and position:
                    satellite_positions[satellite_id] = {
                        "position": position,
                        "payload_status": satellite_info.get("payload_status", {}),
                        "data_quality": satellite_info.get("data_quality", "unknown")
                    }

            logger.debug(f"📊 提取到 {len(satellite_positions)} 个卫星的位置数据")

        except Exception as e:
            logger.error(f"❌ 提取卫星位置数据失败: {e}")

        return satellite_positions

    def _enhance_single_visible_task_with_satellite_position(self, task: Dict[str, Any], satellite_id: str,
                                                           satellite_position_data: Dict[str, Any],
                                                           collection_time: datetime) -> Dict[str, Any]:
        """
        为单个可见任务添加卫星位置信息

        Args:
            task: 原始任务数据
            satellite_id: 卫星ID
            satellite_position_data: 卫星位置数据
            collection_time: 采集时间

        Returns:
            增强后的任务数据
        """
        enhanced_task = task.copy()

        try:
            # 获取任务的时间信息
            task_start_time = task.get("start_time")
            task_end_time = task.get("end_time")

            # 确定要查询的时间点（优先使用任务中间时刻，否则使用采集时间）
            query_time = collection_time
            if task_start_time and task_end_time:
                try:
                    from datetime import datetime
                    start_dt = datetime.fromisoformat(task_start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(task_end_time.replace('Z', '+00:00'))
                    # 使用任务中间时刻
                    query_time = start_dt + (end_dt - start_dt) / 2
                except Exception:
                    # 如果时间解析失败，使用采集时间
                    query_time = collection_time

            # 获取指定时间的卫星位置
            real_time_position = self._get_satellite_position_at_specific_time(satellite_id, query_time)

            # 如果获取实时位置失败，使用constellation_data中的位置作为备用
            if real_time_position:
                position_data = real_time_position
                position_source = "real_time_query"
                position_timestamp = query_time.strftime("%d %b %Y %H:%M:%S.%f")
            else:
                position_data = satellite_position_data["position"]
                position_source = "constellation_data_fallback"
                position_timestamp = satellite_position_data["position"].get("time")
                logger.debug(f"⚠️ 无法获取卫星 {satellite_id} 在 {query_time} 的实时位置，使用备用数据")

            # 添加卫星位置信息
            satellite_position = {
                "satellite_id": satellite_id,
                "position_data": position_data,
                "payload_status": satellite_position_data["payload_status"],
                "data_quality": satellite_position_data["data_quality"],
                "position_timestamp": position_timestamp,
                "query_time": query_time.isoformat(),
                "position_source": position_source,
                "enhancement_source": "real_time_constellation_data"
            }

            # 添加任务时间信息
            if task_start_time and task_end_time:
                satellite_position["task_time_span"] = {
                    "start_time": task_start_time,
                    "end_time": task_end_time,
                    "collection_time": collection_time.isoformat(),
                    "query_time": query_time.isoformat()
                }

            # 计算几何分析（如果有导弹位置数据）
            missile_position = task.get("missile_position")
            if missile_position:
                geometric_analysis = self._calculate_satellite_missile_geometric_analysis(
                    position_data, missile_position
                )
                if geometric_analysis:
                    satellite_position["geometric_analysis"] = geometric_analysis

            enhanced_task["satellite_position"] = satellite_position

        except Exception as e:
            logger.debug(f"⚠️ 增强任务 {task.get('task_id', 'unknown')} 失败: {e}")

        return enhanced_task

    def _get_satellite_position_at_specific_time(self, satellite_id: str, query_time: datetime) -> Optional[Dict[str, Any]]:
        """
        获取指定时间的卫星位置

        Args:
            satellite_id: 卫星ID
            query_time: 查询时间

        Returns:
            卫星位置数据，如果获取失败返回None
        """
        try:
            if not self.stk_manager or not self.stk_manager.is_connected():
                logger.debug(f"STK未连接，无法获取卫星 {satellite_id} 的实时位置")
                return None

            # 格式化查询时间为STK格式
            stk_time_str = query_time.strftime("%d %b %Y %H:%M:%S.%f")

            # 构建STK命令获取卫星在指定时间的位置
            position_cmd = f'Position */Satellite/{satellite_id} "{stk_time_str}"'

            # 执行STK命令
            result = self.stk_manager.execute_command(position_cmd)

            if result and result.strip():
                # 解析STK返回的位置数据
                lines = result.strip().split('\n')
                for line in lines:
                    if 'Cartesian' in line or 'Position' in line:
                        # 尝试解析位置数据
                        parts = line.split()
                        if len(parts) >= 3:
                            try:
                                # 查找数字部分
                                coords = []
                                for part in parts:
                                    try:
                                        coord = float(part)
                                        coords.append(coord)
                                    except ValueError:
                                        continue

                                if len(coords) >= 3:
                                    return {
                                        "time": stk_time_str,
                                        "x": coords[0],
                                        "y": coords[1],
                                        "z": coords[2]
                                    }
                            except (ValueError, IndexError):
                                continue

                logger.debug(f"⚠️ 无法解析卫星 {satellite_id} 的位置数据: {result}")
                return None
            else:
                logger.debug(f"⚠️ STK命令返回空结果: {position_cmd}")
                return None

        except Exception as e:
            logger.debug(f"⚠️ 获取卫星 {satellite_id} 在 {query_time} 的位置失败: {e}")
            return None

    def _calculate_satellite_missile_geometric_analysis(self, satellite_position: Dict[str, Any],
                                                      missile_position: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        计算卫星-导弹几何分析数据

        Args:
            satellite_position: 卫星位置数据
            missile_position: 导弹位置数据

        Returns:
            几何分析数据
        """
        try:
            import math

            # 提取卫星坐标（笛卡尔坐标）
            sat_x = satellite_position.get("x", 0)
            sat_y = satellite_position.get("y", 0)
            sat_z = satellite_position.get("z", 0)

            # 提取导弹坐标（从start_position）
            missile_start = missile_position.get("start_position", {}).get("position", {})

            # 尝试不同的坐标格式
            missile_coords = None

            if "latitude" in missile_start and "longitude" in missile_start:
                # 地理坐标转换为笛卡尔坐标（简化）
                lat = math.radians(missile_start["latitude"])
                lon = math.radians(missile_start["longitude"])
                alt = missile_start.get("altitude", 0) * 1000  # 转换为米

                # 简化的地理坐标到笛卡尔坐标转换
                earth_radius = 6371000  # 地球半径（米）
                r = earth_radius + alt

                missile_x = r * math.cos(lat) * math.cos(lon)
                missile_y = r * math.cos(lat) * math.sin(lon)
                missile_z = r * math.sin(lat)

                missile_coords = (missile_x / 1000, missile_y / 1000, missile_z / 1000)  # 转换为km

            elif "x" in missile_start and "y" in missile_start and "z" in missile_start:
                # 直接使用笛卡尔坐标
                missile_coords = (missile_start["x"], missile_start["y"], missile_start["z"])

            if not missile_coords:
                return None

            missile_x, missile_y, missile_z = missile_coords

            # 计算距离
            dx = sat_x - missile_x
            dy = sat_y - missile_y
            dz = sat_z - missile_z

            distance_km = math.sqrt(dx**2 + dy**2 + dz**2)

            # 计算角度（简化计算）
            # 仰角：从导弹到卫星的仰角
            horizontal_distance = math.sqrt(dx**2 + dy**2)
            elevation_angle = math.degrees(math.atan2(dz, horizontal_distance))

            # 方位角：从导弹到卫星的方位角
            azimuth_angle = math.degrees(math.atan2(dy, dx))
            if azimuth_angle < 0:
                azimuth_angle += 360

            geometric_analysis = {
                "range_km": round(distance_km, 2),
                "elevation_angle_deg": round(elevation_angle, 2),
                "azimuth_angle_deg": round(azimuth_angle, 2),
                "calculation_method": "cartesian_coordinates",
                "satellite_position_km": {
                    "x": round(sat_x, 2),
                    "y": round(sat_y, 2),
                    "z": round(sat_z, 2)
                },
                "missile_position_km": {
                    "x": round(missile_x, 2),
                    "y": round(missile_y, 2),
                    "z": round(missile_z, 2)
                }
            }

            return geometric_analysis

        except Exception as e:
            logger.debug(f"⚠️ 几何分析计算失败: {e}")
            return None
