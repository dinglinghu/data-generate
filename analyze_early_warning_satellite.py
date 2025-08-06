#!/usr/bin/env python3
"""
预警卫星载荷配置分析工具
专门分析预警卫星的星空观测载荷配置
"""

import logging
import math
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EarlyWarningSatelliteAnalyzer:
    """预警卫星载荷配置分析器"""
    
    def __init__(self):
        # 当前配置
        self.current_config = {
            "inner_cone_half_angle": 66.0,
            "outer_cone_half_angle": 90.0,
            "clockwise_angle_min": 300.0,
            "clockwise_angle_max": 60.0,
            "pointing": {
                "azimuth": 0.0,
                "elevation": 0.0
            }
        }
    
    def analyze_early_warning_requirements(self) -> Dict[str, Any]:
        """分析预警卫星载荷需求"""
        logger.info("🛰️ 分析预警卫星载荷配置需求...")
        
        analysis = {
            "mission_type": "预警卫星 - 星空背景观测",
            "current_config": self.current_config,
            "configuration_analysis": {},
            "optimization_recommendations": []
        }
        
        # 分析各个参数
        analysis["configuration_analysis"] = {
            "cone_angles": self._analyze_cone_angles(),
            "clock_angles": self._analyze_clock_angles(),
            "pointing_direction": self._analyze_pointing_direction(),
            "space_observation_suitability": self._analyze_space_observation_suitability()
        }
        
        # 生成优化建议
        analysis["optimization_recommendations"] = self._generate_early_warning_recommendations()
        
        return analysis
    
    def _analyze_cone_angles(self) -> Dict[str, Any]:
        """分析圆锥角配置"""
        inner = self.current_config["inner_cone_half_angle"]
        outer = self.current_config["outer_cone_half_angle"]
        
        analysis = {
            "inner_cone_half_angle": inner,
            "outer_cone_half_angle": outer,
            "effective_fov": outer - inner,
            "total_cone_angle": outer * 2,
            "assessment": "",
            "issues": []
        }
        
        effective_fov = outer - inner
        
        # 预警卫星视场分析
        if outer >= 90.0:
            analysis["issues"].append("外锥角90度意味着观测到地平线，可能包含地球边缘")
        
        if inner >= 60.0:
            analysis["issues"].append("内锥角过大，可能错过近距离空间目标")
        
        if effective_fov < 10.0:
            analysis["assessment"] = "视场过窄，不适合预警卫星大范围搜索"
        elif effective_fov > 40.0:
            analysis["assessment"] = "视场很宽，适合大范围空间监视"
        else:
            analysis["assessment"] = "视场适中，平衡搜索范围与精度"
        
        return analysis
    
    def _analyze_clock_angles(self) -> Dict[str, Any]:
        """分析时钟角配置"""
        clock_min = self.current_config["clockwise_angle_min"]
        clock_max = self.current_config["clockwise_angle_max"]
        
        analysis = {
            "clockwise_angle_min": clock_min,
            "clockwise_angle_max": clock_max,
            "scan_range_deg": 0.0,
            "mechanical_limits": "",
            "coverage_assessment": ""
        }
        
        # 计算扫描范围（跨越0度的情况）
        if clock_min == 300.0 and clock_max == 60.0:
            scan_range = 120.0  # 左右各60度
            analysis["scan_range_deg"] = scan_range
            analysis["mechanical_limits"] = "左右各60度，符合机械限位要求"
            analysis["coverage_assessment"] = "✅ 完美符合预警卫星左右60度扫描需求"
        else:
            if clock_max > clock_min:
                scan_range = clock_max - clock_min
            else:
                scan_range = (360.0 - clock_min) + clock_max
            
            analysis["scan_range_deg"] = scan_range
            analysis["mechanical_limits"] = f"总扫描范围{scan_range}度"
            
            if scan_range != 120.0:
                analysis["coverage_assessment"] = f"⚠️ 扫描范围{scan_range}度，不符合左右60度要求"
        
        return analysis
    
    def _analyze_pointing_direction(self) -> Dict[str, Any]:
        """分析指向方向"""
        azimuth = self.current_config["pointing"]["azimuth"]
        elevation = self.current_config["pointing"]["elevation"]
        
        analysis = {
            "azimuth": azimuth,
            "elevation": elevation,
            "pointing_description": "",
            "space_observation_suitability": "",
            "recommendations": []
        }
        
        # 解释指向方向
        if elevation == 0.0:
            pointing_desc = "水平指向"
            space_suitability = "⚠️ 水平指向主要观测地球边缘，不适合深空预警"
            analysis["recommendations"].append("建议调整为向上指向以观测深空")
        elif elevation > 0.0:
            pointing_desc = f"向上{elevation}度"
            if elevation >= 45.0:
                space_suitability = "✅ 向上指向，适合观测深空和星空背景"
            else:
                space_suitability = "⚠️ 向上角度较小，可能受地球边缘影响"
        else:
            pointing_desc = f"向下{abs(elevation)}度"
            space_suitability = "❌ 向下指向，完全不适合预警卫星星空观测"
            analysis["recommendations"].append("必须改为向上指向")
        
        analysis["pointing_description"] = pointing_desc
        analysis["space_observation_suitability"] = space_suitability
        
        return analysis
    
    def _analyze_space_observation_suitability(self) -> Dict[str, Any]:
        """分析空间观测适用性"""
        config = self.current_config
        
        suitability = {
            "overall_score": 0,
            "strengths": [],
            "weaknesses": [],
            "critical_issues": []
        }
        
        # 评分系统（总分100）
        score = 0
        
        # 时钟角评分（30分）
        if config["clockwise_angle_min"] == 300.0 and config["clockwise_angle_max"] == 60.0:
            score += 30
            suitability["strengths"].append("时钟角配置完美，实现左右60度扫描")
        else:
            suitability["weaknesses"].append("时钟角配置不符合机械限位要求")
        
        # 圆锥角评分（40分）
        effective_fov = config["outer_cone_half_angle"] - config["inner_cone_half_angle"]
        if effective_fov >= 20.0:
            score += 30
            suitability["strengths"].append(f"有效视场{effective_fov}度，适合大范围搜索")
        else:
            score += 15
            suitability["weaknesses"].append("视场相对较窄")
        
        if config["outer_cone_half_angle"] <= 85.0:
            score += 10
            suitability["strengths"].append("外锥角避免了地球边缘干扰")
        else:
            suitability["weaknesses"].append("外锥角可能包含地球边缘")
        
        # 指向方向评分（30分）
        elevation = config["pointing"]["elevation"]
        if elevation >= 45.0:
            score += 30
            suitability["strengths"].append("指向角度适合深空观测")
        elif elevation > 0.0:
            score += 15
            suitability["weaknesses"].append("指向角度偏低，可能受地球影响")
        else:
            suitability["critical_issues"].append("指向方向不适合空间观测")
        
        suitability["overall_score"] = score
        
        return suitability
    
    def _generate_early_warning_recommendations(self) -> List[Dict[str, Any]]:
        """生成预警卫星优化建议"""
        recommendations = []
        
        # 建议1: 优化指向方向
        recommendations.append({
            "priority": "关键",
            "parameter": "pointing.elevation",
            "current_value": self.current_config["pointing"]["elevation"],
            "recommended_value": 60.0,
            "reason": "预警卫星需要向上指向观测深空，避免地球边缘干扰",
            "impact": "大幅提升空间目标探测能力"
        })
        
        # 建议2: 优化外锥角
        recommendations.append({
            "priority": "重要",
            "parameter": "outer_cone_half_angle",
            "current_value": self.current_config["outer_cone_half_angle"],
            "recommended_value": 80.0,
            "reason": "减小外锥角避免观测到地球边缘，专注深空区域",
            "impact": "减少地球背景干扰，提高目标识别精度"
        })
        
        # 建议3: 优化内锥角
        recommendations.append({
            "priority": "中等",
            "parameter": "inner_cone_half_angle",
            "current_value": self.current_config["inner_cone_half_angle"],
            "recommended_value": 45.0,
            "reason": "适当减小内锥角，扩大近距离空间目标探测范围",
            "impact": "提高对近地空间目标的探测能力"
        })
        
        # 建议4: 保持时钟角配置
        recommendations.append({
            "priority": "维持",
            "parameter": "clockwise_angles",
            "current_value": "300.0° - 60.0°",
            "recommended_value": "保持不变",
            "reason": "当前配置完美实现左右60度机械限位要求",
            "impact": "满足机械约束，实现最大扫描范围"
        })
        
        return recommendations
    
    def generate_optimized_config(self) -> Dict[str, Any]:
        """生成优化后的预警卫星配置"""
        optimized_config = {
            "mission_type": "预警卫星 - 深空观测优化配置",
            "description": "专门针对预警卫星星空背景观测的优化配置",
            "parameters": {
                "inner_cone_half_angle": 45.0,   # 减小内锥角，扩大近距离探测
                "outer_cone_half_angle": 80.0,   # 减小外锥角，避免地球边缘
                "clockwise_angle_min": 300.0,    # 保持左右60度扫描
                "clockwise_angle_max": 60.0,     # 保持左右60度扫描
                "pointing": {
                    "azimuth": 0.0,              # 沿轨道方向
                    "elevation": 60.0            # 向上60度，深空观测
                }
            },
            "technical_specifications": {
                "effective_fov": "35度 (80° - 45°)",
                "scan_range": "120度 (左右各60度)",
                "observation_direction": "向上60度深空方向",
                "earth_avoidance": "避免地球边缘干扰",
                "target_types": ["弹道导弹", "空间碎片", "卫星", "深空目标"]
            }
        }
        
        return optimized_config
    
    def print_analysis_report(self, analysis: Dict[str, Any]):
        """打印分析报告"""
        print("\n" + "="*70)
        print("🛰️ 预警卫星载荷配置分析报告")
        print("="*70)
        
        print(f"\n📋 任务类型: {analysis['mission_type']}")
        
        # 当前配置
        current = analysis["current_config"]
        print(f"\n📊 当前配置:")
        print(f"   内锥半角: {current['inner_cone_half_angle']}°")
        print(f"   外锥半角: {current['outer_cone_half_angle']}°")
        print(f"   时钟角范围: {current['clockwise_angle_min']}° - {current['clockwise_angle_max']}°")
        print(f"   指向方位角: {current['pointing']['azimuth']}°")
        print(f"   指向俯仰角: {current['pointing']['elevation']}°")
        
        # 配置分析
        config_analysis = analysis["configuration_analysis"]
        
        print(f"\n🔍 配置分析:")
        
        # 圆锥角分析
        cone = config_analysis["cone_angles"]
        print(f"   圆锥视场:")
        print(f"     有效视场: {cone['effective_fov']}°")
        print(f"     评估: {cone['assessment']}")
        if cone['issues']:
            for issue in cone['issues']:
                print(f"     ⚠️ {issue}")
        
        # 时钟角分析
        clock = config_analysis["clock_angles"]
        print(f"   扫描范围:")
        print(f"     扫描角度: {clock['scan_range_deg']}°")
        print(f"     机械限位: {clock['mechanical_limits']}")
        print(f"     评估: {clock['coverage_assessment']}")
        
        # 指向方向分析
        pointing = config_analysis["pointing_direction"]
        print(f"   指向方向:")
        print(f"     描述: {pointing['pointing_description']}")
        print(f"     空间观测适用性: {pointing['space_observation_suitability']}")
        
        # 适用性评分
        suitability = config_analysis["space_observation_suitability"]
        print(f"\n📈 空间观测适用性评分: {suitability['overall_score']}/100")
        
        if suitability['strengths']:
            print(f"   ✅ 优势:")
            for strength in suitability['strengths']:
                print(f"     • {strength}")
        
        if suitability['weaknesses']:
            print(f"   ⚠️ 不足:")
            for weakness in suitability['weaknesses']:
                print(f"     • {weakness}")
        
        if suitability['critical_issues']:
            print(f"   ❌ 关键问题:")
            for issue in suitability['critical_issues']:
                print(f"     • {issue}")
        
        # 优化建议
        recommendations = analysis["optimization_recommendations"]
        print(f"\n💡 优化建议:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. [{rec['priority']}] {rec['parameter']}")
            print(f"      当前值: {rec['current_value']}")
            print(f"      建议值: {rec['recommended_value']}")
            print(f"      原因: {rec['reason']}")
        
        print("="*70)

