import os
import time
import tempfile
import aiohttp
import zipfile
import subprocess
import platform
from typing import List
from astrbot.api import logger

class CloudflareIPOptimizer:
    """Cloudflare IP优选器核心类"""
    
    def __init__(self, cloudflarespeedtest_path: str = None):
        """
        初始化Cloudflare IP优选器
        :param cloudflarespeedtest_path: CloudflareSpeedTest可执行文件路径
        """
        logger.info("=== 初始化Cloudflare IP优选器 ===")
        
        if cloudflarespeedtest_path is None:
            # 自动检测cfst目录下的可执行文件
            cfst_dir = self._get_cfst_dir()
            logger.info(f"CloudflareSpeedTest目录: {cfst_dir}")
            
            # 检测当前操作系统
            system = platform.system().lower()
            logger.info(f"检测到的操作系统: {system}")
            
            # 根据操作系统设置默认路径
            default_paths = []
            if 'windows' in system:
                default_paths = [
                    os.path.join(cfst_dir, 'cfst.exe'),
                    os.path.join(cfst_dir, 'CloudflareSpeedTest.exe'),
                ]
            else:
                default_paths = [
                    os.path.join(cfst_dir, 'cfst'),
                    os.path.join(cfst_dir, 'CloudflareSpeedTest'),
                ]
            
            logger.info(f"检测路径列表: {default_paths}")
            
            for path in default_paths:
                if os.path.exists(path):
                    cloudflarespeedtest_path = path
                    logger.info(f"✅ 找到工具: {path}")
                    break
                else:
                    logger.debug(f"❌ 路径不存在: {path}")
            else:
                # 如果没有找到，设置为默认值
                if 'windows' in system:
                    cloudflarespeedtest_path = os.path.join(cfst_dir, 'CloudflareSpeedTest.exe')
                else:
                    cloudflarespeedtest_path = os.path.join(cfst_dir, 'CloudflareSpeedTest')
                logger.info(f"❌ 未找到工具，使用默认路径: {cloudflarespeedtest_path}")
        else:
            logger.info(f"使用指定路径: {cloudflarespeedtest_path}")
            
        self.cloudflarespeedtest_path = cloudflarespeedtest_path
        logger.info(f"最终工具路径: {self.cloudflarespeedtest_path}")
        logger.info("=== 初始化完成 ===")
        
    def _get_cfst_dir(self) -> str:
        """获取cfst目录路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.join(current_dir, 'csft')
        os.makedirs(target_dir, exist_ok=True)
        return target_dir
        
    async def download_cloudflarespeedtest(self) -> bool:
        """自动下载并安装CloudflareSpeedTest工具（异步版本）"""
        logger.info("=== 开始下载CloudflareSpeedTest工具 ===")
        
        try:
            # GitHub releases API URL
            api_url = "https://api.github.com/repos/XIU2/CloudflareSpeedTest/releases/latest"
            logger.info(f"请求GitHub API: {api_url}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as response:
                    logger.info(f"API响应状态码: {response.status}")
                    response.raise_for_status()
                    release_info = await response.json()
                    logger.info(f"获取版本信息: {release_info.get('tag_name', '未知')}")

            system = platform.system().lower()
            logger.info(f"当前操作系统: {system}")

            # 根据操作系统选择下载链接和文件后缀
            download_url = None
            file_suffix = ''
            
            logger.info(f"可用资产列表: {[asset['name'] for asset in release_info['assets']]}")
            
            if 'windows' in system:
                # 查找Windows版本
                logger.info("正在查找Windows版本...")
                for asset in release_info['assets']:
                    logger.debug(f"检查资产: {asset['name']} - 是否匹配: {'windows' in asset['name'].lower() and asset['name'].endswith('.zip')}")
                    if 'windows' in asset['name'].lower() and asset['name'].endswith('.zip'):
                        download_url = asset['browser_download_url']
                        file_suffix = '.zip'
                        logger.info(f"找到Windows版本: {asset['name']}")
                        break
            elif 'linux' in system:
                # 查找Linux版本
                logger.info("正在查找Linux版本...")
                for asset in release_info['assets']:
                    logger.debug(f"检查资产: {asset['name']} - 是否匹配: {'linux' in asset['name'].lower() and asset['name'].endswith('.tar.gz')}")
                    if 'linux' in asset['name'].lower() and asset['name'].endswith('.tar.gz'):
                        download_url = asset['browser_download_url']
                        file_suffix = '.tar.gz'
                        logger.info(f"找到Linux版本: {asset['name']}")
                        break
            else:
                # 默认尝试Linux版本
                logger.info("未知系统，默认查找Linux版本...")
                for asset in release_info['assets']:
                    logger.debug(f"检查资产: {asset['name']} - 是否匹配: {'linux' in asset['name'].lower() and asset['name'].endswith('.tar.gz')}")
                    if 'linux' in asset['name'].lower() and asset['name'].endswith('.tar.gz'):
                        download_url = asset['browser_download_url']
                        file_suffix = '.tar.gz'
                        logger.info(f"找到Linux版本: {asset['name']}")
                        break

            if not download_url:
                logger.error(f"❌ 未找到适用于{system}系统的下载链接")
                return False
            
            logger.info(f"下载URL: {download_url}")
            logger.info(f"文件后缀: {file_suffix}")

            # 创建cfst目录
            cfst_dir = self._get_cfst_dir()
            os.makedirs(cfst_dir, exist_ok=True)
            
            # 异步下载文件
            logger.info("开始下载文件...")
            async with aiohttp.ClientSession() as session:
                async with session.get(download_url) as response:
                    logger.info(f"下载响应状态码: {response.status}")
                    response.raise_for_status()
                    content = await response.read()
                    logger.info(f"下载完成，文件大小: {len(content)} 字节")
            
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(suffix=file_suffix, delete=False) as tmp_file:
                tmp_file.write(content)
                logger.info(f"临时文件保存完成: {tmp_file.name}")
            
            cfst_dir = self._get_cfst_dir()
            logger.info(f"解压目标目录: {cfst_dir}")
            
            # 根据文件类型选择解压方式
            if file_suffix == '.zip':
                logger.info("使用zipfile解压...")
                with zipfile.ZipFile(tmp_file.name, 'r') as zip_ref:
                    zip_ref.extractall(cfst_dir)
                    logger.info(f"解压完成，文件列表: {zip_ref.namelist()}")
            elif file_suffix == '.tar.gz':
                logger.info("使用tarfile解压...")
                import tarfile
                with tarfile.open(tmp_file.name, 'r:gz') as tar_ref:
                    tar_ref.extractall(cfst_dir)
                    logger.info(f"解压完成，文件列表: {tar_ref.getnames()}")
            
            os.unlink(tmp_file.name)
            logger.info("临时文件已清理")
            logger.info("CloudflareSpeedTest下载并安装成功")
            
            # 更新工具路径
            cfst_dir = self._get_cfst_dir()
            # 查找解压后的可执行文件
            for root, dirs, files in os.walk(cfst_dir):
                for file in files:
                    # Windows系统下直接查找带.exe的文件
                    if 'windows' in system:
                        if file.lower() == 'cfst.exe' or file.lower() == 'cloudflarespeedtest.exe':
                            self.cloudflarespeedtest_path = os.path.join(root, file)
                            break
                    else:
                        if file.lower() == 'cfst' or file.lower() == 'cloudflarespeedtest':
                            self.cloudflarespeedtest_path = os.path.join(root, file)
                            os.chmod(self.cloudflarespeedtest_path, 0o755)
                            break
                    if self.cloudflarespeedtest_path != os.path.join(cfst_dir, 'CloudflareSpeedTest') and self.cloudflarespeedtest_path != os.path.join(cfst_dir, 'CloudflareSpeedTest.exe'):
                        break
            return True
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return False
            
    async def run_test(self, args: List[str] = None) -> bool:
        """
        运行CloudflareSpeedTest进行IP测试
        :param args: 额外的命令行参数
        :return: 是否运行成功
        """
        logger.info("=== 开始执行Cloudflare IP优选测试 ===")
        
        if args is None:
            args = []
            
        logger.info(f"测试参数: {args}")
        
        try:
            # 检查工具是否存在
            logger.info(f"检查工具路径: {self.cloudflarespeedtest_path}")
            if not os.path.exists(self.cloudflarespeedtest_path):
                logger.warning(f"❌ 工具不存在: {self.cloudflarespeedtest_path}")
                logger.info("尝试下载工具...")
                if not await self.download_cloudflarespeedtest():
                    logger.error("❌ 工具下载失败")
                    return False
                logger.info("✅ 工具下载成功")
            else:
                logger.info(f"✅ 工具已存在: {self.cloudflarespeedtest_path}")
            
            # 添加输出CSV格式参数
            if '-o' not in args:
                # 与ddns.py配置保持一致
                result_file = os.path.join(self._get_cfst_dir(), 'result.csv')
                args.extend(['-o', result_file])
            
            # 构建命令时确保使用完整的绝对路径
            cmd = [self.cloudflarespeedtest_path] + args
            logger.info(f"完整命令: {' '.join(cmd)}")
            logger.info(f"工作目录: {self._get_cfst_dir()}")

            # 执行命令，捕获输出但不实时打印
            logger.info("开始执行命令...")
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
            logger.info(f"进程PID: {process.pid}")

            output = []
            timeout = 300 # 添加超时参数
            start_time = time.time()
            last_output_time = start_time

            # 定义成功指标
            success_indicators = ["延迟测速完成", "完整测速结果已写入", "测试完成", "完成测试", "测试结束"]
            # 添加一个标志来指示是否找到了成功指标
            success_found = False

            logger.info(f"开始监控进程，超时时间: {timeout}秒")
            
            while True:
                # 检查是否超时
                current_time = time.time()
                elapsed_time = current_time - start_time
                
                if current_time - start_time > timeout:
                    process.kill()
                    logger.error(f"❌ 命令执行超时 ({timeout}秒)，已运行: {elapsed_time:.1f}秒")
                    return False

                # 非阻塞读取输出
                line = process.stdout.readline()
                if line:
                    last_output_time = current_time
                    output.append(line)
                    logger.debug(f"进程输出: {line.strip()}")

                    # 检查是否包含成功指标
                    if not success_found and any(indicator in line for indicator in success_indicators):
                        success_found = True
                        logger.info(f"✅ 检测到测试进度: {line.strip()}")
                        # 继续等待进程结束，最多再等待10秒
                        wait_time = 0
                        while process.poll() is None and wait_time < 10:
                            time.sleep(0.5)
                            wait_time += 0.5
                        break

                elif process.poll() is not None:
                    # 进程已结束
                    logger.info(f"进程正常结束，返回码: {process.returncode}")
                    break
                elif current_time - last_output_time > 120:
                    # 2分钟没有输出，认为进程卡住
                    process.kill()
                    logger.error(f"❌ 命令执行无响应 (超过2分钟没有输出)，已运行: {elapsed_time:.1f}秒")
                    return False

                # 短暂休眠避免CPU占用过高
                time.sleep(0.1)

            output_str = ''.join(output)
            return_code = process.returncode
            elapsed_time = time.time() - start_time
            logger.info(f"命令执行完成，返回码: {return_code}, 运行时间: {elapsed_time:.1f}秒")
            logger.info(f"输出总行数: {len(output)} 行")
            
            # 记录关键输出信息
            if output_str:
                logger.debug(f"完整输出:\n{output_str}")
            else:
                logger.warning("❌ 没有获取到任何输出")

            # 确定输出文件路径
            output_file = args[-1] if len(args) > 0 and args[-2] == '-o' else 'result.csv'
            output_file_path = os.path.join(self._get_cfst_dir(), output_file)
            logger.info(f"预期结果文件: {output_file_path}")

            # 检查文件状态
            file_exists = os.path.exists(output_file_path)
            file_size = 0
            if file_exists:
                file_size = os.path.getsize(output_file_path)
                logger.info(f"结果文件状态: 存在={file_exists}, 大小={file_size}字节")
            else:
                logger.warning(f"❌ 结果文件不存在: {output_file_path}")

            # 检查命令是否成功执行
            success_condition = (return_code == 0 and (success_found or any(indicator in output_str for indicator in success_indicators))) or \
               (success_found and file_exists and file_size > 0)
            
            logger.info(f"成功条件检查结果: {success_condition}")
            logger.info(f"返回码: {return_code}, 成功标志: {success_found}")
            
            if success_condition:
                logger.info("✅ Cloudflare IP优选测试成功完成")
                logger.info(f"📊 完整测速结果已写入: {output_file_path}")
                
                # 读取结果文件前几行作为验证
                if file_exists and file_size > 0:
                    try:
                        with open(output_file_path, 'r', encoding='utf-8') as f:
                            first_line = f.readline().strip()
                            logger.info(f"结果文件首行: {first_line}")
                    except Exception as e:
                        logger.warning(f"读取结果文件失败: {e}")
                        
                return True

            # 失败情况详细记录
            logger.error("❌ Cloudflare IP优选测试失败")
            logger.error(f"失败原因分析:")
            logger.error(f"  - 返回码: {return_code} (0表示成功)")
            logger.error(f"  - 成功标志: {success_found} (是否检测到成功指标)")
            logger.error(f"  - 结果文件: {file_exists} (是否存在)")
            logger.error(f"  - 文件大小: {file_size}字节")
            
            if output_str:
                # 提取错误信息
                error_lines = [line for line in output_str.split('\n') if any(keyword in line.lower() for keyword in ['error', '错误', 'failed', '失败', 'exception'])]
                if error_lines:
                    logger.error(f"错误信息摘要:\n" + '\n'.join(error_lines[-5:]))  # 最后5条错误
                else:
                    # 记录最后几行输出
                    lines = output_str.split('\n')
                    last_lines = lines[-10:] if len(lines) > 10 else lines
                    logger.error(f"最后输出内容:\n" + '\n'.join(last_lines))
            
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