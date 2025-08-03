"""
可见元子任务计算器
负责计算每个卫星对所有目标的可见元子任务和虚拟原子任务
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from ..utils.config_manager import get_config_manager

logger = logging.getLogger(__name__)

class VisibleMetaTaskCalculator:
    """可见元子任务计算器"""
    
    def __init__(self, visibility_calculator, meta_task_manager, config_manager=None):
        """
        初始化可见元子任务计算器
        
        Args:
            visibility_calculator: 可见性计算器
            meta_task_manager: 元任务管理器
            config_manager: 配置管理器
        """
        self.visibility_calculator = visibility_calculator
        self.meta_task_manager = meta_task_manager
        self.config_manager = config_manager or get_config_manager()
        
        # 获取可见元子任务配置
        self.meta_task_config = self.config_manager.config.get("meta_task_management", {})
        self.visible_task_config = self.meta_task_config.get("visible_task_criteria", {})
        self.coverage_requirement = self.visible_task_config.get("coverage_requirement", "complete")
        self.minimum_overlap_ratio = self.visible_task_config.get("minimum_overlap_ratio", 1.0)
        
        # 存储可见元任务集
        self.constellation_visible_task_sets = {}
        
        logger.info("👁️ 可见元子任务计算器初始化完成")
        logger.info(f"   覆盖要求: {self.coverage_requirement}")
        logger.info(f"   最小重叠比例: {self.minimum_overlap_ratio}")
    
    def calculate_constellation_visible_meta_tasks(self, satellite_ids: List[str], 
                                                 missile_ids: List[str]) -> Dict[str, Any]:
        """
        计算整个星座的可见元任务集
        
        Args:
            satellite_ids: 卫星ID列表
            missile_ids: 导弹ID列表
            
        Returns:
            星座可见元任务集字典
        """
        try:
            logger.info(f"👁️ 开始计算星座可见元任务集")
            logger.info(f"   卫星数量: {len(satellite_ids)}")
            logger.info(f"   导弹数量: {len(missile_ids)}")
            
            constellation_results = {}
            
            # 为每颗卫星计算可见元任务集
            for satellite_id in satellite_ids:
                logger.info(f"🛰️ 计算卫星 {satellite_id} 的可见元任务集...")
                
                satellite_visible_tasks = self._calculate_satellite_visible_meta_tasks(
                    satellite_id, missile_ids
                )
                
                constellation_results[satellite_id] = satellite_visible_tasks
                
                # 统计信息
                total_visible = sum(len(missile_tasks.get("visible_tasks", [])) 
                                  for missile_tasks in satellite_visible_tasks.get("missile_tasks", {}).values())
                total_virtual = sum(len(missile_tasks.get("virtual_tasks", [])) 
                                  for missile_tasks in satellite_visible_tasks.get("missile_tasks", {}).values())
                
                logger.info(f"   ✅ 卫星 {satellite_id}: 可见任务 {total_visible}, 虚拟任务 {total_virtual}")
            
            # 存储结果
            self.constellation_visible_task_sets = constellation_results
            
            # 生成汇总信息
            summary = self._generate_constellation_summary(constellation_results)
            
            logger.info(f"✅ 星座可见元任务集计算完成")
            logger.info(f"   总可见任务: {summary['total_visible_tasks']}")
            logger.info(f"   总虚拟任务: {summary['total_virtual_tasks']}")
            
            return {
                "constellation_visible_task_sets": constellation_results,
                "summary": summary,
                "calculation_time": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 星座可见元任务集计算失败: {e}")
            return {}
    
    def _calculate_satellite_visible_meta_tasks(self, satellite_id: str, 
                                              missile_ids: List[str]) -> Dict[str, Any]:
        """
        计算单颗卫星对所有导弹的可见元任务
        
        Args:
            satellite_id: 卫星ID
            missile_ids: 导弹ID列表
            
        Returns:
            卫星可见元任务字典
        """
        try:
            satellite_results = {
                "satellite_id": satellite_id,
                "missile_tasks": {},
                "total_visible_tasks": 0,
                "total_virtual_tasks": 0,
                "calculation_time": datetime.now().isoformat()
            }
            
            # 对每个导弹计算可见元任务
            for missile_id in missile_ids:
                missile_visible_tasks = self._calculate_missile_visible_meta_tasks(
                    satellite_id, missile_id
                )
                
                satellite_results["missile_tasks"][missile_id] = missile_visible_tasks
                satellite_results["total_visible_tasks"] += len(missile_visible_tasks.get("visible_tasks", []))
                satellite_results["total_virtual_tasks"] += len(missile_visible_tasks.get("virtual_tasks", []))
            
            return satellite_results
            
        except Exception as e:
            logger.error(f"❌ 计算卫星 {satellite_id} 可见元任务失败: {e}")
            return {}
    
    def _calculate_missile_visible_meta_tasks(self, satellite_id: str, 
                                            missile_id: str) -> Dict[str, Any]:
        """
        计算卫星对单个导弹的可见元任务
        
        Args:
            satellite_id: 卫星ID
            missile_id: 导弹ID
            
        Returns:
            导弹可见元任务字典
        """
        try:
            logger.debug(f"🔍 计算 {satellite_id} -> {missile_id} 可见元任务")
            
            # 1. 获取导弹的元子任务集
            missile_meta_tasks = self.meta_task_manager.get_meta_tasks_for_missile(missile_id)
            if not missile_meta_tasks:
                logger.warning(f"⚠️ 导弹 {missile_id} 没有元任务")
                return {"visible_tasks": [], "virtual_tasks": []}
            
            atomic_tasks = missile_meta_tasks.get("atomic_tasks", [])
            
            # 2. 获取卫星对导弹的可见窗口
            visibility_result = self.visibility_calculator.calculate_satellite_to_missile_access(
                satellite_id, missile_id
            )
            
            if not visibility_result or not visibility_result.get("success"):
                logger.debug(f"   无可见性数据，所有任务为虚拟任务")
                return {
                    "visible_tasks": [],
                    "virtual_tasks": atomic_tasks.copy(),
                    "access_intervals": [],
                    "has_access": False
                }
            
            access_intervals = visibility_result.get("access_intervals", [])
            
            # 3. 逐一比较元子任务与可见窗口
            visible_tasks = []
            virtual_tasks = []
            
            for atomic_task in atomic_tasks:
                is_visible = self._is_atomic_task_visible(atomic_task, access_intervals)
                
                if is_visible:
                    # 添加可见性信息
                    visible_task = atomic_task.copy()
                    visible_task["visibility_info"] = {
                        "is_visible": True,
                        "overlapping_windows": self._get_overlapping_windows(atomic_task, access_intervals),
                        "coverage_ratio": self._calculate_coverage_ratio(atomic_task, access_intervals)
                    }
                    visible_tasks.append(visible_task)
                else:
                    # 虚拟原子任务
                    virtual_task = atomic_task.copy()
                    virtual_task["visibility_info"] = {
                        "is_visible": False,
                        "reason": "no_coverage_or_insufficient_overlap"
                    }
                    virtual_tasks.append(virtual_task)
            
            result = {
                "visible_tasks": visible_tasks,
                "virtual_tasks": virtual_tasks,
                "access_intervals": access_intervals,
                "has_access": len(access_intervals) > 0,
                "visibility_summary": {
                    "total_tasks": len(atomic_tasks),
                    "visible_count": len(visible_tasks),
                    "virtual_count": len(virtual_tasks),
                    "visibility_ratio": len(visible_tasks) / len(atomic_tasks) if atomic_tasks else 0
                }
            }
            
            logger.debug(f"   ✅ {satellite_id} -> {missile_id}: "
                        f"可见 {len(visible_tasks)}, 虚拟 {len(virtual_tasks)}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 计算 {satellite_id} -> {missile_id} 可见元任务失败: {e}")
            return {"visible_tasks": [], "virtual_tasks": []}
    
    def _is_atomic_task_visible(self, atomic_task: Dict[str, Any], 
                              access_intervals: List[Dict[str, Any]]) -> bool:
        """
        判断元子任务是否为可见元子任务
        根据配置的覆盖要求判断：能完全覆盖该时间段定义为可见元子任务
        
        Args:
            atomic_task: 元子任务
            access_intervals: 访问间隔列表
            
        Returns:
            是否为可见元子任务
        """
        try:
            if not access_intervals:
                return False
            
            task_start = atomic_task["start_time"]
            task_end = atomic_task["end_time"]
            
            if isinstance(task_start, str):
                task_start = datetime.fromisoformat(task_start.replace('Z', '+00:00'))
            if isinstance(task_end, str):
                task_end = datetime.fromisoformat(task_end.replace('Z', '+00:00'))
            
            # 根据覆盖要求判断
            if self.coverage_requirement == "complete":
                # 完全覆盖：任务时间段必须完全在某个可见窗口内
                return self._is_completely_covered(task_start, task_end, access_intervals)
            elif self.coverage_requirement == "partial":
                # 部分覆盖：任务时间段与可见窗口有重叠即可
                coverage_ratio = self._calculate_coverage_ratio_value(task_start, task_end, access_intervals)
                return coverage_ratio >= self.minimum_overlap_ratio
            else:
                # 默认使用完全覆盖
                return self._is_completely_covered(task_start, task_end, access_intervals)
                
        except Exception as e:
            logger.debug(f"判断元子任务可见性失败: {e}")
            return False
    
    def _is_completely_covered(self, task_start: datetime, task_end: datetime, 
                             access_intervals: List[Dict[str, Any]]) -> bool:
        """
        判断任务时间段是否被完全覆盖
        
        Args:
            task_start: 任务开始时间
            task_end: 任务结束时间
            access_intervals: 访问间隔列表
            
        Returns:
            是否完全覆盖
        """
        try:
            for interval in access_intervals:
                interval_start_str = interval.get("start") or interval.get("Start")
                interval_end_str = interval.get("stop") or interval.get("Stop") or interval.get("end") or interval.get("End")
                
                if interval_start_str and interval_end_str:
                    try:
                        interval_start = self._parse_stk_time(interval_start_str)
                        interval_end = self._parse_stk_time(interval_end_str)
                        
                        if interval_start and interval_end:
                            # 检查任务是否完全在这个间隔内
                            if interval_start <= task_start and task_end <= interval_end:
                                return True
                    except Exception:
                        continue
            
            return False
            
        except Exception as e:
            logger.debug(f"判断完全覆盖失败: {e}")
            return False
    
    def _calculate_coverage_ratio_value(self, task_start: datetime, task_end: datetime, 
                                      access_intervals: List[Dict[str, Any]]) -> float:
        """
        计算覆盖比例
        
        Args:
            task_start: 任务开始时间
            task_end: 任务结束时间
            access_intervals: 访问间隔列表
            
        Returns:
            覆盖比例 (0.0 - 1.0)
        """
        try:
            task_duration = (task_end - task_start).total_seconds()
            if task_duration <= 0:
                return 0.0
            
            covered_duration = 0.0
            
            for interval in access_intervals:
                interval_start_str = interval.get("start") or interval.get("Start")
                interval_end_str = interval.get("stop") or interval.get("Stop") or interval.get("end") or interval.get("End")
                
                if interval_start_str and interval_end_str:
                    try:
                        interval_start = self._parse_stk_time(interval_start_str)
                        interval_end = self._parse_stk_time(interval_end_str)
                        
                        if interval_start and interval_end:
                            # 计算重叠时间
                            overlap_start = max(task_start, interval_start)
                            overlap_end = min(task_end, interval_end)
                            
                            if overlap_start < overlap_end:
                                overlap_duration = (overlap_end - overlap_start).total_seconds()
                                covered_duration += overlap_duration
                    except Exception:
                        continue
            
            return min(covered_duration / task_duration, 1.0)
            
        except Exception as e:
            logger.debug(f"计算覆盖比例失败: {e}")
            return 0.0
    
    def _get_overlapping_windows(self, atomic_task: Dict[str, Any], 
                               access_intervals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        获取与元子任务重叠的可见窗口
        
        Args:
            atomic_task: 元子任务
            access_intervals: 访问间隔列表
            
        Returns:
            重叠的窗口列表
        """
        try:
            overlapping_windows = []
            
            task_start = atomic_task["start_time"]
            task_end = atomic_task["end_time"]
            
            if isinstance(task_start, str):
                task_start = datetime.fromisoformat(task_start.replace('Z', '+00:00'))
            if isinstance(task_end, str):
                task_end = datetime.fromisoformat(task_end.replace('Z', '+00:00'))
            
            for interval in access_intervals:
                interval_start_str = interval.get("start") or interval.get("Start")
                interval_end_str = interval.get("stop") or interval.get("Stop") or interval.get("end") or interval.get("End")
                
                if interval_start_str and interval_end_str:
                    try:
                        interval_start = self._parse_stk_time(interval_start_str)
                        interval_end = self._parse_stk_time(interval_end_str)
                        
                        if interval_start and interval_end:
                            # 检查是否有重叠
                            if task_start < interval_end and task_end > interval_start:
                                overlapping_windows.append({
                                    "window_start": interval_start_str,
                                    "window_end": interval_end_str,
                                    "overlap_start": max(task_start, interval_start).isoformat(),
                                    "overlap_end": min(task_end, interval_end).isoformat()
                                })
                    except Exception:
                        continue
            
            return overlapping_windows
            
        except Exception as e:
            logger.debug(f"获取重叠窗口失败: {e}")
            return []
    
    def _calculate_coverage_ratio(self, atomic_task: Dict[str, Any], 
                                access_intervals: List[Dict[str, Any]]) -> float:
        """
        计算元子任务的覆盖比例
        
        Args:
            atomic_task: 元子任务
            access_intervals: 访问间隔列表
            
        Returns:
            覆盖比例
        """
        try:
            task_start = atomic_task["start_time"]
            task_end = atomic_task["end_time"]
            
            if isinstance(task_start, str):
                task_start = datetime.fromisoformat(task_start.replace('Z', '+00:00'))
            if isinstance(task_end, str):
                task_end = datetime.fromisoformat(task_end.replace('Z', '+00:00'))
            
            return self._calculate_coverage_ratio_value(task_start, task_end, access_intervals)
            
        except Exception as e:
            logger.debug(f"计算覆盖比例失败: {e}")
            return 0.0
    
    def _parse_stk_time(self, time_str: str) -> Optional[datetime]:
        """
        解析STK时间格式
        
        Args:
            time_str: STK时间字符串
            
        Returns:
            datetime对象
        """
        try:
            # STK格式: "26 Jul 2025 04:12:56.535"
            return datetime.strptime(time_str, "%d %b %Y %H:%M:%S.%f")
        except:
            try:
                # 尝试其他格式
                return datetime.strptime(time_str, "%d %b %Y %H:%M:%S")
            except:
                return None
    
    def _generate_constellation_summary(self, constellation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成星座可见元任务汇总信息
        
        Args:
            constellation_results: 星座计算结果
            
        Returns:
            汇总信息字典
        """
        try:
            total_visible_tasks = 0
            total_virtual_tasks = 0
            satellite_count = len(constellation_results)
            
            for satellite_id, satellite_results in constellation_results.items():
                total_visible_tasks += satellite_results.get("total_visible_tasks", 0)
                total_virtual_tasks += satellite_results.get("total_virtual_tasks", 0)
            
            total_tasks = total_visible_tasks + total_virtual_tasks
            
            return {
                "satellite_count": satellite_count,
                "total_visible_tasks": total_visible_tasks,
                "total_virtual_tasks": total_virtual_tasks,
                "total_tasks": total_tasks,
                "visibility_ratio": total_visible_tasks / total_tasks if total_tasks > 0 else 0,
                "average_visible_per_satellite": total_visible_tasks / satellite_count if satellite_count > 0 else 0,
                "average_virtual_per_satellite": total_virtual_tasks / satellite_count if satellite_count > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"❌ 生成汇总信息失败: {e}")
            return {}
    
    def get_constellation_visible_task_sets(self) -> Dict[str, Any]:
        """
        获取星座可见元任务集
        
        Returns:
            星座可见元任务集字典
        """
        return self.constellation_visible_task_sets
    
    def get_satellite_visible_tasks(self, satellite_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定卫星的可见元任务
        
        Args:
            satellite_id: 卫星ID
            
        Returns:
            卫星可见元任务字典
        """
        return self.constellation_visible_task_sets.get(satellite_id)
