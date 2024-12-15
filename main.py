import os
import subprocess
import re
from statistics import mean, median
import time
import threading

__version__ = '1.0.0'

def get_device_info():
    subprocess.run(['adb', 'root'], capture_output=True, text=True)

    # 获取制造商
    manufacturer = subprocess.check_output(['adb', 'shell', 'getprop', 'ro.product.manufacturer']).decode('utf-8').strip()

    # 获取设备型号
    model = subprocess.check_output(['adb', 'shell', 'getprop', 'ro.product.model']).decode('utf-8').strip()

    # 获取设备序列号
    sn = subprocess.check_output(['adb', 'shell', 'getprop', 'ro.serialno']).decode('utf-8').strip()

    # 获取设备内存
    meminfo = subprocess.check_output(['adb', 'shell', 'cat', '/proc/meminfo']).decode('utf-8')
    total_ram = None
    for line in meminfo.splitlines():
        if line.startswith('MemTotal'):
            total_ram = int(line.split()[1]) * 1024  # 转换为字节
            break
    
    # 获取设备存储
    storage_info = subprocess.check_output(['adb', 'shell', 'df']).decode('utf-8')
    storage = None
    for line in storage_info.splitlines():
        if '/data' in line:
            parts = line.split()
            storage = int(parts[1]) * 1024  # 转换为字节
            break
    
    # 获取设备版本信息
    android_version = subprocess.check_output(['adb', 'shell', 'getprop', 'ro.build.version.release']).decode('utf-8').strip()
    build_id = subprocess.check_output(['adb', 'shell', 'getprop', 'ro.build.id']).decode('utf-8').strip()
    build_fingerprint = subprocess.check_output(['adb', 'shell', 'getprop', 'ro.build.fingerprint']).decode('utf-8').strip()
    
    device_info = {
        'Manufacturer': manufacturer,
        'Model': model,
        'SN': sn,
        'RAM': total_ram,
        'Storage': storage,
        'OSVersion': android_version,
        'BuildID': build_id,
        'BuildFingerprint': build_fingerprint
    }

    print(f'Manufacturer: {device_info["Manufacturer"]}')
    print(f'Model: {device_info["Model"]}')
    print(f'SN: {device_info["SN"]}')
    print(f'RAM: {device_info["RAM"] / (1024 * 1024 * 1024)} GB')
    print(f'Storage: {device_info["Storage"] / (1024 * 1024 * 1024)} GB')
    print(f'OSVersion: {device_info["OSVersion"]}')
    print(f'BuildID: {device_info["BuildID"]}')
    print(f'BuildFingerprint: {device_info["BuildFingerprint"]}')
    pass

def install_apks():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    apk_dir = os.path.join(script_dir, 'pre-apks')
    if os.path.exists(apk_dir) and os.path.isdir(apk_dir):
        apks = [f for f in os.listdir(apk_dir) if f.endswith('.apk')]
        for apk in apks:
            apk_path = os.path.join(apk_dir, apk)
            print(f'Installing {apk}...')
            result = subprocess.run(['adb', 'install', '-r', apk_path], capture_output=True, text=True)
            if result.returncode == 0:
                print(f'Successfully installed {apk}')
            else:
                print(f'Failed to install {apk}: {result.stderr}')
    else:
        print(f'Directory {apk_dir} does not exist or is not a directory.')
    pass


