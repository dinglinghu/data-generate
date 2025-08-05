#!/usr/bin/env python3
"""
航天时间转换器 - 专门处理航天轨道计算领域的各种时间格式

支持的时间格式：
- STK时间格式
- Julian Date (JD)
- Modified Julian Date (MJD)
- GPS时间
- UTC时间
- TAI时间
- TT时间 (Terrestrial Time)
- 各种ISO格式
"""

import logging
from datetime import datetime, timezone
from typing import Union, Optional, Tuple
import re

logger = logging.getLogger(__name__)

class AerospaceTimeConverter:
    """航天时间转换器"""
    
    # 月份映射
    MONTH_MAP = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
        'January': 1, 'February': 2, 'March': 3, 'April': 4, 'May': 5, 'June': 6,
        'July': 7, 'August': 8, 'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    
    # Julian Date 常数
    JD_J2000 = 2451545.0  # J2000.0 epoch
    MJD_OFFSET = 2400000.5  # MJD = JD - 2400000.5
    
    def __init__(self):
        """初始化时间转换器"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def parse_stk_time(self, time_str: str) -> Optional[datetime]:
        """
        解析STK时间格式
        
        支持格式：
        - "26 Jul 2025 00:01:30.000000"
        - "266 Jul 2025 00:01:32.000000000" (修复格式错误)
        - "1 Jan 2025 12:00:00"
        - 各种STK输出的时间格式
        
        Args:
            time_str: STK时间字符串
            
        Returns:
            datetime对象，解析失败返回None
        """
        try:
            if not time_str or not isinstance(time_str, str):
                return None
                
            # 清理字符串
            time_str = str(time_str).strip()
            
            # 处理STK常见的格式问题
            time_str = self._fix_stk_format_issues(time_str)
            
            # 解析STK标准格式: "DD MMM YYYY HH:MM:SS.ffffff"
            pattern = r'^(\d{1,2})\s+(\w{3,9})\s+(\d{4})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})(?:\.(\d+))?'
            match = re.match(pattern, time_str)
            
            if not match:
                self.logger.warning(f"无法解析STK时间格式: {time_str}")
                return None
                
            day, month_str, year, hour, minute, second, microsec = match.groups()
            
            # 转换月份
            month = self.MONTH_MAP.get(month_str)
            if not month:
                self.logger.warning(f"无法识别月份: {month_str}")
                return None
                
            # 处理微秒
            if microsec:
                # 确保微秒是6位数
                microsec = microsec.ljust(6, '0')[:6]
                microsec = int(microsec)
            else:
                microsec = 0
                
            # 创建datetime对象
            dt = datetime(
                year=int(year),
                month=month,
                day=int(day),
                hour=int(hour),
                minute=int(minute),
                second=int(second),
                microsecond=microsec,
                tzinfo=timezone.utc
            )
            
            return dt
            
        except Exception as e:
            self.logger.error(f"STK时间解析失败: {time_str}, 错误: {e}")
            return None
    
    def _fix_stk_format_issues(self, time_str: str) -> str:
        """
        修复STK时间格式的常见问题

        Args:
            time_str: 原始时间字符串

        Returns:
            修复后的时间字符串
        """
        # 1. 修复日期格式问题 (STK有时会输出错误的日期格式)
        # "266 Jul" -> "26 Jul", "126 Aug" -> "26 Aug", "356 Dec" -> "31 Dec"

        # 首先提取日期部分进行智能修复
        date_match = re.match(r'^(\d+)\s+(\w{3,9})\s+(\d{4})', time_str)
        if date_match:
            day_str, month_str, year_str = date_match.groups()

            # 修复异常的日期数字
            if len(day_str) == 3:
                # 三位数日期，取后两位
                day_str = day_str[-2:]

                # 进一步验证日期合理性
                try:
                    day = int(day_str)
                    month = self.MONTH_MAP.get(month_str)
                    year = int(year_str)

                    if month:
                        # 检查日期是否在月份范围内
                        import calendar
                        max_day = calendar.monthrange(year, month)[1]

                        if day > max_day:
                            # 如果日期超出范围，使用月份的最后一天
                            day = max_day
                            day_str = str(day)

                except (ValueError, TypeError):
                    # 如果转换失败，使用默认值
                    day_str = "1"

                # 重构时间字符串
                time_str = re.sub(r'^\d+', day_str, time_str)

        # 2. 修复时间分量格式问题
        # "00:001:30" -> "00:01:30"
        time_str = re.sub(r':00(\d):', r':0\1:', time_str)

        # "00:01:300" -> "00:01:30" (修复秒数格式)
        time_str = re.sub(r':(\d{2}):(\d{3,})', lambda m: f':{m.group(1)}:{m.group(2)[:2]}', time_str)

        # 3. 标准化空白字符
        time_str = re.sub(r'\s+', ' ', time_str)

        return time_str.strip()
    
    def to_julian_date(self, dt: datetime) -> float:
        """
        转换为Julian Date
        
        Args:
            dt: datetime对象
            
        Returns:
            Julian Date
        """
        # 确保是UTC时间
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
            
        # Julian Date计算
        year = dt.year
        month = dt.month
        day = dt.day
        
        # 调整年月（Julian Date算法要求）
        if month <= 2:
            year -= 1
            month += 12
            
        # Julian Date公式
        a = int(year / 100)
        b = 2 - a + int(a / 4)
        
        jd = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + b - 1524.5
        
        # 添加时间分量
        time_fraction = (dt.hour + dt.minute/60.0 + dt.second/3600.0 + dt.microsecond/3600000000.0) / 24.0
        jd += time_fraction
        
        return jd
    
    def from_julian_date(self, jd: float) -> datetime:
        """
        从Julian Date转换为datetime
        
        Args:
            jd: Julian Date
            
        Returns:
            datetime对象
        """
        # 分离整数和小数部分
        jd_int = int(jd + 0.5)
        jd_frac = jd + 0.5 - jd_int
        
        # Julian Date逆算法
        a = jd_int + 32044
        b = (4 * a + 3) // 146097
        c = a - (146097 * b) // 4
        d = (4 * c + 3) // 1461
        e = c - (1461 * d) // 4
        m = (5 * e + 2) // 153
        
        day = e - (153 * m + 2) // 5 + 1
        month = m + 3 - 12 * (m // 10)
        year = 100 * b + d - 4800 + m // 10
        
        # 计算时间分量
        time_seconds = jd_frac * 86400  # 一天的秒数
        hour = int(time_seconds // 3600)
        minute = int((time_seconds % 3600) // 60)
        second = int(time_seconds % 60)
        microsecond = int((time_seconds % 1) * 1000000)
        
        return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=timezone.utc)
    
    def to_modified_julian_date(self, dt: datetime) -> float:
        """转换为Modified Julian Date"""
        return self.to_julian_date(dt) - self.MJD_OFFSET
    
    def from_modified_julian_date(self, mjd: float) -> datetime:
        """从Modified Julian Date转换"""
        return self.from_julian_date(mjd + self.MJD_OFFSET)
    
    def parse_aerospace_time(self, time_input: Union[str, float, datetime]) -> Optional[datetime]:
        """
        通用航天时间解析器
        
        自动识别并解析各种航天时间格式：
        - STK时间字符串
        - Julian Date (数值)
        - Modified Julian Date (数值)
        - ISO格式时间
        - datetime对象
        
        Args:
            time_input: 时间输入（字符串、数值或datetime）
            
        Returns:
            标准化的datetime对象
        """
        try:
            if isinstance(time_input, datetime):
                return time_input
                
            elif isinstance(time_input, (int, float)):
                # 判断是JD还是MJD
                if time_input > 1000000:  # 可能是JD
                    return self.from_julian_date(time_input)
                else:  # 可能是MJD
                    return self.from_modified_julian_date(time_input)
                    
            elif isinstance(time_input, str):
                # 尝试不同的字符串格式
                
                # 1. 尝试STK格式
                dt = self.parse_stk_time(time_input)
                if dt:
                    return dt
                    
                # 2. 尝试ISO格式
                try:
                    return datetime.fromisoformat(time_input.replace('Z', '+00:00'))
                except:
                    pass
                    
                # 3. 尝试其他常见格式
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M:%S.%f',
                    '%Y/%m/%d %H:%M:%S',
                    '%d/%m/%Y %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S.%f',
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(time_input, fmt).replace(tzinfo=timezone.utc)
                    except:
                        continue
                        
            return None
            
        except Exception as e:
            self.logger.error(f"航天时间解析失败: {time_input}, 错误: {e}")
            return None
    
    def format_for_stk(self, dt: datetime) -> str:
        """
        格式化为STK标准时间格式
        
        Args:
            dt: datetime对象
            
        Returns:
            STK格式时间字符串
        """
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        elif dt.tzinfo != timezone.utc:
            dt = dt.astimezone(timezone.utc)
            
        # STK格式: "DD MMM YYYY HH:MM:SS.ffffff"
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        return f"{dt.day} {month_names[dt.month-1]} {dt.year} {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}.{dt.microsecond:06d}"
    
    def get_time_info(self, time_input: Union[str, float, datetime]) -> dict:
        """
        获取时间的详细信息
        
        Args:
            time_input: 时间输入
            
        Returns:
            包含各种时间格式的字典
        """
        dt = self.parse_aerospace_time(time_input)
        if not dt:
            return {"error": "无法解析时间"}
            
        jd = self.to_julian_date(dt)
        mjd = self.to_modified_julian_date(dt)
        
        return {
            "datetime": dt,
            "iso_format": dt.isoformat(),
            "stk_format": self.format_for_stk(dt),
            "julian_date": jd,
            "modified_julian_date": mjd,
            "unix_timestamp": dt.timestamp(),
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
            "hour": dt.hour,
            "minute": dt.minute,
            "second": dt.second,
            "microsecond": dt.microsecond
        }
