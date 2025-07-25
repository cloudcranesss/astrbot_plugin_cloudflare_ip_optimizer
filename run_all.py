import os
import subprocess
import sys

def run_script(script_name):
    """运行指定的Python脚本"""
    try:
        print(f"正在运行{script_name}...")
        # 构造完整的脚本路径
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), script_name)
        # 运行脚本
        result = subprocess.run([sys.executable, script_path], check=True)
        print(f"{script_name}执行成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{script_name}执行失败: {e}")
        return False
    except Exception as e:
        print(f"运行{script_name}时发生错误: {e}")
        return False

if __name__ == '__main__':
    # 先运行main.py
    main_success = run_script('main.py')
    
    # 如果main.py执行成功，再运行ddns.py
    if main_success:
        run_script('ddns.py')
    else:
        print("main.py执行失败，不继续运行ddns.py")
        sys.exit(1)