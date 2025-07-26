import os
import asyncio
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
        
        # 定时器配置
        self.enable_auto_update = config.get("enable_auto_update", False)
        self.auto_update_interval = config.get("auto_update_interval", 3600)  # 默认1小时
        self.auto_task = None
        
        # 初始化优化器
        self.optimizer = CloudflareIPOptimizer()
        
        logger.info("Cloudflare IP优化器插件已初始化")
        
        # 如果启用了自动更新，启动定时任务
        if self.enable_auto_update:
            asyncio.create_task(self.start_auto_update())
        
    @filter.command_group("cf")
    async def cf_group(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """Cloudflare IP优化器命令组"""
        if not event.message_str.strip():
            yield event.plain_result(
                "🌐 Cloudflare IP优化器 命令帮助:\n"
                "  cf 优化 - 执行IP优选测试\n"
                "  cf 更新 - 更新DDNS记录\n"
                "  cf 状态 - 检查插件状态\n"
                "  cf 自动更新 - 切换自动更新状态\n"
                "  cf 定时状态 - 查看自动更新状态"
            )
            return
    
    @cf_group.command("优化")
    async def optimize_ip(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """执行Cloudflare IP优选测试"""
        logger.info("📞 收到cf优化命令请求")
        try:
            yield event.plain_result("🚀 开始执行Cloudflare IP优选测试，请稍候...")
            
            # 检查工具状态
            logger.info(f"检查工具路径: {self.optimizer.cloudflarespeedtest_path}")
            tool_exists = os.path.exists(self.optimizer.cloudflarespeedtest_path)
            logger.info(f"工具存在状态: {tool_exists}")
            
            if not tool_exists:
                yield event.plain_result("📥 正在下载CloudflareSpeedTest工具...")
                logger.info("开始下载CloudflareSpeedTest工具...")
                download_success = await self.optimizer.download_cloudflarespeedtest()
                if not download_success:
                    logger.error("❌ 工具下载失败")
                    yield event.plain_result("❌ 下载CloudflareSpeedTest工具失败")
                    return
                logger.info("✅ 工具下载成功")
            else:
                logger.info("✅ 工具已存在，跳过下载")
            
            # 执行IP优选测试
            logger.info("开始执行IP优选测试...")
            success = await self.optimizer.run_test()
            
            if success:
                logger.info("✅ IP优选测试执行成功")
                # 读取结果文件
                result_file = os.path.join(self.optimizer._get_cfst_dir(), 'result.csv')
                logger.info(f"尝试读取结果文件: {result_file}")
                
                if os.path.exists(result_file):
                    import pandas as pd
                    try:
                        df = pd.read_csv(result_file)
                        logger.info(f"结果文件读取成功，共{len(df)}条记录")
                        
                        # 按延迟排序并显示前5个结果
                        df_sorted = df.sort_values(by='平均延迟').head(5)
                        
                        result_msg = "✅ IP优选测试完成！\n\n最优的5个IP:\n"
                        for idx, row in df_sorted.iterrows():
                            result_msg += f"{row['IP 地址']} - 延迟: {row['平均延迟']}ms - 速度: {row['下载速度(MB/s)']}MB/s\n"
                        
                        logger.info("准备返回测试结果给用户")
                        yield event.plain_result(result_msg)
                    except Exception as e:
                        logger.error(f"读取结果文件失败: {e}")
                        yield event.plain_result(f"✅ 测试完成，但读取结果失败: {str(e)}")
                else:
                    logger.warning("结果文件不存在")
                    yield event.plain_result("✅ IP优选测试完成，但未找到结果文件")
            else:
                logger.error("❌ IP优选测试执行失败")
                yield event.plain_result("❌ IP优选测试失败，请检查日志")
                
        except Exception as e:
            logger.error(f"❌ cf优化命令执行异常: {e}")
            import traceback
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            yield event.plain_result(f"❌ 执行失败: {str(e)}")

    @cf_group.command("更新")
    async def update_ddns(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """更新Cloudflare DDNS记录"""
        logger.info("📞 收到cf更新命令请求")
        try:
            # 检查必要配置
            missing_configs = []
            if not self.cf_token:
                missing_configs.append("cf_token")
            if not self.zone_id:
                missing_configs.append("zone_id")
            if not self.main_domain:
                missing_configs.append("main_domain")
                
            if missing_configs:
                logger.warning(f"❌ 缺少配置项: {missing_configs}")
                yield event.plain_result(f"❌ 请先配置Cloudflare相关参数: {', '.join(missing_configs)}")
                return
            
            logger.info("✅ 所有必要配置已设置")
            yield event.plain_result("🔄 开始更新Cloudflare DDNS记录...")
            
            logger.info("✅ IP优选测试完成，准备更新DDNS")
            
            # 配置DDNS更新器
            config = {
                "cf_token": self.cf_token,
                "zone_id": self.zone_id,
                "main_domain": self.main_domain,
                "sub_domain": self.sub_domain,
                "record_type": self.record_type,
                "result_file": "csft/result.csv"
            }
            
            logger.info(f"DDNS配置: {config}")
            ddns_updater = CloudflareDDNSUpdater(config)
            
            # 执行DDNS更新（异步）
            logger.info("开始执行DDNS更新...")
            yield event.plain_result("🔄 正在更新DDNS记录...")
            update_success = await ddns_updater.update_ddns()
            
            if update_success:
                logger.info("✅ DDNS更新成功")
                best_ip = ddns_updater._get_lowest_latency_ip()
                if best_ip:
                    domain = f"{self.sub_domain}.{self.main_domain}" if self.sub_domain else self.main_domain
                    logger.info(f"域名 {domain} 已更新为 IP: {best_ip}")
                    yield event.plain_result(f"✅ DDNS更新成功！\n域名: {domain} -> IP: {best_ip}")
                else:
                    logger.info("DDNS更新成功，但无法获取最佳IP")
                    yield event.plain_result("✅ DDNS更新成功！")
            else:
                logger.error("❌ DDNS更新失败")
                yield event.plain_result("❌ DDNS更新失败")
                
        except Exception as e:
            logger.error(f"❌ cf更新命令执行异常: {e}")
            import traceback
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            yield event.plain_result(f"❌ 更新失败: {str(e)}")

    @cf_group.command("状态")
    async def check_status(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """检查Cloudflare优化器状态"""
        logger.info("📞 收到cf状态命令请求")
        try:
            cfst_dir = self.optimizer._get_cfst_dir()
            tool_path = self.optimizer.cloudflarespeedtest_path
            
            logger.info(f"获取状态信息 - 工具目录: {cfst_dir}")
            logger.info(f"获取状态信息 - 工具路径: {tool_path}")
            
            # 检查工具状态
            tool_exists = os.path.exists(tool_path)
            result_file = os.path.join(cfst_dir, 'result.csv')
            result_exists = os.path.exists(result_file)
            
            logger.info(f"工具存在: {tool_exists}")
            logger.info(f"结果文件存在: {result_exists}")
            
            # 构建状态消息
            status_msg = "📊 Cloudflare优化器状态:\n\n"
            status_msg += f"工具目录: {cfst_dir}\n"
            status_msg += f"工具路径: {tool_path}\n"
            status_msg += f"工具存在: {'✅' if tool_exists else '❌'}\n"
            
            if result_exists:
                file_size = os.path.getsize(result_file)
                import time
                file_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(result_file)))
                status_msg += f"结果文件: ✅ (大小: {file_size}字节, 时间: {file_time})\n"
                logger.info(f"结果文件详情: 大小={file_size}字节, 修改时间={file_time}")
            else:
                status_msg += "结果文件: ❌\n"
            
            # Cloudflare配置状态
            cf_token_status = '✅' if self.cf_token else '❌'
            zone_id_status = '✅' if self.zone_id else '❌'
            
            status_msg += f"\nCloudflare配置:\n"
            status_msg += f"Token: {cf_token_status}\n"
            status_msg += f"Zone ID: {zone_id_status}\n"
            status_msg += f"主域名: {self.main_domain or '未设置'}\n"
            status_msg += f"子域名: {self.sub_domain or '未设置'}\n"
            
            logger.info(f"配置状态 - Token: {cf_token_status}, Zone ID: {zone_id_status}")
            logger.info(f"配置状态 - 主域名: {self.main_domain}, 子域名: {self.sub_domain}")
            
            logger.info("状态检查完成，准备返回结果")
            yield event.plain_result(status_msg)
            
        except Exception as e:
            logger.error(f"❌ cf状态命令执行异常: {e}")
            import traceback
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            yield event.plain_result(f"❌ 获取状态失败: {str(e)}")

    async def start_auto_update(self):
        """启动自动更新定时任务"""
        if self.auto_task is not None:
            logger.warning("自动更新任务已在运行")
            return
            
        logger.info(f"启动自动更新定时任务，间隔: {self.auto_update_interval}秒")
        self.auto_task = asyncio.create_task(self._auto_update_loop())

    async def stop_auto_update(self):
        """停止自动更新定时任务"""
        if self.auto_task is not None:
            logger.info("停止自动更新定时任务")
            self.auto_task.cancel()
            try:
                await self.auto_task
            except asyncio.CancelledError:
                pass
            self.auto_task = None

    async def _auto_update_loop(self):
        """自动更新循环任务"""
        logger.info("自动更新循环任务已启动")
        
        while True:
            try:
                # 等待指定间隔时间
                await asyncio.sleep(self.auto_update_interval)
                
                # 检查必要配置
                if not all([self.cf_token, self.zone_id, self.main_domain]):
                    logger.warning("自动更新缺少必要配置，跳过本次执行")
                    continue
                
                logger.info("🔄 开始执行定时IP优选和DDNS更新")
                
                # 执行IP优选测试
                test_success = await self.optimizer.run_test()
                if not test_success:
                    logger.error("定时IP优选测试失败，跳过DDNS更新")
                    continue
                
                # 执行DDNS更新
                config = {
                    "cf_token": self.cf_token,
                    "zone_id": self.zone_id,
                    "main_domain": self.main_domain,
                    "sub_domain": self.sub_domain,
                    "record_type": self.record_type,
                    "result_file": "csft/result.csv"
                }
                
                ddns_updater = CloudflareDDNSUpdater(config)
                update_success = await ddns_updater.update_ddns()
                
                if update_success:
                    best_ip = ddns_updater._get_lowest_latency_ip()
                    domain = f"{self.sub_domain}.{self.main_domain}" if self.sub_domain else self.main_domain
                    logger.info(f"✅ 定时DDNS更新成功！{domain} -> {best_ip}")
                else:
                    logger.error("❌ 定时DDNS更新失败")
                    
            except asyncio.CancelledError:
                logger.info("自动更新任务被取消")
                break
            except Exception as e:
                logger.error(f"自动更新任务执行异常: {e}")
                import traceback
                logger.error(f"异常堆栈:\n{traceback.format_exc()}")
                # 发生异常时等待一段时间后重试，避免频繁重试
                await asyncio.sleep(300)  # 等待5分钟

    @cf_group.command("自动更新")
    async def toggle_auto_update(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """切换自动更新状态"""
        try:
            if self.enable_auto_update:
                # 如果已启用，则禁用
                self.enable_auto_update = False
                await self.stop_auto_update()
                logger.info("自动更新已禁用")
                yield event.plain_result("✅ 自动更新已禁用")
            else:
                # 如果未启用，则启用
                self.enable_auto_update = True
                await self.start_auto_update()
                logger.info("自动更新已启用")
                yield event.plain_result(f"✅ 自动更新已启用，间隔: {self.auto_update_interval}秒")
                
        except Exception as e:
            logger.error(f"切换自动更新状态失败: {e}")
            yield event.plain_result(f"❌ 操作失败: {str(e)}")

    @cf_group.command("定时状态")
    async def check_auto_update_status(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """检查自动更新状态"""
        try:
            status_msg = "📊 自动更新状态:\n\n"
            status_msg += f"自动更新: {'✅ 已启用' if self.enable_auto_update else '❌ 已禁用'}\n"
            status_msg += f"更新间隔: {self.auto_update_interval}秒 ({self.auto_update_interval//3600}小时{self.auto_update_interval%3600//60}分钟)\n"
            status_msg += f"定时任务: {'✅ 运行中' if self.auto_task and not self.auto_task.cancelled() else '❌ 未运行'}\n"
            
            yield event.plain_result(status_msg)
            
        except Exception as e:
            logger.error(f"检查自动更新状态失败: {e}")
            yield event.plain_result(f"❌ 检查状态失败: {str(e)}")
