#!/usr/bin/env python3
"""
载荷指向配置分析工具
分析和优化载荷指向参数，实现左右60度机动范围
"""

import logging
import math
from typing import Dict, Any, Tuple, List
from src.utils.config_manager import get_config_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PayloadPointingAnalyzer:
    """载荷指向配置分析器"""
    
    def __init__(self):
        self.config_manager = get_config_manager()
        self.current_config = self.config_manager.get_payload_config()
    
    def analyze_current_config(self) -> Dict[str, Any]:
        """分析当前载荷配置"""
        logger.info("🔍 分析当前载荷指向配置...")
        
        analysis = {
            "current_config": self.current_config,
            "analysis_results": {},
            "recommendations": []
        }
        
        # 分析指向参数
        pointing = self.current_config.get("pointing", {})
        azimuth = pointing.get("azimuth", 0.0)
        elevation = pointing.get("elevation", 90.0)
        
        # 分析时钟角范围
        clock_min = self.current_config.get("clockwise_angle_min", 0.0)
        clock_max = self.current_config.get("clockwise_angle_max", 360.0)
        
        # 分析锥角
        inner_cone = self.current_config.get("inner_cone_half_angle", 45.0)
        outer_cone = self.current_config.get("outer_cone_half_angle", 75.0)
        
        analysis["analysis_results"] = {
            "pointing_direction": self._analyze_pointing_direction(azimuth, elevation),
            "clock_angle_range": self._analyze_clock_angle_range(clock_min, clock_max),
            "cone_coverage": self._analyze_cone_coverage(inner_cone, outer_cone),
            "mobility_assessment": self._assess_mobility_capability(azimuth, elevation, clock_min, clock_max)
        }
        
        # 生成建议
        analysis["recommendations"] = self._generate_recommendations(analysis["analysis_results"])
        
        return analysis
    
    def _analyze_pointing_direction(self, azimuth: float, elevation: float) -> Dict[str, Any]:
        """分析指向方向"""
        direction_info = {
            "azimuth_deg": azimuth,
            "elevation_deg": elevation,
            "direction_description": "",
            "coordinate_system": "STK Body Fixed"
        }
        
        # 解释方位角
        if azimuth == 0.0:
            az_desc = "正北方向"
        elif azimuth == 90.0:
            az_desc = "正东方向"
        elif azimuth == 180.0:
            az_desc = "正南方向"
        elif azimuth == 270.0:
            az_desc = "正西方向"
        else:
            az_desc = f"{azimuth}度方位"
        
        # 解释俯仰角
        if elevation == 90.0:
            el_desc = "垂直向上"
        elif elevation == 0.0:
            el_desc = "水平方向"
        elif elevation == -90.0:
            el_desc = "垂直向下（天底）"
        elif elevation > 0:
            el_desc = f"向上{elevation}度"
        else:
            el_desc = f"向下{abs(elevation)}度"
        
        direction_info["direction_description"] = f"{az_desc}, {el_desc}"
        
        return direction_info
    
    def _analyze_clock_angle_range(self, clock_min: float, clock_max: float) -> Dict[str, Any]:
        """分析时钟角范围"""
        range_info = {
            "min_angle": clock_min,
            "max_angle": clock_max,
            "total_range": 0.0,
            "coverage_type": "",
            "left_right_symmetric": False
        }
        
        # 计算角度范围
        if clock_max > clock_min:
            total_range = clock_max - clock_min
        else:
            # 跨越0度的情况
            total_range = (360.0 - clock_min) + clock_max
        
        range_info["total_range"] = total_range
        
        # 判断覆盖类型
        if total_range >= 350.0:
            range_info["coverage_type"] = "全方位覆盖"
        elif total_range >= 180.0:
            range_info["coverage_type"] = "半球覆盖"
        elif total_range >= 120.0:
            range_info["coverage_type"] = "扇形覆盖"
        else:
            range_info["coverage_type"] = "窄角覆盖"
        
        # 检查是否为左右对称
        if clock_min == 300.0 and clock_max == 60.0:
            range_info["left_right_symmetric"] = True
            range_info["coverage_type"] = "左右60度对称扫描"
        
        return range_info
    
    def _analyze_cone_coverage(self, inner_cone: float, outer_cone: float) -> Dict[str, Any]:
        """分析锥形视场覆盖"""
        cone_info = {
            "inner_half_angle": inner_cone,
            "outer_half_angle": outer_cone,
            "effective_fov": outer_cone - inner_cone,
            "coverage_assessment": ""
        }
        
        effective_fov = outer_cone - inner_cone
        
        if effective_fov > 30.0:
            cone_info["coverage_assessment"] = "宽视场，适合大范围搜索"
        elif effective_fov > 15.0:
            cone_info["coverage_assessment"] = "中等视场，平衡搜索与精度"
        else:
            cone_info["coverage_assessment"] = "窄视场，适合精确跟踪"
        
        return cone_info
    
    def _assess_mobility_capability(self, azimuth: float, elevation: float, 
                                  clock_min: float, clock_max: float) -> Dict[str, Any]:
        """评估机动能力"""
        mobility = {
            "current_capability": "",
            "left_right_range": 0.0,
            "suitable_for_requirement": False,
            "issues": []
        }
        
        # 计算左右扫描范围
        if clock_min == 300.0 and clock_max == 60.0:
            left_right_range = 120.0  # 左右各60度
            mobility["left_right_range"] = left_right_range
            mobility["suitable_for_requirement"] = True
            mobility["current_capability"] = "左右60度对称扫描"
        else:
            if clock_max > clock_min:
                total_range = clock_max - clock_min
            else:
                total_range = (360.0 - clock_min) + clock_max
            
            mobility["left_right_range"] = total_range
            
            if total_range >= 120.0:
                mobility["current_capability"] = f"总扫描范围{total_range}度"
                if total_range > 120.0:
                    mobility["issues"].append("扫描范围过大，可能影响精度")
            else:
                mobility["current_capability"] = f"扫描范围不足：{total_range}度"
                mobility["issues"].append("扫描范围小于要求的120度")
        
        # 检查指向配置
        if elevation == 90.0:
            mobility["issues"].append("垂直向上指向，无法观测地面目标")
        elif elevation == -90.0:
            mobility["current_capability"] += "，天底指向"
        
        return mobility
    
    def _generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成配置建议"""
        recommendations = []
        
        mobility = analysis_results["mobility_assessment"]
        
        # 建议1: 左右60度对称扫描配置
        if not mobility["suitable_for_requirement"]:
            recommendations.append({
                "priority": "高",
                "title": "实现左右60度对称扫描",
                "description": "配置时钟角实现卫星飞行方向左右各60度的扫描范围",
                "config_changes": {
                    "clockwise_angle_min": 300.0,
                    "clockwise_angle_max": 60.0
                },
                "expected_result": "左右各60度，总计120度扫描范围"
            })
        
        # 建议2: 优化指向方向
        pointing = analysis_results["pointing_direction"]
        if pointing["elevation_deg"] == 90.0:
            recommendations.append({
                "priority": "高",
                "title": "调整载荷指向方向",
                "description": "将载荷从垂直向上改为适合地面观测的角度",
                "config_changes": {
                    "pointing": {
                        "azimuth": 0.0,
                        "elevation": 30.0  # 前下方30度
                    }
                },
                "expected_result": "载荷指向前下方，适合地面目标观测"
            })
        
        # 建议3: 视场角优化
        cone = analysis_results["cone_coverage"]
        if cone["effective_fov"] > 40.0:
            recommendations.append({
                "priority": "中",
                "title": "优化视场角配置",
                "description": "调整内外锥角以平衡覆盖范围和探测精度",
                "config_changes": {
                    "inner_cone_half_angle": 45.0,
                    "outer_cone_half_angle": 75.0
                },
                "expected_result": "30度有效视场，平衡搜索范围与精度"
            })
        
        return recommendations
    
    def generate_optimized_configs(self) -> Dict[str, Dict[str, Any]]:
        """生成优化配置方案"""
        logger.info("🎯 生成载荷指向优化配置方案...")
        
        configs = {
            "方案A_前向扫描": {
                "description": "载荷指向飞行方向，左右60度扫描",
                "use_case": "适合前方目标搜索和跟踪",
                "config": {
                    "clockwise_angle_min": 300.0,
                    "clockwise_angle_max": 60.0,
                    "pointing": {
                        "azimuth": 0.0,    # 飞行方向
                        "elevation": 0.0   # 水平指向
                    }
                }
            },
            
            "方案B_前下方扫描": {
                "description": "载荷指向前下方，左右60度扫描",
                "use_case": "适合地面目标观测",
                "config": {
                    "clockwise_angle_min": 300.0,
                    "clockwise_angle_max": 60.0,
                    "pointing": {
                        "azimuth": 0.0,     # 飞行方向
                        "elevation": -30.0  # 前下方30度
                    }
                }
            },
            
            "方案C_天底扫描": {
                "description": "载荷天底指向，左右60度扫描",
                "use_case": "适合正下方区域覆盖",
                "config": {
                    "clockwise_angle_min": 300.0,
                    "clockwise_angle_max": 60.0,
                    "pointing": {
                        "azimuth": 0.0,     # 任意方向（天底指向时方位角影响较小）
                        "elevation": -90.0  # 垂直向下
                    }
                }
            },
            
            "方案D_侧向扫描": {
                "description": "载荷侧向指向，左右60度扫描",
                "use_case": "适合侧方目标观测",
                "config": {
                    "clockwise_angle_min": 300.0,
                    "clockwise_angle_max": 60.0,
                    "pointing": {
                        "azimuth": 90.0,    # 垂直于飞行方向
                        "elevation": -45.0  # 侧下方45度
                    }
                }
            }
        }
        
        return configs
    
    def print_analysis_report(self, analysis: Dict[str, Any]):
        """打印分析报告"""
        print("\n" + "="*60)
        print("🎯 载荷指向配置分析报告")
        print("="*60)
        
        # 当前配置
        current = analysis["current_config"]
        print(f"\n📊 当前配置:")
        print(f"   指向方位角: {current['pointing']['azimuth']}°")
        print(f"   指向俯仰角: {current['pointing']['elevation']}°")
        print(f"   时钟角范围: {current['clockwise_angle_min']}° - {current['clockwise_angle_max']}°")
        print(f"   内锥半角: {current['inner_cone_half_angle']}°")
        print(f"   外锥半角: {current['outer_cone_half_angle']}°")
        
        # 分析结果
        results = analysis["analysis_results"]
        print(f"\n🔍 分析结果:")
        print(f"   指向方向: {results['pointing_direction']['direction_description']}")
        print(f"   扫描范围: {results['clock_angle_range']['coverage_type']}")
        print(f"   总扫描角度: {results['clock_angle_range']['total_range']}°")
        print(f"   视场评估: {results['cone_coverage']['coverage_assessment']}")
        print(f"   机动能力: {results['mobility_assessment']['current_capability']}")
        
        # 问题识别
        issues = results['mobility_assessment']['issues']
        if issues:
            print(f"\n⚠️ 发现问题:")
            for issue in issues:
                print(f"   - {issue}")
        
        # 建议
        recommendations = analysis["recommendations"]
        if recommendations:
            print(f"\n💡 优化建议:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. [{rec['priority']}] {rec['title']}")
                print(f"      {rec['description']}")
        
        print("="*60)

def main():
    """主函数"""
    analyzer = PayloadPointingAnalyzer()
    
    # 分析当前配置
    analysis = analyzer.analyze_current_config()
    analyzer.print_analysis_report(analysis)
    
    # 生成优化方案
    optimized_configs = analyzer.generate_optimized_configs()
    
    print(f"\n🚀 载荷指向优化方案:")
    print("="*60)
    
    for name, config in optimized_configs.items():
        print(f"\n📋 {name}:")
        print(f"   描述: {config['description']}")
        print(f"   适用场景: {config['use_case']}")
        print(f"   配置参数:")
        
        cfg = config['config']
        print(f"     clockwise_angle_min: {cfg['clockwise_angle_min']}")
        print(f"     clockwise_angle_max: {cfg['clockwise_angle_max']}")
        print(f"     pointing:")
        print(f"       azimuth: {cfg['pointing']['azimuth']}")
        print(f"       elevation: {cfg['pointing']['elevation']}")
    
    print("\n" + "="*60)
    print("💡 建议选择方案B（前下方扫描）作为默认配置")
    print("="*60)

if __name__ == "__main__":
    main()
