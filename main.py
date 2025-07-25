import os
import json
import asyncio
import logging
from typing import Any, AsyncGenerator
from astrbot.api import logger, AstrBotConfig
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Star, register, Context

# 导入原有的功能模块
from .cloudflare_optimizer import CloudflareIPOptimizer
from .cloudflare_ddns import CloudflareDDNSUpdater

@register("Cloudflare IP优化器", "cloudcranesss", "Cloudflare IP优选和DDNS更新插件", "1.0.0")
class CloudflareIPOptimizerPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        
        # 获取配置
        self.cf_token = config.get("cf_token", "")
        self.zone_id = config.get("zone_id", "")
        self.main_domain = config.get("main_domain", "")
        self.sub_domain = config.get("sub_domain", "")
        self.record_type = config.get("record_type", "A")
        
        # 初始化优化器
        self.optimizer = CloudflareIPOptimizer()
        
        logger.info("Cloudflare IP优化器插件已初始化")
        
    @filter.command("cf优化")
    async def optimize_ip(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """执行Cloudflare IP优选测试"""
        try:
            yield event.plain_result("🚀 开始执行Cloudflare IP优选测试，请稍候...")
            
            # 确保CloudflareSpeedTest已安装
            if not os.path.exists(self.optimizer.cloudflarespeedtest_path):
                yield event.plain_result("📥 正在下载CloudflareSpeedTest工具...")
                download_success = await self.optimizer.download_cloudflarespeedtest()
                if not download_success:
                    yield event.plain_result("❌ 下载CloudflareSpeedTest工具失败")
                    return
            
            # 执行IP优选测试
            success = await self.optimizer.run_test()
            
            if success:
                # 读取结果文件
                result_file = os.path.join(self.optimizer._get_cfst_dir(), 'result.csv')
                if os.path.exists(result_file):
                    import pandas as pd
                    try:
                        df = pd.read_csv(result_file)
                        # 按延迟排序并显示前5个结果
                        df_sorted = df.sort_values(by='延迟(ms)').head(5)
                        
                        result_msg = "✅ IP优选测试完成！\n\n最优的5个IP:\n"
                        for idx, row in df_sorted.iterrows():
                            result_msg += f"{row['IP 地址']} - 延迟: {row['延迟(ms)']}ms - 速度: {row['下载速度(MB/s)']}MB/s\n"
                        
                        yield event.plain_result(result_msg)
                    except Exception as e:
                        yield event.plain_result(f"✅ 测试完成，但读取结果失败: {str(e)}")
                else:
                    yield event.plain_result("✅ IP优选测试完成，但未找到结果文件")
            else:
                yield event.plain_result("❌ IP优选测试失败，请检查日志")
                
        except Exception as e:
            yield event.plain_result(f"❌ 执行失败: {str(e)}")

    @filter.command("cf更新")
    async def update_ddns(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """更新Cloudflare DDNS记录"""
        try:
            # 检查必要配置
            if not all([self.cf_token, self.zone_id, self.main_domain]):
                yield event.plain_result("❌ 请先配置Cloudflare相关参数")
                return
            
            yield event.plain_result("🔄 开始更新Cloudflare DDNS记录...")
            
            # 确保CloudflareSpeedTest已安装
            if not os.path.exists(self.optimizer.cloudflarespeedtest_path):
                yield event.plain_result("📥 正在下载CloudflareSpeedTest工具...")
                download_success = await self.optimizer.download_cloudflarespeedtest()
                if not download_success:
                    yield event.plain_result("❌ 下载CloudflareSpeedTest工具失败")
                    return
            
            # 首先执行IP优选
            success = await self.optimizer.run_test()
            if not success:
                yield event.plain_result("❌ IP优选失败，无法更新DDNS")
                return
            
            # 配置DDNS更新器
            config = {
                "cf_token": self.cf_token,
                "zone_id": self.zone_id,
                "main_domain": self.main_domain,
                "sub_domain": self.sub_domain,
                "record_type": self.record_type,
                "result_file": "csft/result.csv"
            }
            
            ddns_updater = CloudflareDDNSUpdater(config)
            
            # 执行DDNS更新（异步）
            update_success = await ddns_updater.update_ddns()
            
            if update_success:
                best_ip = ddns_updater._get_lowest_latency_ip()
                if best_ip:
                    domain = f"{self.sub_domain}.{self.main_domain}" if self.sub_domain else self.main_domain
                    yield event.plain_result(f"✅ DDNS更新成功！\n域名: {domain} -> IP: {best_ip}")
                else:
                    yield event.plain_result("✅ DDNS更新成功！")
            else:
                yield event.plain_result("❌ DDNS更新失败")
                
        except Exception as e:
            yield event.plain_result(f"❌ 更新失败: {str(e)}")

    @filter.command("cf状态")
    async def check_status(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """检查Cloudflare优化器状态"""
        try:
            cfst_dir = self.optimizer._get_cfst_dir()
            tool_path = self.optimizer.cloudflarespeedtest_path
            
            status_msg = "📊 Cloudflare优化器状态:\n\n"
            status_msg += f"工具目录: {cfst_dir}\n"
            status_msg += f"工具路径: {tool_path}\n"
            status_msg += f"工具存在: {'✅' if os.path.exists(tool_path) else '❌'}\n"
            
            result_file = os.path.join(cfst_dir, 'result.csv')
            if os.path.exists(result_file):
                file_size = os.path.getsize(result_file)
                import time
                file_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(result_file)))
                status_msg += f"结果文件: ✅ (大小: {file_size}字节, 时间: {file_time})\n"
            else:
                status_msg += "结果文件: ❌\n"
            
            status_msg += f"\nCloudflare配置:\n"
            status_msg += f"Token: {'✅' if self.cf_token else '❌'}\n"
            status_msg += f"Zone ID: {'✅' if self.zone_id else '❌'}\n"
            status_msg += f"主域名: {self.main_domain or '未设置'}\n"
            status_msg += f"子域名: {self.sub_domain or '未设置'}\n"
            
            yield event.plain_result(status_msg)
            
        except Exception as e:
            yield event.plain_result(f"❌ 获取状态失败: {str(e)}")