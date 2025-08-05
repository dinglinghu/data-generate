#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冲突消解数据处理器
用于生成包含虚拟元任务填充的完整时间轴数据，支持星座预警领域的冲突消解
"""

import json
import tempfile
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class ConflictResolutionDataProcessor:
    """冲突消解数据处理器"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        
    def generate_conflict_resolution_data(self, collection_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        生成冲突消解数据（包含虚拟元任务填充的完整时间轴）
        
        Args:
            collection_result: 原始采集数据
            
        Returns:
            包含完整时间轴的冲突消解数据
        """
        try:
            from aerospace_meta_task_gantt import AerospaceMetaTaskGantt
            
            # 创建临时文件保存采集数据
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as temp_file:
                json.dump(collection_result, temp_file, indent=2, ensure_ascii=False, default=str)
                temp_file_path = temp_file.name
            
            try:
                # 创建甘特图生成器实例
                gantt = AerospaceMetaTaskGantt()
                
                # 加载数据
                gantt.load_data(temp_file_path)
                
                # 提取元任务数据
                meta_df = gantt.extract_meta_task_data()
                logger.info(f"📊 提取到 {len(meta_df)} 条元任务数据")
                
                # 提取可见元任务数据
                visible_df = gantt.extract_visible_meta_task_data()
                logger.info(f"👁️ 提取到 {len(visible_df)} 条可见元任务数据")
                
                if meta_df.empty and visible_df.empty:
                    logger.warning("⚠️ 没有足够的数据生成冲突消解数据")
                    return None
                
                # 确定时间范围
                all_times = []
                if not meta_df.empty:
                    all_times.extend(meta_df['Start'].tolist())
                    all_times.extend(meta_df['End'].tolist())
                if not visible_df.empty:
                    all_times.extend(visible_df['Start'].tolist())
                    all_times.extend(visible_df['End'].tolist())
                
                if not all_times:
                    logger.warning("⚠️ 无法确定时间范围")
                    return None
                
                min_time = min(all_times)
                max_time = max(all_times)
                
                # 为元任务填充虚拟任务，确保时间轴完整
                complete_meta_df = self._fill_meta_timeline_with_positions(meta_df, min_time, max_time, gantt)
                
                # 为可见元任务填充虚拟任务，确保时间轴完整
                complete_visible_df = self._fill_visible_timeline(visible_df, min_time, max_time, gantt)
                
                # 添加位置信息到真实任务
                enhanced_meta_df = self._enhance_with_position_data(complete_meta_df, collection_result)
                enhanced_visible_df = self._enhance_with_satellite_position_data(complete_visible_df, collection_result)
                
                # 构建冲突消解数据结构
                conflict_resolution_data = {
                    "metadata": {
                        "collection_time": collection_result.get("collection_time", ""),
                        "collection_index": collection_result.get("rolling_collection_info", {}).get("collection_index", 0),
                        "time_range": {
                            "start_time": min_time.isoformat(),
                            "end_time": max_time.isoformat(),
                            "duration_seconds": (max_time - min_time).total_seconds()
                        },
                        "data_statistics": {
                            "original_meta_tasks": len(meta_df),
                            "complete_meta_tasks": len(enhanced_meta_df),
                            "original_visible_tasks": len(visible_df),
                            "complete_visible_tasks": len(enhanced_visible_df)
                        },
                        "conflict_resolution_info": {
                            "virtual_tasks_filled": True,
                            "position_data_included": True,
                            "timeline_complete": True
                        }
                    },
                    "complete_meta_tasks": self._dataframe_to_dict_list(enhanced_meta_df),
                    "complete_visible_tasks": self._dataframe_to_dict_list(enhanced_visible_df),
                    "timeline_analysis": self._analyze_timeline_conflicts(enhanced_meta_df, enhanced_visible_df),
                    "original_collection_data": collection_result
                }
                
                logger.info(f"✅ 冲突消解数据生成成功")
                logger.info(f"   元任务: {len(meta_df)} → {len(enhanced_meta_df)} (填充虚拟任务)")
                logger.info(f"   可见任务: {len(visible_df)} → {len(enhanced_visible_df)} (填充虚拟任务)")
                
                return conflict_resolution_data
                
            finally:
                # 清理临时文件
                Path(temp_file_path).unlink(missing_ok=True)
                
        except Exception as e:
            logger.error(f"❌ 生成冲突消解数据失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _fill_meta_timeline_with_positions(self, meta_df: pd.DataFrame, min_time: datetime, max_time: datetime, gantt) -> pd.DataFrame:
        """为元任务时间轴填充虚拟任务"""
        if meta_df.empty:
            return meta_df
            
        # 创建Y轴位置映射
        unique_missiles = sorted(meta_df['MissileID'].unique())
        y_positions = {}
        y_pos = 0
        for missile_id in unique_missiles:
            y_positions[f'{missile_id}_atomic'] = y_pos
            y_pos += 1
            y_pos += 0.5
        
        # 使用甘特图生成器的填充方法
        return gantt._fill_virtual_tasks_for_meta_timeline(meta_df, min_time, max_time, y_positions)
    
    def _fill_visible_timeline(self, visible_df: pd.DataFrame, min_time: datetime, max_time: datetime, gantt) -> pd.DataFrame:
        """为可见元任务时间轴填充虚拟任务"""
        if visible_df.empty:
            return visible_df

        # 为可见任务填充虚拟任务（类似元任务的填充逻辑）
        complete_tasks = []

        # 获取所有唯一的卫星ID
        unique_satellites = sorted(visible_df['SatelliteID'].unique()) if not visible_df.empty else []

        # 为每个卫星生成完整时间轴
        for satellite_id in unique_satellites:
            # 获取该卫星的现有任务
            satellite_tasks = visible_df[visible_df['SatelliteID'] == satellite_id].copy()

            if satellite_tasks.empty:
                # 如果没有任何任务，为整个时间范围填充虚拟任务
                virtual_task = {
                    'Start': min_time,
                    'End': max_time,
                    'SatelliteID': satellite_id,
                    'Type': 'virtual_atomic_task',
                    'TaskIndex': 0,
                    'TaskID': f'virtual_{satellite_id}_full',
                    'TaskName': f'{satellite_id} 虚拟可见任务',
                    'Duration': (max_time - min_time).total_seconds(),
                    'Category': '虚拟可见任务',
                    'Level': 'virtual_visible',
                    'IsVirtualTask': True
                }
                complete_tasks.append(virtual_task)
            else:
                # 如果有任务，先添加所有原始任务
                for _, task in satellite_tasks.iterrows():
                    complete_tasks.append(task.to_dict())

                # 然后检查是否需要填充空隙
                satellite_tasks_sorted = satellite_tasks.sort_values('Start')

                # 检查开始前的空隙
                first_task_start = satellite_tasks_sorted.iloc[0]['Start']
                if min_time < first_task_start:
                    virtual_task = {
                        'Start': min_time,
                        'End': first_task_start,
                        'SatelliteID': satellite_id,
                        'Type': 'virtual_atomic_task',
                        'TaskIndex': 0,
                        'TaskID': f'virtual_{satellite_id}_start',
                        'TaskName': f'{satellite_id} 虚拟可见任务',
                        'Duration': (first_task_start - min_time).total_seconds(),
                        'Category': '虚拟可见任务',
                        'Level': 'virtual_visible',
                        'IsVirtualTask': True
                    }
                    complete_tasks.append(virtual_task)

                # 检查任务间的空隙
                for i in range(len(satellite_tasks_sorted) - 1):
                    current_task_end = satellite_tasks_sorted.iloc[i]['End']
                    next_task_start = satellite_tasks_sorted.iloc[i + 1]['Start']

                    if current_task_end < next_task_start:
                        virtual_task = {
                            'Start': current_task_end,
                            'End': next_task_start,
                            'SatelliteID': satellite_id,
                            'Type': 'virtual_atomic_task',
                            'TaskIndex': i + 1,
                            'TaskID': f'virtual_{satellite_id}_gap_{i}',
                            'TaskName': f'{satellite_id} 虚拟可见任务',
                            'Duration': (next_task_start - current_task_end).total_seconds(),
                            'Category': '虚拟可见任务',
                            'Level': 'virtual_visible',
                            'IsVirtualTask': True
                        }
                        complete_tasks.append(virtual_task)

                # 检查结束后的空隙
                last_task_end = satellite_tasks_sorted.iloc[-1]['End']
                if last_task_end < max_time:
                    virtual_task = {
                        'Start': last_task_end,
                        'End': max_time,
                        'SatelliteID': satellite_id,
                        'Type': 'virtual_atomic_task',
                        'TaskIndex': len(satellite_tasks_sorted),
                        'TaskID': f'virtual_{satellite_id}_end',
                        'TaskName': f'{satellite_id} 虚拟可见任务',
                        'Duration': (max_time - last_task_end).total_seconds(),
                        'Category': '虚拟可见任务',
                        'Level': 'virtual_visible',
                        'IsVirtualTask': True
                    }
                    complete_tasks.append(virtual_task)

        return pd.DataFrame(complete_tasks)
    
    def _enhance_with_position_data(self, df: pd.DataFrame, collection_result: Dict[str, Any]) -> pd.DataFrame:
        """为真实元任务添加导弹位置信息"""
        if df.empty:
            return df

        enhanced_df = df.copy()

        # 初始化新列
        enhanced_df['position_data'] = None
        enhanced_df['has_position_data'] = False

        # 获取导弹轨迹数据
        meta_tasks = collection_result.get("meta_tasks", {}).get("meta_tasks", {})
        
        # 为每个真实任务添加位置信息
        for idx, row in enhanced_df.iterrows():
            if row.get('IsRealTask', False):
                missile_id = row['MissileID']
                task_start = row['Start']
                task_end = row['End']
                
                # 获取该导弹的轨迹数据
                missile_data = meta_tasks.get(missile_id, {})
                trajectory_data = missile_data.get("trajectory_data", {})
                trajectory_points = trajectory_data.get("trajectory_points", [])
                
                # 提取任务时间范围内的位置信息
                position_data = self._extract_position_data_for_timerange(
                    trajectory_points, task_start, task_end
                )
                
                enhanced_df.at[idx, 'position_data'] = position_data
                enhanced_df.at[idx, 'has_position_data'] = len(position_data) > 0
        
        return enhanced_df
    
    def _enhance_with_satellite_position_data(self, df: pd.DataFrame, collection_result: Dict[str, Any]) -> pd.DataFrame:
        """为真实可见任务添加卫星位置信息"""
        if df.empty:
            return df

        enhanced_df = df.copy()

        # 初始化新列
        enhanced_df['satellite_position_data'] = None
        enhanced_df['has_satellite_position_data'] = False

        # 获取卫星位置数据
        visible_meta_tasks = collection_result.get("visible_meta_tasks", {})
        constellation_data = visible_meta_tasks.get("constellation_visible_task_sets", {})
        
        # 为每个真实可见任务添加位置信息
        for idx, row in enhanced_df.iterrows():
            if row['Type'] == 'visible_meta_task':
                satellite_id = row['SatelliteID']
                task_start = row['Start']
                task_end = row['End']
                
                # 获取该卫星的位置数据
                satellite_data = constellation_data.get(satellite_id, {})
                position_data = satellite_data.get("satellite_position_data", [])
                
                # 提取任务时间范围内的位置信息
                satellite_position_data = self._extract_satellite_position_for_timerange(
                    position_data, task_start, task_end
                )
                
                enhanced_df.at[idx, 'satellite_position_data'] = satellite_position_data
                enhanced_df.at[idx, 'has_satellite_position_data'] = len(satellite_position_data) > 0
        
        return enhanced_df
    
    def _extract_position_data_for_timerange(self, trajectory_points: List[Dict], start_time, end_time) -> List[Dict]:
        """提取指定时间范围内的导弹位置数据"""
        if not trajectory_points:
            return []
            
        position_data = []
        
        # 将时间转换为字符串进行比较（如果需要）
        if isinstance(start_time, datetime):
            start_str = start_time.isoformat()
            end_str = end_time.isoformat()
        else:
            start_str = str(start_time)
            end_str = str(end_time)
        
        for point in trajectory_points:
            point_time = point.get("time", "")
            if start_str <= point_time <= end_str:
                position_data.append({
                    "time": point_time,
                    "latitude": point.get("lat", point.get("latitude", 0.0)),
                    "longitude": point.get("lon", point.get("longitude", 0.0)),
                    "altitude": point.get("alt", point.get("altitude", 0.0)),
                    "velocity": point.get("velocity", {}),
                    "is_midcourse": point.get("is_midcourse", False)
                })
        
        return position_data
    
    def _extract_satellite_position_for_timerange(self, position_data: List[Dict], start_time, end_time) -> List[Dict]:
        """提取指定时间范围内的卫星位置数据"""
        if not position_data:
            return []
            
        satellite_positions = []
        
        # 将时间转换为字符串进行比较（如果需要）
        if isinstance(start_time, datetime):
            start_str = start_time.isoformat()
            end_str = end_time.isoformat()
        else:
            start_str = str(start_time)
            end_str = str(end_time)
        
        for pos in position_data:
            pos_time = pos.get("time", "")
            if start_str <= pos_time <= end_str:
                satellite_positions.append({
                    "time": pos_time,
                    "latitude": pos.get("latitude", 0.0),
                    "longitude": pos.get("longitude", 0.0),
                    "altitude": pos.get("altitude", 0.0),
                    "velocity": pos.get("velocity", {})
                })
        
        return satellite_positions
    
    def _analyze_timeline_conflicts(self, meta_df: pd.DataFrame, visible_df: pd.DataFrame) -> Dict[str, Any]:
        """分析时间轴冲突"""
        # 安全地计算各种任务数量，避免空数组判断错误
        real_meta_tasks = 0
        virtual_meta_tasks = 0
        real_visible_tasks = 0
        virtual_visible_tasks = 0

        try:
            if not meta_df.empty:
                # 使用.get()方法安全地获取列值，避免KeyError
                if 'IsRealTask' in meta_df.columns:
                    real_meta_mask = meta_df['IsRealTask'] == True
                    real_meta_tasks = real_meta_mask.sum() if real_meta_mask.size > 0 else 0

                if 'IsVirtualTask' in meta_df.columns:
                    virtual_meta_mask = meta_df['IsVirtualTask'] == True
                    virtual_meta_tasks = virtual_meta_mask.sum() if virtual_meta_mask.size > 0 else 0
        except Exception as e:
            logger.warning(f"⚠️ 元任务分析失败: {e}")

        try:
            if not visible_df.empty:
                if 'Type' in visible_df.columns:
                    real_visible_mask = visible_df['Type'] == 'visible_meta_task'
                    real_visible_tasks = real_visible_mask.sum() if real_visible_mask.size > 0 else 0

                    virtual_visible_mask = visible_df['Type'] == 'virtual_atomic_task'
                    virtual_visible_tasks = virtual_visible_mask.sum() if virtual_visible_mask.size > 0 else 0
        except Exception as e:
            logger.warning(f"⚠️ 可见任务分析失败: {e}")

        analysis = {
            "total_meta_tasks": len(meta_df),
            "total_visible_tasks": len(visible_df),
            "real_meta_tasks": real_meta_tasks,
            "virtual_meta_tasks": virtual_meta_tasks,
            "real_visible_tasks": real_visible_tasks,
            "virtual_visible_tasks": virtual_visible_tasks,
            "timeline_coverage": "complete",
            "conflict_potential": "analyzed"
        }

        return analysis
    
    def _dataframe_to_dict_list(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """将DataFrame转换为字典列表，处理时间序列化"""
        if df.empty:
            return []
        
        result = []
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            # 处理时间字段的序列化
            for key, value in row_dict.items():
                try:
                    if hasattr(value, 'isoformat'):  # datetime对象
                        row_dict[key] = value.isoformat()
                    elif hasattr(value, 'item'):  # numpy类型
                        row_dict[key] = value.item()
                    elif hasattr(value, '__len__') and len(value) == 0:  # 空数组
                        row_dict[key] = None
                    elif pd.isna(value):  # NaN值
                        row_dict[key] = None
                except (ValueError, TypeError):
                    # 处理无法判断的复杂类型
                    try:
                        row_dict[key] = str(value) if value is not None else None
                    except:
                        row_dict[key] = None
            result.append(row_dict)
        
        return result
