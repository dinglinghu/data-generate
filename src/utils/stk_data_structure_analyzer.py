#!/usr/bin/env python3
"""
STK数据结构分析器 - 诊断和分析STK DataProvider返回的数据结构

这个工具用于：
1. 分析STK DataProvider的数据结构
2. 诊断数据提取问题
3. 提供正确的数据访问方法
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class STKDataStructureAnalyzer:
    """STK数据结构分析器"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def analyze_dataprovider_result(self, result, description: str = "DataProvider结果") -> Dict[str, Any]:
        """
        分析STK DataProvider返回的结果结构
        
        Args:
            result: STK DataProvider.Exec()的返回结果
            description: 结果描述
            
        Returns:
            分析报告字典
        """
        analysis = {
            "description": description,
            "result_type": str(type(result)),
            "has_datasets": False,
            "datasets_count": 0,
            "datasets_info": [],
            "data_access_methods": [],
            "recommended_method": None,
            "sample_data": {},
            "errors": []
        }
        
        try:
            self.logger.info(f"🔍 分析 {description}")
            self.logger.info(f"   结果类型: {type(result)}")
            
            # 检查是否有DataSets属性
            if hasattr(result, 'DataSets'):
                analysis["has_datasets"] = True
                datasets = result.DataSets
                analysis["datasets_count"] = datasets.Count
                
                self.logger.info(f"   DataSets数量: {datasets.Count}")
                
                # 分析每个数据集
                for i in range(datasets.Count):
                    dataset_info = self._analyze_dataset(datasets.Item(i), i)
                    analysis["datasets_info"].append(dataset_info)
                
                # 尝试不同的数据访问方法
                access_methods = self._test_data_access_methods(result)
                analysis["data_access_methods"] = access_methods
                
                # 推荐最佳方法
                analysis["recommended_method"] = self._recommend_access_method(access_methods)
                
                # 获取样本数据
                analysis["sample_data"] = self._extract_sample_data(result, analysis["recommended_method"])
                
            else:
                self.logger.warning(f"   ⚠️ 结果没有DataSets属性")
                analysis["errors"].append("结果没有DataSets属性")
                
        except Exception as e:
            error_msg = f"分析过程中发生错误: {e}"
            self.logger.error(f"   ❌ {error_msg}")
            analysis["errors"].append(error_msg)
        
        return analysis
    
    def _analyze_dataset(self, dataset, index: int) -> Dict[str, Any]:
        """分析单个数据集"""
        info = {
            "index": index,
            "type": str(type(dataset)),
            "count": 0,
            "name": None,
            "has_name": False,
            "has_getvalues": False,
            "sample_values": None,
            "errors": []
        }
        
        try:
            # 检查数据点数量
            if hasattr(dataset, 'Count'):
                info["count"] = dataset.Count
                self.logger.info(f"     数据集 {index}: 数据点数={dataset.Count}")
            
            # 检查名称
            if hasattr(dataset, 'Name'):
                info["name"] = dataset.Name
                info["has_name"] = True
                self.logger.info(f"     数据集 {index}: 名称={dataset.Name}")
            
            # 检查GetValues方法
            if hasattr(dataset, 'GetValues'):
                info["has_getvalues"] = True
                
                # 尝试获取样本数据
                try:
                    values = dataset.GetValues()
                    if values and len(values) > 0:
                        # 只取前几个值作为样本
                        sample_size = min(5, len(values))
                        info["sample_values"] = [str(values[i]) for i in range(sample_size)]
                        self.logger.info(f"     数据集 {index}: 样本数据={info['sample_values']}")
                    else:
                        self.logger.warning(f"     数据集 {index}: GetValues()返回空数据")
                        
                except Exception as e:
                    error_msg = f"GetValues()调用失败: {e}"
                    info["errors"].append(error_msg)
                    self.logger.warning(f"     数据集 {index}: {error_msg}")
            
        except Exception as e:
            error_msg = f"数据集分析失败: {e}"
            info["errors"].append(error_msg)
            self.logger.error(f"     数据集 {index}: {error_msg}")
        
        return info
    
    def _test_data_access_methods(self, result) -> List[Dict[str, Any]]:
        """测试不同的数据访问方法"""
        methods = []
        
        # 方法1: GetDataSetByName
        method1 = self._test_getdatasetbyname_method(result)
        if method1:
            methods.append(method1)
        
        # 方法2: 索引访问
        method2 = self._test_index_access_method(result)
        if method2:
            methods.append(method2)
        
        # 方法3: 直接GetValues
        method3 = self._test_direct_getvalues_method(result)
        if method3:
            methods.append(method3)
        
        return methods
    
    def _test_getdatasetbyname_method(self, result) -> Optional[Dict[str, Any]]:
        """测试GetDataSetByName方法"""
        method_info = {
            "name": "GetDataSetByName",
            "success": False,
            "available_names": [],
            "sample_data": {},
            "errors": []
        }
        
        try:
            # 常见的数据集名称
            common_names = ["Time", "Lat", "Lon", "Alt", "Latitude", "Longitude", "Altitude", "x", "y", "z"]
            
            for name in common_names:
                try:
                    dataset = result.DataSets.GetDataSetByName(name)
                    values = dataset.GetValues()
                    
                    method_info["available_names"].append(name)
                    method_info["sample_data"][name] = str(values[0]) if values and len(values) > 0 else "空数据"
                    method_info["success"] = True
                    
                    self.logger.info(f"   ✅ GetDataSetByName('{name}') 成功")
                    
                except Exception as e:
                    self.logger.debug(f"   GetDataSetByName('{name}') 失败: {e}")
            
            if not method_info["available_names"]:
                method_info["errors"].append("没有找到任何可用的命名数据集")
                
        except Exception as e:
            error_msg = f"GetDataSetByName方法测试失败: {e}"
            method_info["errors"].append(error_msg)
            self.logger.warning(f"   ⚠️ {error_msg}")
        
        return method_info if method_info["success"] or method_info["errors"] else None
    
    def _test_index_access_method(self, result) -> Optional[Dict[str, Any]]:
        """测试索引访问方法"""
        method_info = {
            "name": "IndexAccess",
            "success": False,
            "datasets_count": 0,
            "sample_data": {},
            "errors": []
        }
        
        try:
            datasets_count = result.DataSets.Count
            method_info["datasets_count"] = datasets_count
            
            for i in range(min(4, datasets_count)):  # 只测试前4个
                try:
                    dataset = result.DataSets.Item(i)
                    values = dataset.GetValues()
                    
                    if values and len(values) > 0:
                        method_info["sample_data"][f"Dataset_{i}"] = str(values[0])
                        method_info["success"] = True
                        self.logger.info(f"   ✅ DataSets.Item({i}) 成功")
                    else:
                        self.logger.warning(f"   ⚠️ DataSets.Item({i}) 返回空数据")
                        
                except Exception as e:
                    error_msg = f"DataSets.Item({i}) 失败: {e}"
                    method_info["errors"].append(error_msg)
                    self.logger.warning(f"   ⚠️ {error_msg}")
            
        except Exception as e:
            error_msg = f"索引访问方法测试失败: {e}"
            method_info["errors"].append(error_msg)
            self.logger.warning(f"   ⚠️ {error_msg}")
        
        return method_info if method_info["success"] or method_info["errors"] else None
    
    def _test_direct_getvalues_method(self, result) -> Optional[Dict[str, Any]]:
        """测试直接GetValues方法"""
        method_info = {
            "name": "DirectGetValues",
            "success": False,
            "sample_data": {},
            "errors": []
        }
        
        try:
            if result.DataSets.Count > 0:
                dataset = result.DataSets.Item(0)
                values = dataset.GetValues()
                
                if values:
                    method_info["sample_data"]["first_dataset"] = {
                        "length": len(values),
                        "type": str(type(values)),
                        "sample": [str(values[i]) for i in range(min(5, len(values)))]
                    }
                    method_info["success"] = True
                    self.logger.info(f"   ✅ 直接GetValues() 成功")
                else:
                    method_info["errors"].append("GetValues()返回空数据")
                    
        except Exception as e:
            error_msg = f"直接GetValues方法测试失败: {e}"
            method_info["errors"].append(error_msg)
            self.logger.warning(f"   ⚠️ {error_msg}")
        
        return method_info if method_info["success"] or method_info["errors"] else None
    
    def _recommend_access_method(self, methods: List[Dict[str, Any]]) -> Optional[str]:
        """推荐最佳的数据访问方法"""
        
        # 优先级：GetDataSetByName > IndexAccess > DirectGetValues
        for method in methods:
            if method["name"] == "GetDataSetByName" and method["success"]:
                return "GetDataSetByName"
        
        for method in methods:
            if method["name"] == "IndexAccess" and method["success"]:
                return "IndexAccess"
        
        for method in methods:
            if method["name"] == "DirectGetValues" and method["success"]:
                return "DirectGetValues"
        
        return None
    
    def _extract_sample_data(self, result, recommended_method: Optional[str]) -> Dict[str, Any]:
        """根据推荐方法提取样本数据"""
        sample_data = {}
        
        if not recommended_method:
            return sample_data
        
        try:
            if recommended_method == "GetDataSetByName":
                # 尝试获取常见的数据
                common_names = ["Time", "Lat", "Lon", "Alt"]
                for name in common_names:
                    try:
                        dataset = result.DataSets.GetDataSetByName(name)
                        values = dataset.GetValues()
                        if values and len(values) > 0:
                            sample_data[name] = str(values[0])
                    except:
                        pass
            
            elif recommended_method == "IndexAccess":
                # 使用索引获取前几个数据集
                for i in range(min(4, result.DataSets.Count)):
                    try:
                        dataset = result.DataSets.Item(i)
                        values = dataset.GetValues()
                        if values and len(values) > 0:
                            sample_data[f"Index_{i}"] = str(values[0])
                    except:
                        pass
            
        except Exception as e:
            self.logger.error(f"提取样本数据失败: {e}")
        
        return sample_data
    
    def print_analysis_report(self, analysis: Dict[str, Any]):
        """打印分析报告"""
        print(f"\n🔍 STK数据结构分析报告: {analysis['description']}")
        print(f"=" * 60)
        
        print(f"📊 基本信息:")
        print(f"   结果类型: {analysis['result_type']}")
        print(f"   有DataSets: {analysis['has_datasets']}")
        print(f"   DataSets数量: {analysis['datasets_count']}")
        
        if analysis['datasets_info']:
            print(f"\n📋 数据集详情:")
            for info in analysis['datasets_info']:
                print(f"   数据集 {info['index']}:")
                print(f"     名称: {info['name'] if info['has_name'] else '无名称'}")
                print(f"     数据点数: {info['count']}")
                print(f"     样本数据: {info['sample_values']}")
                if info['errors']:
                    print(f"     错误: {info['errors']}")
        
        if analysis['data_access_methods']:
            print(f"\n🔧 数据访问方法测试:")
            for method in analysis['data_access_methods']:
                status = "✅ 成功" if method['success'] else "❌ 失败"
                print(f"   {method['name']}: {status}")
                if method.get('available_names'):
                    print(f"     可用名称: {method['available_names']}")
                if method.get('sample_data'):
                    print(f"     样本数据: {method['sample_data']}")
                if method.get('errors'):
                    print(f"     错误: {method['errors']}")
        
        print(f"\n🎯 推荐方法: {analysis['recommended_method'] or '无可用方法'}")
        
        if analysis['sample_data']:
            print(f"\n📄 样本数据:")
            for key, value in analysis['sample_data'].items():
                print(f"   {key}: {value}")
        
        if analysis['errors']:
            print(f"\n❌ 错误:")
            for error in analysis['errors']:
                print(f"   {error}")
        
        print(f"=" * 60)


# 全局分析器实例
_analyzer_instance = None

def get_stk_analyzer() -> STKDataStructureAnalyzer:
    """获取STK数据结构分析器的全局实例"""
    global _analyzer_instance
    
    if _analyzer_instance is None:
        _analyzer_instance = STKDataStructureAnalyzer()
    
    return _analyzer_instance
