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
        """自动下载并安装CloudflareSpeedTest工具"""
        try:
            # GitHub releases API URL
            api_url = "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest"
            response = requests.get(api_url)
            response.raise_for_status()
            release_info = response.json()

            system = platform.system().lower()
            logger.info(f"当前操作系统: {system}")

            # 根据操作系统选择下载链接和文件后缀
            download_url = None
            file_suffix = ''
            if 'windows' in system:
                # 查找Windows版本
                for asset in release_info['assets']:
                    if 'windows' in asset['name'].lower() and asset['name'].endswith('.zip'):
                        download_url = asset['browser_download_url']
                        file_suffix = '.zip'
                        break
            elif 'linux' in system:
                # 查找Linux版本
                for asset in release_info['assets']:
                    if 'linux' in asset['name'].lower() and asset['name'].endswith('.tar.gz'):
                        download_url = asset['browser_download_url']
                        file_suffix = '.tar.gz'
                        break
            else:
                # 默认尝试Linux版本
                for asset in release_info['assets']:
                    if 'linux' in asset['name'].lower() and asset['name'].endswith('.tar.gz'):
                        download_url = asset['browser_download_url']
                        file_suffix = '.tar.gz'
                        break

            if not download_url:
                logger.error(f"未找到适用于{system}系统的下载链接")
                return False

            # 创建cfst目录
            cfst_dir = self._get_cfst_dir()
            os.makedirs(cfst_dir, exist_ok=True)
            
            # 下载并解压
            with tempfile.NamedTemporaryFile(suffix=file_suffix, delete=False) as tmp_file:
                tmp_file.write(requests.get(download_url).content)
            
            cfst_dir = self._get_cfst_dir()
            
            # 根据文件类型选择解压方式
            if file_suffix == '.zip':
                # 使用zipfile解压
                with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                    zip_ref.extractall(cfst_dir)
            elif file_suffix == '.tar.gz':
                # 使用tarfile解压
                import tarfile
                with tarfile.open(tmp_file.name, 'r:gz') as tar_ref:
                    tar_ref.extractall(cfst_dir)
            
            os.unlink(tmp_file.name)
            logger.info("CloudflareSpeedTest下载并安装成功")
            
            # 更新工具路径
            cfst_dir = self._get_cfst_dir()
            # 查找解压后的可执行文件
            for root, dirs, files in os.walk(cfst_dir):
                for file in files:
                    # Windows系统下直接查找带.exe的文件
                    if 'windows' in system:
                        if file.lower() == 'cloudflarespeedtest.exe':
                            self.cloudflarespeedtest_path = os.path.join(root, file)
                            break
                    else:
                        if file == 'CloudflareSpeedTest':
                            self.cloudflarespeedtest_path = os.path.join(root, file)
                            os.chmod(self.cloudflarespeedtest_path, 0o755)
                            break
                    if self.cloudflarespeedtest_path != 'CloudflareSpeedTest':
                        break
            return True
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return False
    @filter.command("cf更新")
    async def update_ddns(self, event: AstrMessageEvent) -> AsyncGenerator[Any, None]:
        """更新Cloudflare DDNS记录"""
        try:
            # 检查必要配置
            if not all([self.cf_token, self.zone_id, self.main_domain]):
                yield event.plain_result("❌ 请先配置Cloudflare相关参数")
                return
            
            yield event.plain_result("🔄 开始更新Cloudflare DDNS记录...")
            
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
            
            # 执行DDNS更新
            update_success = await asyncio.to_thread(ddns_updater.update_ddns)
            
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
    import argparse
    parser = argparse.ArgumentParser(description='Cloudflare IP优选')
    parser.add_argument('-n', '--thread', type=int, default=500, help='延迟测速线程；越多延迟测速越快，性能弱的设备 (如路由器) 请勿太高')
    parser.add_argument('-dn', '--count', type=int, default=10, help='下载测速数量；延迟测速并排序后，从最低延迟起下载测速的数量')
    parser.add_argument('-o', '--output', default='result.csv', help='写入结果文件；如路径含有空格请加上引号；值为空时不写入文件 [-o ""]；(默认 result.csv)')
    parser.add_argument('-p', '--params', type=int, default=0, help='显示结果数量；测速后直接显示指定数量的结果，为 0 时不显示结果直接退出；(默认 10 个)')
    args = parser.parse_args()
    
    # 运行IP优选
    optimizer = CloudflareIPOptimizer()
    test_params = []
    if args.thread:
        test_params.extend(['-n', str(args.thread)])
    if args.count:
        test_params.extend(['-dn', str(args.count)])
    if args.output:
        test_params.extend(['-o', args.output])
    if args.params:
        test_params.extend(['-p', str(args.params)])
    
    # 执行测试并处理结果
    success = optimizer.run_test(test_params)
    
    # 显示结果（如果需要）
    if success and args.params > 0:
        try:
            import pandas as pd
            df = pd.read_csv(os.path.join(optimizer._get_cfst_dir(), args.output))
            # 按延迟排序并显示前N个结果
            df_sorted = df.sort_values(by='延迟(ms)')
            print(f"\n前{args.params}个最优IP: ")
            print(df_sorted.head(args.params).to_string(index=False))
        except Exception as e:
            logger.error(f"显示结果时出错: {str(e)}")
    
    # 确保程序退出
    import sys
    sys.exit(0 if success else 1)