#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间轴转换器工具类
用于将采集的数据转换为包含完整时间轴信息的格式
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)


class TimelineConverter:
    """时间轴转换器"""

    def __init__(self, config_path="config/config.yaml"):
        # 加载配置文件
        self.config = self._load_config(config_path)

        # 获取可视化配置
        viz_config = self.config.get('visualization', {})
        converter_config = viz_config.get('timeline_converter', {})
        gantt_config = viz_config.get('gantt_chart', {})

        # 颜色配置
        self.colors = gantt_config.get('colors', {})

        # 转换器配置
        self.converter_config = converter_config

        # 虚拟任务采样配置
        sampling_config = converter_config.get('virtual_task_sampling', {})
        self.display_interval = sampling_config.get('display_interval', 10)

        # 任务默认值配置
        defaults_config = converter_config.get('task_defaults', {})
        self.default_task_index = defaults_config.get('task_index', 0)
        self.default_coverage_ratio = defaults_config.get('coverage_ratio', 0.0)
        self.default_alpha_real = defaults_config.get('alpha_real', 0.9)
        self.default_alpha_virtual = defaults_config.get('alpha_virtual', 0.6)
        self.default_alpha = defaults_config.get('alpha_default', 0.9)

    def _load_config(self, config_path):
        """加载配置文件"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                logger.warning(f"配置文件不存在: {config_path}，使用默认配置")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return self._get_default_config()

    def _get_default_config(self):
        """获取默认配置"""
        return {
            'visualization': {
                'timeline_converter': {
                    'virtual_task_sampling': {'display_interval': 10},
                    'task_defaults': {
                        'task_index': 0,
                        'coverage_ratio': 0.0,
                        'alpha_real': 0.9,
                        'alpha_virtual': 0.6,
                        'alpha_default': 0.9
                    }
                },
                'gantt_chart': {
                    'colors': {
                        'visible_meta_task': '#4caf50',
                        'virtual_atomic_task': '#ff9800',
                        'real_meta_task': '#4caf50',
                        'virtual_meta_task': '#ff5722',
                        'meta_task_background': '#2196f3'
                    }
                }
            }
        }
    
    def parse_time(self, time_str):
        """解析时间字符串"""
        if isinstance(time_str, datetime):
            return time_str
        
        # 支持多种时间格式
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        
        raise ValueError(f"无法解析时间格式: {time_str}")
    
    def extract_meta_task_timeline(self, meta_tasks_data: Dict) -> List[Dict]:
        """提取元任务时间轴数据"""
        timeline_data = []
        
        # 处理嵌套的数据结构
        meta_tasks = meta_tasks_data.get('meta_tasks', {})
        if not meta_tasks:
            # 如果没有meta_tasks键，直接使用meta_tasks_data
            meta_tasks = meta_tasks_data
        
        for missile_id, missile_data in meta_tasks.items():
            atomic_tasks = missile_data.get('atomic_tasks', [])
            
            # 添加每个元子任务
            for task in atomic_tasks:
                task_type = task.get('task_type', 'atomic_meta_task')
                is_real_task = task_type == 'real_meta_task'
                is_virtual_task = task_type == 'virtual_meta_task'
                
                # 优先使用ISO格式时间，如果没有则使用普通格式
                start_time_str = task.get('start_time_iso') or task.get('start_time')
                end_time_str = task.get('end_time_iso') or task.get('end_time')
                
                timeline_data.append({
                    'type': 'meta_atomic_task',
                    'missile_id': missile_id,
                    'task_id': task.get('task_id', ''),
                    'task_index': task.get('task_index', self.default_task_index),
                    'task_name': f'{missile_id} 元子任务 {task.get("task_index", self.default_task_index)}',
                    'start_time': self.parse_time(start_time_str).isoformat(),
                    'end_time': self.parse_time(end_time_str).isoformat(),
                    'duration_seconds': task.get('duration_seconds', 0),
                    'category': '元子任务',
                    'level': 'atomic',
                    'task_type': task_type,
                    'is_real_task': is_real_task,
                    'is_virtual_task': is_virtual_task,
                    'color': self.colors.get('real_meta_task', '#4caf50') if is_real_task else
                            (self.colors.get('virtual_meta_task', '#ff5722') if is_virtual_task else self.colors.get('meta_task_background', '#2196f3')),
                    'alpha': self.default_alpha_real if is_real_task else (self.default_alpha_virtual if is_virtual_task else self.default_alpha)
                })
        
        return timeline_data
    
    def extract_visible_meta_task_timeline(self, visible_meta_tasks_data: Dict, min_time: datetime, max_time: datetime) -> List[Dict]:
        """提取可见元任务时间轴数据（包含完整填充）"""
        timeline_data = []
        
        constellation_sets = visible_meta_tasks_data.get('constellation_visible_task_sets', {})
        
        # 获取所有唯一的导弹和卫星
        unique_missiles = set()
        unique_satellites = sorted(constellation_sets.keys())
        
        for satellite_data in constellation_sets.values():
            missile_tasks = satellite_data.get('missile_tasks', {})
            unique_missiles.update(missile_tasks.keys())
        
        unique_missiles = sorted(unique_missiles)
        
        # 为每个导弹-卫星组合生成完整时间轴
        for missile_id in unique_missiles:
            for satellite_id in unique_satellites:
                combo_tasks = []
                
                # 获取该组合的现有任务
                if satellite_id in constellation_sets:
                    missile_tasks = constellation_sets[satellite_id].get('missile_tasks', {})
                    if missile_id in missile_tasks:
                        task_data = missile_tasks[missile_id]
                        
                        # 处理可见元任务
                        visible_tasks = task_data.get('visible_tasks', [])
                        for task in visible_tasks:
                            # 优先使用ISO格式时间
                            start_time_str = task.get('start_time_iso') or task.get('start_time')
                            end_time_str = task.get('end_time_iso') or task.get('end_time')
                            
                            combo_tasks.append({
                                'type': 'visible_meta_task',
                                'satellite_id': satellite_id,
                                'missile_id': missile_id,
                                'task_id': task.get('task_id', ''),
                                'task_index': task.get('task_index', self.default_task_index),
                                'task_name': f'{satellite_id} → {missile_id} 可见元任务',
                                'start_time': self.parse_time(start_time_str),
                                'end_time': self.parse_time(end_time_str),
                                'duration_seconds': task.get('duration_seconds', 0),
                                'category': '可见元任务',
                                'level': 'visible',
                                'visibility_info': task.get('visibility_info', {}),
                                'coverage_ratio': task.get('visibility_info', {}).get('coverage_ratio', 1.0),
                                'color': self.colors.get('visible_meta_task', '#4caf50'),
                                'alpha': self.default_alpha_real
                            })
                        
                        # 处理虚拟原子任务（采样显示）
                        virtual_tasks = task_data.get('virtual_tasks', [])
                        for i, task in enumerate(virtual_tasks):
                            if i % self.display_interval == 0:  # 采样显示，避免过于密集
                                # 优先使用ISO格式时间
                                start_time_str = task.get('start_time_iso') or task.get('start_time')
                                end_time_str = task.get('end_time_iso') or task.get('end_time')
                                
                                combo_tasks.append({
                                    'type': 'virtual_atomic_task',
                                    'satellite_id': satellite_id,
                                    'missile_id': missile_id,
                                    'task_id': task.get('task_id', ''),
                                    'task_index': task.get('task_index', self.default_task_index),
                                    'task_name': f'{satellite_id} → {missile_id} 虚拟原子任务',
                                    'start_time': self.parse_time(start_time_str),
                                    'end_time': self.parse_time(end_time_str),
                                    'duration_seconds': task.get('duration_seconds', 0),
                                    'category': '虚拟原子任务',
                                    'level': 'virtual',
                                    'visibility_info': task.get('visibility_info', {}),
                                    'color': self.colors.get('virtual_atomic_task', '#ff9800'),
                                    'alpha': self.default_alpha_virtual
                                })
                
                # 生成完整时间轴填充
                complete_timeline = self._generate_complete_timeline(
                    combo_tasks, satellite_id, missile_id, min_time, max_time
                )
                timeline_data.extend(complete_timeline)
        
        return timeline_data
    
    def _generate_complete_timeline(self, combo_tasks: List[Dict], satellite_id: str, missile_id: str, 
                                   min_time: datetime, max_time: datetime) -> List[Dict]:
        """为单个导弹-卫星组合生成完整时间轴"""
        complete_tasks = []
        
        if not combo_tasks:
            # 如果没有任何任务，为整个时间范围填充虚拟任务
            virtual_task = {
                'type': 'virtual_atomic_task',
                'satellite_id': satellite_id,
                'missile_id': missile_id,
                'task_id': f'virtual_{satellite_id}_{missile_id}_full',
                'task_index': self.default_task_index,
                'task_name': f'{satellite_id} → {missile_id} 虚拟原子任务',
                'start_time': min_time,
                'end_time': max_time,
                'duration_seconds': (max_time - min_time).total_seconds(),
                'category': '虚拟原子任务',
                'level': 'virtual',
                'visibility_info': {},
                'coverage_ratio': self.default_coverage_ratio,
                'color': self.colors.get('virtual_atomic_task', '#ff9800'),
                'alpha': self.default_alpha_virtual
            }
            complete_tasks.append(virtual_task)
        else:
            # 先添加所有原始任务
            for task in combo_tasks:
                complete_tasks.append(task)
            
            # 按时间排序
            combo_tasks_sorted = sorted(combo_tasks, key=lambda x: x['start_time'])
            
            # 检查开始前的空隙
            if combo_tasks_sorted:
                first_task_start = combo_tasks_sorted[0]['start_time']
                if min_time < first_task_start:
                    virtual_task = {
                        'type': 'virtual_atomic_task',
                        'satellite_id': satellite_id,
                        'missile_id': missile_id,
                        'task_id': f'virtual_{satellite_id}_{missile_id}_start',
                        'task_index': self.default_task_index,
                        'task_name': f'{satellite_id} → {missile_id} 虚拟原子任务',
                        'start_time': min_time,
                        'end_time': first_task_start,
                        'duration_seconds': (first_task_start - min_time).total_seconds(),
                        'category': '虚拟原子任务',
                        'level': 'virtual',
                        'visibility_info': {},
                        'coverage_ratio': self.default_coverage_ratio,
                        'color': self.colors.get('virtual_atomic_task', '#ff9800'),
                        'alpha': self.default_alpha_virtual
                    }
                    complete_tasks.append(virtual_task)
                
                # 检查任务间的空隙
                for i in range(len(combo_tasks_sorted) - 1):
                    current_task_end = combo_tasks_sorted[i]['end_time']
                    next_task_start = combo_tasks_sorted[i + 1]['start_time']
                    
                    if current_task_end < next_task_start:
                        virtual_task = {
                            'type': 'virtual_atomic_task',
                            'satellite_id': satellite_id,
                            'missile_id': missile_id,
                            'task_id': f'virtual_{satellite_id}_{missile_id}_gap_{i}',
                            'task_index': self.default_task_index,
                            'task_name': f'{satellite_id} → {missile_id} 虚拟原子任务',
                            'start_time': current_task_end,
                            'end_time': next_task_start,
                            'duration_seconds': (next_task_start - current_task_end).total_seconds(),
                            'category': '虚拟原子任务',
                            'level': 'virtual',
                            'visibility_info': {},
                            'coverage_ratio': self.default_coverage_ratio,
                            'color': self.colors.get('virtual_atomic_task', '#ff9800'),
                            'alpha': self.default_alpha_virtual
                        }
                        complete_tasks.append(virtual_task)
                
                # 检查结束后的空隙
                last_task_end = combo_tasks_sorted[-1]['end_time']
                if last_task_end < max_time:
                    virtual_task = {
                        'type': 'virtual_atomic_task',
                        'satellite_id': satellite_id,
                        'missile_id': missile_id,
                        'task_id': f'virtual_{satellite_id}_{missile_id}_end',
                        'task_index': self.default_task_index,
                        'task_name': f'{satellite_id} → {missile_id} 虚拟原子任务',
                        'start_time': last_task_end,
                        'end_time': max_time,
                        'duration_seconds': (max_time - last_task_end).total_seconds(),
                        'category': '虚拟原子任务',
                        'level': 'virtual',
                        'visibility_info': {},
                        'coverage_ratio': self.default_coverage_ratio,
                        'color': self.colors.get('virtual_atomic_task', '#ff9800'),
                        'alpha': self.default_alpha_virtual
                    }
                    complete_tasks.append(virtual_task)
        
        # 转换时间为ISO格式
        for task in complete_tasks:
            if isinstance(task['start_time'], datetime):
                task['start_time'] = task['start_time'].isoformat()
            if isinstance(task['end_time'], datetime):
                task['end_time'] = task['end_time'].isoformat()
        
        return complete_tasks

    def convert_collection_data(self, collection_data: Dict) -> Dict:
        """转换单次采集数据"""
        try:
            # 提取基本信息
            collection_time_str = collection_data.get('collection_time', '')
            meta_tasks = collection_data.get('meta_tasks', {})
            visible_meta_tasks = collection_data.get('visible_meta_tasks', {})

            # 确定时间范围
            planning_period = meta_tasks.get('planning_period', {})

            # 如果没有planning_period，从第一个导弹的planning_cycle中获取
            if not planning_period or not planning_period.get('start_time'):
                meta_tasks_inner = meta_tasks.get('meta_tasks', {})
                if meta_tasks_inner:
                    first_missile = next(iter(meta_tasks_inner.values()))
                    planning_cycle = first_missile.get('planning_cycle', {})
                    planning_period = {
                        'start_time': planning_cycle.get('start_time'),
                        'end_time': planning_cycle.get('end_time')
                    }

            min_time = self.parse_time(planning_period.get('start_time'))
            max_time = self.parse_time(planning_period.get('end_time'))

            # 提取元任务时间轴
            meta_task_timeline = self.extract_meta_task_timeline(meta_tasks)

            # 提取可见元任务时间轴
            visible_meta_task_timeline = self.extract_visible_meta_task_timeline(
                visible_meta_tasks, min_time, max_time
            )

            # 构建转换后的数据
            converted_data = {
                'collection_info': {
                    'collection_time': collection_time_str,
                    'data_type': 'timeline_converted_data',
                    'conversion_time': datetime.now().isoformat()
                },
                'planning_period': {
                    'start_time': min_time.isoformat(),
                    'end_time': max_time.isoformat(),
                    'duration_seconds': (max_time - min_time).total_seconds(),
                    'duration_hours': (max_time - min_time).total_seconds() / 3600
                },
                'meta_task_timeline': {
                    'tasks': meta_task_timeline,
                    'total_count': len(meta_task_timeline),
                    'real_task_count': len([t for t in meta_task_timeline if t.get('is_real_task', False)]),
                    'virtual_task_count': len([t for t in meta_task_timeline if t.get('is_virtual_task', False)])
                },
                'visible_meta_task_timeline': {
                    'tasks': visible_meta_task_timeline,
                    'total_count': len(visible_meta_task_timeline),
                    'visible_task_count': len([t for t in visible_meta_task_timeline if t['type'] == 'visible_meta_task']),
                    'virtual_atomic_task_count': len([t for t in visible_meta_task_timeline if t['type'] == 'virtual_atomic_task'])
                },
                'statistics': {
                    'missile_count': len(set([t['missile_id'] for t in meta_task_timeline])),
                    'satellite_count': len(set([t['satellite_id'] for t in visible_meta_task_timeline])) if visible_meta_task_timeline else 0,
                    'visibility_ratio': len([t for t in visible_meta_task_timeline if t['type'] == 'visible_meta_task']) /
                                      len(visible_meta_task_timeline) if visible_meta_task_timeline else 0
                },
                'original_data': collection_data  # 保留原始数据以备参考
            }

            logger.info(f"✅ 时间轴数据转换完成")
            logger.info(f"   元任务: {len(meta_task_timeline)} 个")
            logger.info(f"   可见任务: {len([t for t in visible_meta_task_timeline if t['type'] == 'visible_meta_task'])} 个")
            logger.info(f"   虚拟原子任务: {len([t for t in visible_meta_task_timeline if t['type'] == 'virtual_atomic_task'])} 个")

            return converted_data

        except Exception as e:
            logger.error(f"❌ 时间轴数据转换失败: {e}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return {}
