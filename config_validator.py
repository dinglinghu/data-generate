#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件验证器
检查配置文件中的参数是否被代码实际使用，识别未使用的配置项
"""

import yaml
import os
import re
from pathlib import Path
from typing import Dict, Set, List, Any

class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, config_path="config/config.yaml"):
        self.config_path = config_path
        self.config = self._load_config()
        self.used_configs = set()
        self.unused_configs = set()
        
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return {}
    
    def _extract_config_keys(self, config_dict: Dict[str, Any], prefix: str = "") -> Set[str]:
        """递归提取配置键"""
        keys = set()
        for key, value in config_dict.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            
            if isinstance(value, dict):
                keys.update(self._extract_config_keys(value, full_key))
        
        return keys
    
    def _scan_code_files(self, directory: str = "src") -> Set[str]:
        """扫描代码文件中使用的配置"""
        used_configs = set()
        
        # 扫描Python文件
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    used_configs.update(self._scan_file(file_path))
        
        # 扫描主目录的Python文件
        for file in os.listdir('.'):
            if file.endswith('.py'):
                used_configs.update(self._scan_file(file))
        
        return used_configs
    
    def _scan_file(self, file_path: str) -> Set[str]:
        """扫描单个文件中使用的配置"""
        used_configs = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找配置访问模式
            patterns = [
                r'config\.get\(["\']([^"\']+)["\']',  # config.get('key')
                r'\.get\(["\']([^"\']+)["\']',        # .get('key')
                r'config\[["\']([^"\']+)["\']\]',     # config['key']
                r'\[["\']([^"\']+)["\']\]',           # ['key']
                r'get_(\w+)_config',                  # get_xxx_config()
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    used_configs.add(match)
            
            # 特殊处理一些已知的配置访问方式
            if 'constellation_config' in content:
                used_configs.update(['constellation', 'constellation.type', 'constellation.planes', 
                                   'constellation.satellites_per_plane', 'constellation.total_satellites'])
            
            if 'payload_config' in content:
                used_configs.update(['payload', 'payload.type', 'payload.mounting'])
            
            if 'missile_config' in content:
                used_configs.update(['missile', 'missile.max_concurrent_missiles'])
            
            if 'stk_config' in content:
                used_configs.update(['stk', 'stk.object_types', 'stk.wait_times'])
            
            if 'meta_task_config' in content:
                used_configs.update(['meta_task_management', 'meta_task_management.atomic_task_interval'])
            
        except Exception as e:
            print(f"⚠️ 扫描文件失败 {file_path}: {e}")
        
        return used_configs
    
    def validate(self) -> Dict[str, Any]:
        """验证配置使用情况"""
        print("🔍 开始配置验证...")
        
        # 提取所有配置键
        all_config_keys = self._extract_config_keys(self.config)
        print(f"📊 配置文件中共有 {len(all_config_keys)} 个配置项")
        
        # 扫描代码中使用的配置
        used_configs = self._scan_code_files()
        print(f"📊 代码中使用了 {len(used_configs)} 个配置项")
        
        # 找出未使用的配置
        unused_configs = all_config_keys - used_configs
        
        # 过滤掉一些可能的误报
        filtered_unused = set()
        for config in unused_configs:
            # 跳过一些已知的配置模式
            if not any(pattern in config for pattern in [
                'colors.',  # 颜色配置可能通过字典访问
                'satellite_colors',  # 卫星颜色数组
                'figure_size',  # 图表配置
                'height_ratios',
                'dpi',
                'time_axis.',
                'task_bars.',
                'y_axis.',
                'text.',
                'grid.',
                'timeline_converter.',
                'gantt_chart.'
            ]):
                filtered_unused.add(config)
        
        return {
            'total_configs': len(all_config_keys),
            'used_configs': len(used_configs),
            'unused_configs': len(filtered_unused),
            'all_configs': sorted(all_config_keys),
            'used_config_list': sorted(used_configs),
            'unused_config_list': sorted(filtered_unused),
            'usage_rate': (len(used_configs) / len(all_config_keys)) * 100 if all_config_keys else 0
        }
    
    def print_report(self):
        """打印验证报告"""
        result = self.validate()
        
        print("\n" + "="*80)
        print("📋 配置文件验证报告")
        print("="*80)
        
        print(f"📊 总配置项数: {result['total_configs']}")
        print(f"✅ 已使用配置: {result['used_configs']}")
        print(f"❌ 未使用配置: {result['unused_configs']}")
        print(f"📈 使用率: {result['usage_rate']:.1f}%")
        
        if result['unused_config_list']:
            print(f"\n⚠️ 未使用的配置项 ({len(result['unused_config_list'])}个):")
            for config in result['unused_config_list']:
                print(f"   - {config}")
        
        print(f"\n✅ 已使用的配置项 ({len(result['used_config_list'])}个):")
        for config in result['used_config_list'][:20]:  # 只显示前20个
            print(f"   - {config}")
        if len(result['used_config_list']) > 20:
            print(f"   ... 还有 {len(result['used_config_list']) - 20} 个")
        
        print("="*80)

def main():
    """主函数"""
    validator = ConfigValidator()
    validator.print_report()

if __name__ == "__main__":
    main()