def test_net_speed(url: str):
    """
    测试网络连接延时
    """
    print("URL:", url)
    ping_output = subprocess.run(['adb', 'shell', 'ping', '-c 200', url], capture_output=True, text=True)
    lines = ping_output.stdout.splitlines()
    response_times = []
    pattern = re.compile(r"time=(\d+\.?\d*) ms")
    stats_pattern = re.compile(r"(\d+) packets transmitted, (\d+) received, (\d+)% packet loss")

    for line in lines:
        match = pattern.search(line)
        if match:
            response_time = float(match.group(1))
            response_times.append(response_time)

    # Extract statistics
    stats_match = stats_pattern.search(ping_output.stdout)
    if stats_match:
        packets_transmitted = int(stats_match.group(1))
        packets_received = int(stats_match.group(2))
        packet_loss_percent = int(stats_match.group(3))
    else:
        packets_transmitted = 0
        packets_received = 0
        packet_loss_percent = 0

    analysis = {
        "Average Response Time": mean(response_times) if response_times else 0,
        "Median Response Time": median(response_times) if response_times else 0,
        "Fastest Response Time": min(response_times) if response_times else 0,
        "Slowest Response Time": max(response_times) if response_times else 0,
        "Packets Transmitted": packets_transmitted,
        "Packets Received": packets_received,
        "Packet Loss (%)": packet_loss_percent
    }

    def print_analysis_table(analysis):
        """Display the analysis results in a Markdown table format."""
        if not analysis:
            print("No valid response times found.")
            return
        
        headers = ["Statistic", "Value"]
        rows = [
            ["Average Response Time", f"{analysis['Average Response Time']:.2f} ms"],
            ["Median Response Time", f"{analysis['Median Response Time']:.2f} ms"],
            ["Fastest Response Time", f"{analysis['Fastest Response Time']:.2f} ms"],
            ["Slowest Response Time", f"{analysis['Slowest Response Time']:.2f} ms"],
            ["Packets Transmitted", f"{analysis['Packets Transmitted']}"],
            ["Packets Received", f"{analysis['Packets Received']}"],
            ["Packet Loss (%)", f"{analysis['Packet Loss (%)']}%"]
        ]
        
        # Generate the Markdown table
        markdown_table = f"| {' | '.join(headers)} |\n| {' | '.join(['---'] * len(headers))} |\n"
        for row in rows:
            markdown_table += f"| {' | '.join(row)} |\n"
        
        print(markdown_table)

    print_analysis_table(analysis)
    pass

def test_auto_connect_eth_onboot():
    """
    测试开启自动联网稳定性
    """
    test_no = 0
    connect_success = 0
    connect_fail = 0

    def test():
        subprocess.run(['adb', 'reboot'], capture_output=True, text=True)

        time.sleep(20)
        subprocess.run(['adb', 'wait-for-device'], capture_output=True, text=True)

        output = subprocess.run(['adb', 'shell', 'ip', 'addr'], capture_output=True, text=True)
        if output.returncode != 0:
            print(f"Error running command: {output.stderr}")
            return False

        if "inet " in output.stdout and "eth0" in output.stdout:
            return True
        else:
            print("Device failed to connect to network on boot.")
            return False
    
    for i in range(100):
        print("test_auto_connect_eth_onboot->", i)
        if test():
            connect_success+=1
        else:
            connect_fail+=1
        test_no+=1

    auto_connect_eth_onboot_info = {
        "TestCount" : test_no,
        "TestConSuccessCount" : connect_success,
        "TestConFailCount" : connect_fail,
    }

    print(f'TestCount: {auto_connect_eth_onboot_info["TestCount"]}')
    print(f'TestConSuccessCount: {auto_connect_eth_onboot_info["TestConSuccessCount"]}')
    print(f'TestConFailCount: {auto_connect_eth_onboot_info["TestConFailCount"]}')
    pass

def test_camera():
    """
    测试摄像头基本功能
    """
    # 打开OpenCamera.apk
    # net.sourceforge.opencamera/net.sourceforge.opencamera.MainActivity
    output = subprocess.run(['adb', 'shell', 'v4l2-ctl', '--list-devices'], capture_output=True, text=True)
    if output.returncode != 0:
        print(f"Error running command: {output.stderr}")
        return False
    print(output.stdout)

    os.system('adb remount')
    os.system('adb push bin/v4l2_capture /vendor/bin')
    os.system('adb shell chmod +x /vendor/bin/v4l2_capture')
    
    def task_capture_video():
        os.system('adb shell cd /vendor/bin && ./v4l2_capture -w 3860 -h 1920')
        pass

    thread_capture_video = threading.Thread(target=task_capture_video)
    thread_capture_video.start()

    time.sleep(30)

    if thread_capture_video.is_alive():
        process = thread_capture_video._result 
        if process.poll() is None:
            process.terminate()
            process.wait()

    os.system('adb pull /vendor/bin/capture_output.MJPEG .')
    output = os.popen('ls -l | grep capture_output').read()
    print(output)
    pass

if __name__ == '__main__':
    print(f'Tool version: {__version__}')

    print(f'Device Information:')
    print(20*"***")
    get_device_info()
    print(20*"***")

    print(f'Install APP:')
    print(20*"***")
    install_apks()
    print(20*"***")

    print(f'Test eth speed:')
    print(20*"***")
    test_net_speed('www.baidu.com')
    print(20*"***")
    # 兰州节点服务器
    test_net_speed('117.157.246.34')
    print(20*"***")
    # 秦皇岛节点服务器
    test_net_speed('202.63.172.185')
    print(20*"***")

    print(f'Test auto connect net on boot:')
    print(20*"***")
    test_auto_connect_eth_onboot()
    print(20*"***")


    print(f'Test camera:')
    print(20*"***")
    # test_camera()
    print(20*"***")