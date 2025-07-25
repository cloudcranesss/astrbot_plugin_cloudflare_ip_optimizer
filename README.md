# Cloudflare IP优化器 - AstrBot插件

这是一个AstrBot插件，集成了Cloudflare IP优选和DDNS更新功能，可以自动测试Cloudflare IP延迟并更新DNS记录。

## 🌟 功能特性

- **智能IP优选**: 自动测试Cloudflare IP延迟，选择最优节点
- **自动DDNS**: 自动将最优IP更新到Cloudflare DNS记录
- **跨平台支持**: 支持Windows和Linux系统
- **实时反馈**: 通过AstrBot命令实时查看测试结果
- **配置灵活**: 支持自定义域名、记录类型等参数

## 📦 安装方法

### 方法一：AstrBot插件市场安装
1. 打开AstrBot管理面板
2. 进入"插件管理" → "插件市场"
3. 搜索"Cloudflare IP优化器"
4. 点击安装即可

### 方法二：手动安装
1. 将插件文件夹复制到AstrBot的`data/plugins/`目录下
2. 重启AstrBot
3. 在管理面板中启用插件

## ⚙️ 配置说明

安装插件后，需要在AstrBot管理面板中配置以下参数：

### 必填配置
- **Cloudflare API Token**: 你的Cloudflare API令牌
- **Zone ID**: 你的域名对应的区域ID
- **主域名**: 你的域名，如`example.com`

### 可选配置
- **子域名前缀**: 子域名前缀，如`www`（留空表示根域名）
- **DNS记录类型**: A记录(IPv4)或AAAA记录(IPv6)，默认为A记录

### 获取配置信息

#### 1. 获取Cloudflare API Token
1. 登录[Cloudflare控制台](https://dash.cloudflare.com)
2. 点击右上角头像 → "My Profile"
3. 选择"API Tokens" → "Create Token"
4. 使用"Edit zone DNS"模板
5. 选择对应的域名，生成Token

#### 2. 获取Zone ID
1. 在Cloudflare控制台选择你的域名
2. 在"Overview"页面右侧可以找到"Zone ID"

## 🚀 使用方法

插件安装并配置完成后，可以通过以下AstrBot命令使用：

### 1. 执行IP优选测试
```
cf优化
```
执行Cloudflare IP延迟测试，返回最优的5个IP地址。

**示例输出：**
```
✅ IP优选测试完成！

最优的5个IP:
104.16.123.45 - 延迟: 12ms - 速度: 45.6MB/s
104.16.123.46 - 延迟: 15ms - 速度: 42.3MB/s
...
```

### 2. 更新DDNS记录
```
cf更新
```
执行IP优选测试后，自动将最优IP更新到指定的DNS记录。

**示例输出：**
```
✅ DDNS更新成功！
域名: www.example.com -> IP: 104.16.123.45
```

### 3. 检查插件状态
```
cf状态
```
显示插件当前状态和配置信息。

**示例输出：**
```
📊 Cloudflare优化器状态:

工具目录: /path/to/csft
工具路径: /path/to/cfst.exe
工具存在: ✅
结果文件: ✅ (大小: 1024字节, 时间: 2024-01-01 12:00:00)

Cloudflare配置:
Token: ✅
Zone ID: ✅
主域名: example.com
子域名: www
```

## 🔧 高级用法

### 自定义测试参数
插件会自动使用CloudflareSpeedTest的默认参数，如果需要自定义参数，可以手动修改`cloudflare_optimizer.py`文件中的`run_test`方法。

### 定时任务
可以结合AstrBot的定时任务功能，设置定期执行IP优选和DDNS更新：

```python
# 在AstrBot配置中添加定时任务
"scheduled_tasks": [
    {
        "name": "cloudflare_ip_check",
        "cron": "0 */6 * * *",
        "command": "cf更新"
    }
]
```

## 📋 注意事项

1. **权限要求**：确保Cloudflare API Token具有对应域名的DNS编辑权限
2. **网络要求**：需要能够访问Cloudflare的API接口
3. **首次运行**：首次使用时会自动下载CloudflareSpeedTest工具
4. **结果文件**：测试结果保存在`csft/result.csv`文件中

## 🐛 常见问题

### Q: 命令执行失败怎么办？
A: 使用`cf状态`命令检查插件状态，确认工具文件和配置是否正确。

### Q: DNS更新失败？
A: 检查Cloudflare配置是否正确，API Token是否有足够权限。

### Q: IP测试结果为空？
A: 检查网络连接，确保能够访问Cloudflare的IP测试服务。

## 📞 支持与反馈

如有问题或建议，请通过以下方式联系：
- 提交Issue到GitHub仓库
- 在AstrBot社区寻求帮助

## 📄 许可证

本项目采用MIT许可证，详见LICENSE文件。