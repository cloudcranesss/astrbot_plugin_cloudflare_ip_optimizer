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
            success = await asyncio.to_thread(self.optimizer.run_test)
            
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
            success = await asyncio.to_thread(self.optimizer.run_test)
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
        """
        运行CloudflareSpeedTest进行IP测试
        :param args: 额外的命令行参数
        :return: 是否运行成功
        """
        if args is None:
            args = []
            
        try:
            # 检查工具是否存在
            if not os.path.exists(self.cloudflarespeedtest_path):
                logger.info(f"工具 {self.cloudflarespeedtest_path} 不存在，尝试下载...")
                if not self.download_cloudflarespeedtest():
                    return False
            
            # 添加输出CSV格式参数
            if '-o' not in args:
                # 与ddns.py配置保持一致
                result_file = os.path.join(self._get_cfst_dir(), 'result.csv')
                args.extend(['-o', result_file])
            
            # 构建命令时确保使用完整的绝对路径
            cmd = [self.cloudflarespeedtest_path] + args
            logger.info(f"工具路径: {self.cloudflarespeedtest_path}")
            logger.info(f"工具是否存在: {os.path.exists(self.cloudflarespeedtest_path)}")
            logger.info(f"运行命令: {cmd}")

            # 执行命令，捕获输出但不实时打印
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                cwd=self._get_cfst_dir(),
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            output = []
            timeout = 600  # 增加超时时间到10分钟
            start_time = time.time()
            last_output_time = start_time

            # 定义成功指标
            success_indicators = ["延迟测速完成", "完整测速结果已写入", "测试完成", "完成测试", "测试结束"]
            # 添加一个标志来指示是否找到了成功指标
            success_found = False

            while True:
                # 检查是否超时
                current_time = time.time()
                if current_time - start_time > timeout:
                    process.kill()
                    logger.error(f"命令执行超时 ({timeout}秒)")
                    return False

                # 非阻塞读取输出
                line = process.stdout.readline()
                if line:
                    last_output_time = current_time
                    # 不再实时打印每一行，只收集输出
                    output.append(line)

                    # 检查是否包含成功指标
                    if not success_found and any(indicator in line for indicator in success_indicators):
                        success_found = True
                        logger.info(f"检测到测试进度: {line.strip()}")
                        # 继续等待进程结束，最多再等待10秒
                        wait_time = 0
                        while process.poll() is None and wait_time < 10:
                            time.sleep(0.5)
                            wait_time += 0.5
                        break

                elif process.poll() is not None:
                    # 进程已结束
                    break
                elif current_time - last_output_time > 120:
                    # 2分钟没有输出，认为进程卡住
                    process.kill()
                    logger.error(f"命令执行无响应 (超过2分钟没有输出)")
                    return False

                # 短暂休眠避免CPU占用过高
                time.sleep(0.1)

            output_str = ''.join(output)
            return_code = process.returncode
            logger.info(f"命令执行完成，返回码: {return_code}")
            logger.info(f"输出长度: {len(output_str)} 字符")

            # 确定输出文件路径
            output_file = args[-1] if len(args) > 0 and args[-2] == '-o' else 'result.csv'
            output_file_path = os.path.join(self._get_cfst_dir(), output_file)

            # 检查命令是否成功执行，放宽条件：如果成功指标已找到或结果文件存在且不为空，则认为成功
            if (return_code == 0 and (success_found or any(indicator in output_str for indicator in success_indicators))) or \
               (success_found and os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0):
                logger.info("IP优选完成")
                output_file = args[-1] if len(args) > 0 and args[-2] == '-o' else 'result.csv'
                logger.info(f"完整测速结果已写入 {output_file}")
                # 验证文件是否存在
                if os.path.exists(os.path.join(self._get_cfst_dir(), output_file)):
                    logger.info(f"结果文件已确认存在，大小: {os.path.getsize(os.path.join(self._get_cfst_dir(), output_file))} 字节")
                else:
                    logger.warning(f"结果文件不存在: {output_file}")
                return True

            error_msg = f"命令执行失败，返回码: {return_code}"
            if output_str:
                error_msg += f"，输出: {output_str[:200]}..."
            logger.error(error_msg)
            return False
        except FileNotFoundError:
            logger.error(f"未找到工具: {self.cloudflarespeedtest_path}")
            return False
        except PermissionError:
            logger.error(f"无权限执行工具: {self.cloudflarespeedtest_path}")
            return False
        except Exception as e:
            logger.error(f"发生错误: {str(e)}")
            return False

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