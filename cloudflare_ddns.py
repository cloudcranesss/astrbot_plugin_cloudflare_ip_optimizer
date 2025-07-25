import os
import asyncio
import aiohttp
from astrbot.api import logger
from typing import Dict, Optional

# 默认配置
DEFAULT_CONFIG = {
    "cf_token": "",
    "zone_id": "",
    "main_domain": "",
    "sub_domain": "",
    "record_type": "A",
    "interval": 300,
    "retry_count": 3,
    "result_file": "csft/result.csv",
    "retry_interval": 5
}

class CloudflareDDNSUpdater:
    """Cloudflare DDNS更新器"""
    
    def __init__(self, config: Dict):
        self.config = self._validate_config(config)
        self.cf_token = self.config["cf_token"]
        self.zone_id = self.config["zone_id"]
        self.main_domain = self.config["main_domain"]
        self.sub_domain = self.config["sub_domain"]
        self.record_type = self.config["record_type"]
        self.interval = self.config["interval"]
        self.retry_count = self.config["retry_count"]
        self.result_file = self.config["result_file"]
        self.retry_interval = self.config["retry_interval"]
        self.full_domain = f"{self.sub_domain}.{self.main_domain}" if self.sub_domain else self.main_domain
        
    def _validate_config(self, config: Dict) -> Dict:
        """验证配置参数"""
        # 合并默认配置和用户配置
        merged_config = {**DEFAULT_CONFIG, **config}
        
        # 检查必填字段
        required_fields = ["cf_token", "zone_id", "main_domain", "record_type"]
        for field in required_fields:
            if not merged_config.get(field):
                logger.error(f"缺少必填配置项: {field}")
                raise ValueError(f"缺少必填配置项: {field}")
        
        # 验证记录类型
        valid_record_types = ["A", "AAAA", "CNAME", "MX", "TXT", "SRV", "LOC", "NS", "CERT", "DNSKEY", "DS", "NAPTR", "SMIMEA", "SSHFP", "TLSA", "URI"]
        if merged_config["record_type"] not in valid_record_types:
            logger.error(f"无效的记录类型: {merged_config['record_type']}, 有效值: {', '.join(valid_record_types)}")
            raise ValueError(f"无效的记录类型: {merged_config['record_type']}")
        
        # 验证时间间隔
        if merged_config["interval"] < 60:
            logger.warning("时间间隔过小，可能导致API请求过于频繁")
        
        return merged_config

    async def _get_record_id(self) -> Optional[str]:
        """获取DNS记录ID（异步版本）"""
        url = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records"
        headers = {
            "Authorization": f"Bearer {self.cf_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    for record in data["result"]:
                        if record["name"] == self.full_domain and record["type"] == self.record_type:
                            return record["id"]
                    
                    logger.warning(f"未找到记录: {self.full_domain} ({self.record_type})")
                    return None
        except aiohttp.ClientError as e:
            logger.error(f"获取记录ID失败: {str(e)}")
            return None

    async def _update_dns_record(self, record_id: str, ip: str) -> bool:
        """更新DNS记录（异步版本）"""
        url = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records/{record_id}"
        headers = {
            "Authorization": f"Bearer {self.cf_token}",
            "Content-Type": "application/json"
        }
        data = {
            "type": self.record_type,
            "name": self.full_domain,
            "content": ip,
            "ttl": 1,
            "proxied": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if result["success"]:
                        logger.info(f"成功更新DNS记录: {self.full_domain} -> {ip}")
                        return True
                    else:
                        logger.error(f"更新DNS记录失败: {result['errors']}")
                        return False
        except aiohttp.ClientError as e:
            logger.error(f"更新DNS记录请求失败: {str(e)}")
            return False

    async def _create_dns_record(self, ip: str) -> bool:
        """创建DNS记录（异步版本）"""
        url = f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records"
        headers = {
            "Authorization": f"Bearer {self.cf_token}",
            "Content-Type": "application/json"
        }
        data = {
            "type": self.record_type,
            "name": self.full_domain,
            "content": ip,
            "ttl": 1,
            "proxied": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response.raise_for_status()
                    result = await response.json()
                    
                    if result["success"]:
                        logger.info(f"成功创建DNS记录: {self.full_domain} -> {ip}")
                        return True
                    else:
                        logger.error(f"创建DNS记录失败: {result['errors']}")
                        return False
        except aiohttp.ClientError as e:
            logger.error(f"创建DNS记录请求失败: {str(e)}")
            return False

    def _get_lowest_latency_ip(self) -> Optional[str]:
        """从结果文件中获取延迟最低的IP"""
        try:
            # 获取绝对路径，确保基于脚本所在目录
            script_dir = os.path.dirname(os.path.abspath(__file__))
            result_file_path = os.path.join(script_dir, self.result_file)
            
            if not os.path.exists(result_file_path):
                logger.error(f"结果文件不存在: {result_file_path}")
                return None
            
            with open(result_file_path, 'r', encoding='utf-8') as f:
                # 跳过标题行
                next(f, None)
                
                min_latency = float('inf')
                best_ip = None
                
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # 根据实际CSV格式: IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s),地区码
                        parts = line.split(',')
                        if len(parts) < 5:
                            continue
                        
                        ip = parts[0].strip()
                        try:
                            latency = float(parts[4].strip())
                        except ValueError:
                            logger.warning(f"无效的延迟值: {parts[4].strip()}，跳过此IP")
                            continue
                        
                        if latency < min_latency:
                            min_latency = latency
                            best_ip = ip
                    except ValueError as e:
                        logger.warning(f"解析行失败: {line}, 错误: {str(e)}")
                        continue
            
            if best_ip:
                logger.info(f"找到延迟最低的IP: {best_ip}, 延迟: {min_latency:.2f}ms")
                return best_ip
            else:
                logger.warning("未找到有效的IP地址")
                return None
        except Exception as e:
            logger.error(f"读取结果文件失败: {str(e)}")
            return None

    async def update_ddns(self) -> bool:
        """更新DDNS记录（异步版本）"""
        # 获取延迟最低的IP
        new_ip = self._get_lowest_latency_ip()
        if not new_ip:
            return False
        
        # 获取记录ID
        record_id = await self._get_record_id()
        
        # 重试机制
        for attempt in range(self.retry_count):
            if record_id:
                # 更新现有记录
                if await self._update_dns_record(record_id, new_ip):
                    return True
            else:
                # 创建新记录
                if await self._create_dns_record(new_ip):
                    return True
            
            # 重试前等待
            if attempt < self.retry_count - 1:
                logger.info(f"更新失败，{self.retry_interval}秒后重试...")
                await asyncio.sleep(self.retry_interval)
        
        logger.error(f"达到最大重试次数({self.retry_count})，更新失败")
        return False

    def run(self):
        """运行DDNS更新服务，成功后退出"""
        logger.info(f"启动Cloudflare DDNS更新，域名: {self.full_domain}")
        
        success = self.update_ddns()
        if success:
            logger.info("DDNS更新成功，程序退出")
        else:
            logger.error("DDNS更新失败，程序退出")