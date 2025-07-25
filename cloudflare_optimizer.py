import os
import time
import logging
import tempfile
import requests
import zipfile
import subprocess
import platform
from typing import List

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CloudflareIPOptimizer:
    """Cloudflare IP优选器核心类"""
    
    def __init__(self, cloudflarespeedtest_path: str = None):
        """
        初始化Cloudflare IP优选器
        :param cloudflarespeedtest_path: CloudflareSpeedTest可执行文件路径
        """
        if cloudflarespeedtest_path is None:
            # 自动检测cfst目录下的可执行文件
            cfst_dir = self._get_cfst_dir()
            logger.info(f"CloudflareSpeedTest目录: {cfst_dir}")
            
            # 检测当前操作系统
            system = platform.system().lower()
            
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
            
            for path in default_paths:
                if os.path.exists(path):
                    cloudflarespeedtest_path = path
                    logger.info(f"找到工具: {path}")
                    break
            else:
                # 如果没有找到，设置为默认值
                if 'windows' in system:
                    cloudflarespeedtest_path = os.path.join(cfst_dir, 'CloudflareSpeedTest.exe')
                else:
                    cloudflarespeedtest_path = os.path.join(cfst_dir, 'CloudflareSpeedTest')
                logger.info(f"未找到工具，使用默认路径: {cloudflarespeedtest_path}")
        
        self.cloudflarespeedtest_path = cloudflarespeedtest_path
        
    def _get_cfst_dir(self) -> str:
        """获取cfst目录路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        target_dir = os.path.join(current_dir, 'csft')
        os.makedirs(target_dir, exist_ok=True)
        return target_dir
        
    def download_cloudflarespeedtest(self) -> bool:
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
            
    def run_test(self, args: List[str] = None) -> bool:
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