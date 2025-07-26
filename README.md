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
- **启用自动定时更新**: 是否启用自动定时执行IP优选测试和DDNS更新
- **自动更新间隔时间**: 自动执行的时间间隔，单位为秒，建议至少3600秒（1小时）

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
cf 优化
```
执行Cloudflare IP延迟测试，返回最优的5个IP地址。

**示例输出：**
```
用户: cf 优化
机器人: 🚀 开始执行Cloudflare IP优选测试，请稍候...
机器人: ✅ IP优选测试完成！

最优的5个IP:
104.16.123.45 - 延迟: 45ms - 速度: 15.2MB/s
104.16.123.46 - 延迟: 48ms - 速度: 14.8MB/s
104.16.123.47 - 延迟: 52ms - 速度: 14.5MB/s
104.16.123.48 - 延迟: 55ms - 速度: 14.1MB/s
104.16.123.49 - 延迟: 58ms - 速度: 13.9MB/s
```

### 2. 更新DDNS记录
```
cf 更新
```
执行IP优选测试后，自动将最优IP更新到指定的DNS记录。

**示例输出：**
```
用户: cf 更新
机器人: 🔄 开始更新Cloudflare DDNS记录...
机器人: ✅ DDNS更新成功！
域名: www.example.com -> IP: 104.16.123.45
```

### 3. 检查插件状态
```
cf 状态
```
显示插件当前状态和配置信息。

**示例输出：**
```
用户: cf 状态
机器人: 📊 Cloudflare优化器状态:

工具目录: /app/plugins/astrbot_plugin_cloudflare_ip_optimizer/cfst
工具路径: /app/plugins/astrbot_plugin_cloudflare_ip_optimizer/cfst/cfst
工具存在: ✅
结果文件: ✅ (大小: 1024字节, 时间: 2024-01-15 14:30:25)

Cloudflare配置:
Token: ✅
Zone ID: ✅
主域名: example.com
子域名: www
```

### 4. 自动更新控制

#### 启用/禁用自动更新
```
cf 自动更新
```
切换自动定时更新功能的开关状态。

**示例输出：**
```
✅ 自动更新已启用，间隔: 3600秒
```
或
```
✅ 自动更新已禁用
```

#### 查看定时状态
```
cf 定时状态
```
显示自动更新的当前状态。

**示例输出：**
```
📊 自动更新状态:

自动更新: ✅ 已启用
更新间隔: 3600秒 (1小时0分钟)
定时任务: ✅ 运行中
```

## 🔧 高级用法

### 自定义测试参数
插件会自动使用CloudflareSpeedTest的默认参数，如果需要自定义参数，可以手动修改`cloudflare_optimizer.py`文件中的`run_test`方法。

### 自动定时更新
插件内置了自动定时更新功能，无需额外配置AstrBot定时任务：

#### 配置方法
1. 在AstrBot管理面板的插件配置中
2. 设置"启用自动定时更新"为`true`
3. 设置合适的"自动更新间隔时间"（建议至少3600秒/1小时）

#### 手动控制
即使配置了自动更新，也可以通过命令随时控制：
- `cf自动更新` - 切换自动更新开关
- `cf定时状态` - 查看当前定时状态

#### 推荐配置
- **个人网站**: 3600秒（1小时）
- **企业网站**: 7200秒（2小时）
- **CDN优化**: 1800秒（30分钟）

### 自定义测试参数
插件会自动使用CloudflareSpeedTest的默认参数，如果需要自定义参数，可以手动修改`cloudflare_optimizer.py`文件中的`run_test`方法。

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