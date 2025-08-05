#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一数据管理器
用于管理所有采集数据的统一保存，支持JSON和甘特图分文件夹保存
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class UnifiedDataManager:
    """统一数据管理器"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        self.session_data = []
        self.session_dir = None
        self.json_dir = None
        self.charts_dir = None
        
    def initialize_session(self, session_name: str = None) -> Path:
        """
        初始化会话，创建统一的数据保存目录结构
        
        Args:
            session_name: 会话名称（可选）
            
        Returns:
            会话目录路径
        """
        try:
            # 获取输出配置
            if self.config_manager:
                output_config = self.config_manager.get_output_config()
                base_directory = output_config.get("base_directory", "output")
                file_naming = output_config.get("file_naming", {})
                session_prefix = file_naming.get("session_prefix", "session_")
            else:
                base_directory = "output"
                session_prefix = "session_"
            
            # 创建会话目录
            if session_name:
                session_dir_name = f"{session_prefix}{session_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            else:
                session_dir_name = f"{session_prefix}{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.session_dir = Path(base_directory) / "unified_collections" / session_dir_name
            
            # 创建目录结构
            self.session_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建分类子目录
            self.json_dir = self.session_dir / "json_data"
            self.charts_dir = self.session_dir / "charts"
            logs_dir = self.session_dir / "logs"
            analysis_dir = self.session_dir / "analysis"
            
            self.json_dir.mkdir(exist_ok=True)
            self.charts_dir.mkdir(exist_ok=True)
            logs_dir.mkdir(exist_ok=True)
            analysis_dir.mkdir(exist_ok=True)
            
            logger.info(f"📁 统一会话目录已创建: {self.session_dir}")
            logger.info(f"   JSON数据目录: {self.json_dir}")
            logger.info(f"   图表目录: {self.charts_dir}")
            logger.info(f"   日志目录: {logs_dir}")
            logger.info(f"   分析目录: {analysis_dir}")
            
            return self.session_dir
            
        except Exception as e:
            logger.error(f"❌ 初始化会话失败: {e}")
            raise
    
    def save_collection_data(self, collection_index: int, collection_result: Dict[str, Any], 
                           conflict_resolution_data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """
        保存单次采集的数据到统一目录
        
        Args:
            collection_index: 采集索引
            collection_result: 原始采集数据
            conflict_resolution_data: 冲突消解数据
            
        Returns:
            保存的文件路径字典
        """
        try:
            if not self.session_dir:
                raise ValueError("会话未初始化，请先调用 initialize_session()")
            
            saved_files = {}
            
            # 1. 保存原始采集数据
            original_file = self.json_dir / f"collection_{collection_index:03d}_original.json"
            with open(original_file, 'w', encoding='utf-8') as f:
                json.dump(collection_result, f, indent=2, ensure_ascii=False, default=str)
            saved_files['original_data'] = str(original_file)
            
            # 2. 保存冲突消解数据（如果有）
            if conflict_resolution_data:
                conflict_file = self.json_dir / f"collection_{collection_index:03d}_conflict_resolution.json"
                with open(conflict_file, 'w', encoding='utf-8') as f:
                    json.dump(conflict_resolution_data, f, indent=2, ensure_ascii=False, default=str)
                saved_files['conflict_resolution'] = str(conflict_file)
            
            # 3. 保存时间轴数据（如果有）
            timeline_data = self._extract_timeline_data(collection_result)
            if timeline_data:
                timeline_file = self.json_dir / f"collection_{collection_index:03d}_timeline.json"
                with open(timeline_file, 'w', encoding='utf-8') as f:
                    json.dump(timeline_data, f, indent=2, ensure_ascii=False, default=str)
                saved_files['timeline_data'] = str(timeline_file)
            
            # 4. 保存采集摘要
            summary_data = self._create_collection_summary(collection_index, collection_result, conflict_resolution_data)
            summary_file = self.json_dir / f"collection_{collection_index:03d}_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False, default=str)
            saved_files['summary'] = str(summary_file)
            
            # 5. 添加到会话数据
            self.session_data.append({
                "collection_index": collection_index,
                "collection_time": collection_result.get("collection_time", ""),
                "files": saved_files,
                "statistics": summary_data.get("statistics", {})
            })
            
            logger.info(f"💾 第 {collection_index} 次采集数据已保存到统一目录")
            logger.info(f"   原始数据: {original_file.name}")
            if conflict_resolution_data:
                logger.info(f"   冲突消解数据: {conflict_file.name}")
            
            return saved_files
            
        except Exception as e:
            logger.error(f"❌ 保存采集数据失败: {e}")
            return {}
    
    def save_gantt_chart(self, collection_index: int, chart_path: str, chart_type: str = "gantt") -> Optional[str]:
        """
        保存甘特图到图表目录
        
        Args:
            collection_index: 采集索引
            chart_path: 原始图表路径
            chart_type: 图表类型
            
        Returns:
            新的图表路径
        """
        try:
            if not self.charts_dir:
                raise ValueError("会话未初始化，请先调用 initialize_session()")
            
            import shutil
            
            # 确定新的文件名
            chart_file = Path(chart_path)
            new_chart_name = f"collection_{collection_index:03d}_{chart_type}_{chart_file.name}"
            new_chart_path = self.charts_dir / new_chart_name
            
            # 复制图表文件
            shutil.copy2(chart_path, new_chart_path)
            
            logger.info(f"📈 第 {collection_index} 次采集的{chart_type}图表已保存: {new_chart_name}")
            
            return str(new_chart_path)
            
        except Exception as e:
            logger.error(f"❌ 保存图表失败: {e}")
            return None
    
    def generate_session_summary(self) -> Dict[str, Any]:
        """生成会话汇总数据"""
        try:
            if not self.session_data:
                logger.warning("⚠️ 没有会话数据可汇总")
                return {}
            
            # 统计信息
            total_collections = len(self.session_data)
            total_meta_tasks = sum(data.get("statistics", {}).get("total_meta_tasks", 0) for data in self.session_data)
            total_visible_tasks = sum(data.get("statistics", {}).get("total_visible_tasks", 0) for data in self.session_data)
            total_missiles = sum(data.get("statistics", {}).get("total_missiles", 0) for data in self.session_data)
            
            # 时间范围
            collection_times = [data.get("collection_time", "") for data in self.session_data if data.get("collection_time")]
            start_time = min(collection_times) if collection_times else ""
            end_time = max(collection_times) if collection_times else ""
            
            session_summary = {
                "session_info": {
                    "session_dir": str(self.session_dir),
                    "total_collections": total_collections,
                    "start_time": start_time,
                    "end_time": end_time,
                    "created_at": datetime.now().isoformat()
                },
                "statistics": {
                    "total_meta_tasks": total_meta_tasks,
                    "total_visible_tasks": total_visible_tasks,
                    "total_missiles": total_missiles,
                    "average_meta_tasks_per_collection": total_meta_tasks / total_collections if total_collections > 0 else 0,
                    "average_visible_tasks_per_collection": total_visible_tasks / total_collections if total_collections > 0 else 0
                },
                "collections": self.session_data,
                "directory_structure": {
                    "json_data": str(self.json_dir),
                    "charts": str(self.charts_dir),
                    "logs": str(self.session_dir / "logs"),
                    "analysis": str(self.session_dir / "analysis")
                }
            }
            
            return session_summary
            
        except Exception as e:
            logger.error(f"❌ 生成会话汇总失败: {e}")
            return {}
    
    def save_session_summary(self) -> Optional[str]:
        """保存会话汇总到文件"""
        try:
            if not self.session_dir:
                raise ValueError("会话未初始化")
            
            session_summary = self.generate_session_summary()
            if not session_summary:
                return None
            
            # 保存JSON格式汇总
            summary_file = self.session_dir / "session_summary.json"
            with open(summary_file, 'w', encoding='utf-8') as f:
                json.dump(session_summary, f, indent=2, ensure_ascii=False, default=str)
            
            # 保存可读文本格式汇总
            text_summary_file = self.session_dir / "session_summary.txt"
            with open(text_summary_file, 'w', encoding='utf-8') as f:
                f.write("STK星座预警冲突消解数据采集会话汇总\n")
                f.write("=" * 60 + "\n\n")
                
                session_info = session_summary.get("session_info", {})
                f.write(f"会话目录: {session_info.get('session_dir', '')}\n")
                f.write(f"总采集次数: {session_info.get('total_collections', 0)}\n")
                f.write(f"开始时间: {session_info.get('start_time', '')}\n")
                f.write(f"结束时间: {session_info.get('end_time', '')}\n\n")
                
                statistics = session_summary.get("statistics", {})
                f.write("统计信息:\n")
                f.write(f"  总元任务数: {statistics.get('total_meta_tasks', 0)}\n")
                f.write(f"  总可见任务数: {statistics.get('total_visible_tasks', 0)}\n")
                f.write(f"  总导弹数: {statistics.get('total_missiles', 0)}\n")
                f.write(f"  平均每次采集元任务数: {statistics.get('average_meta_tasks_per_collection', 0):.2f}\n")
                f.write(f"  平均每次采集可见任务数: {statistics.get('average_visible_tasks_per_collection', 0):.2f}\n\n")
                
                f.write("目录结构:\n")
                directory_structure = session_summary.get("directory_structure", {})
                for key, path in directory_structure.items():
                    f.write(f"  {key}: {path}\n")
                
                f.write("\n采集详情:\n")
                for collection in session_summary.get("collections", []):
                    f.write(f"  第{collection.get('collection_index', 0)}次采集: {collection.get('collection_time', '')}\n")
            
            logger.info(f"📋 会话汇总已保存:")
            logger.info(f"   JSON格式: {summary_file}")
            logger.info(f"   文本格式: {text_summary_file}")
            
            return str(summary_file)
            
        except Exception as e:
            logger.error(f"❌ 保存会话汇总失败: {e}")
            return None
    
    def _extract_timeline_data(self, collection_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从采集结果中提取时间轴数据"""
        try:
            from src.utils.timeline_converter import TimelineConverter
            
            converter = TimelineConverter()
            timeline_data = converter.convert_collection_data(collection_result)
            
            return timeline_data
            
        except Exception as e:
            logger.warning(f"⚠️ 提取时间轴数据失败: {e}")
            return None
    
    def _create_collection_summary(self, collection_index: int, collection_result: Dict[str, Any], 
                                 conflict_resolution_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """创建单次采集的摘要数据"""
        try:
            # 基础信息
            rolling_info = collection_result.get("rolling_collection_info", {})
            
            # 元任务统计
            meta_tasks = collection_result.get("meta_tasks", {}).get("meta_tasks", {})
            total_meta_tasks = sum(len(missile_data.get("atomic_tasks", [])) for missile_data in meta_tasks.values())
            total_real_tasks = sum(missile_data.get("real_task_count", 0) for missile_data in meta_tasks.values())
            total_virtual_tasks = sum(missile_data.get("virtual_task_count", 0) for missile_data in meta_tasks.values())
            
            # 可见任务统计
            visible_meta_tasks = collection_result.get("visible_meta_tasks", {})
            constellation_sets = visible_meta_tasks.get("constellation_visible_task_sets", {})
            total_visible_tasks = sum(
                len(satellite_data.get("missile_tasks", {}).get(missile_id, {}).get("visible_tasks", []))
                for satellite_data in constellation_sets.values()
                for missile_id in satellite_data.get("missile_tasks", {})
            )
            total_virtual_visible_tasks = sum(
                len(satellite_data.get("missile_tasks", {}).get(missile_id, {}).get("virtual_tasks", []))
                for satellite_data in constellation_sets.values()
                for missile_id in satellite_data.get("missile_tasks", {})
            )
            
            summary = {
                "collection_info": {
                    "index": collection_index,
                    "time": collection_result.get("collection_time", ""),
                    "midcourse_missiles": rolling_info.get("midcourse_missiles", []),
                    "total_missiles_in_scenario": rolling_info.get("total_missiles_in_scenario", 0)
                },
                "statistics": {
                    "total_missiles": len(meta_tasks),
                    "total_meta_tasks": total_meta_tasks,
                    "total_real_tasks": total_real_tasks,
                    "total_virtual_tasks": total_virtual_tasks,
                    "total_satellites": len(constellation_sets),
                    "total_visible_tasks": total_visible_tasks,
                    "total_virtual_visible_tasks": total_virtual_visible_tasks
                },
                "conflict_resolution": {
                    "data_available": conflict_resolution_data is not None,
                    "enhanced_with_positions": conflict_resolution_data.get("metadata", {}).get("conflict_resolution_info", {}).get("position_data_included", False) if conflict_resolution_data else False,
                    "timeline_complete": conflict_resolution_data.get("metadata", {}).get("conflict_resolution_info", {}).get("timeline_complete", False) if conflict_resolution_data else False
                } if conflict_resolution_data else {"data_available": False}
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ 创建采集摘要失败: {e}")
            return {}