def main():
    """主函数"""
    analyzer = EarlyWarningSatelliteAnalyzer()
    
    # 分析当前配置
    analysis = analyzer.analyze_early_warning_requirements()
    analyzer.print_analysis_report(analysis)
    
    # 生成优化配置
    optimized_config = analyzer.generate_optimized_config()
    
    print(f"\n🚀 预警卫星优化配置方案:")
    print("="*70)
    print(f"任务类型: {optimized_config['mission_type']}")
    print(f"描述: {optimized_config['description']}")
    
    print(f"\n📋 优化参数:")
    params = optimized_config['parameters']
    print(f"  inner_cone_half_angle: {params['inner_cone_half_angle']}  # 内锥半角")
    print(f"  outer_cone_half_angle: {params['outer_cone_half_angle']}  # 外锥半角")
    print(f"  clockwise_angle_min: {params['clockwise_angle_min']}    # 最小时钟角")
    print(f"  clockwise_angle_max: {params['clockwise_angle_max']}     # 最大时钟角")
    print(f"  pointing:")
    print(f"    azimuth: {params['pointing']['azimuth']}              # 指向方位角")
    print(f"    elevation: {params['pointing']['elevation']}           # 指向俯仰角")
    
    print(f"\n📊 技术规格:")
    specs = optimized_config['technical_specifications']
    for key, value in specs.items():
        if key == 'target_types':
            print(f"  {key}: {', '.join(value)}")
        else:
            print(f"  {key}: {value}")
    
    print("="*70)

if __name__ == "__main__":
    main()
