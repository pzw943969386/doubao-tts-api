# doubao-tts-api

豆包双向流式语音合成 API

本项目是基于字节跳动 TTS WebSocket 服务的 Python 客户端实现，支持流式语音合成和音频播放，适合快速集成和测试。

# 火山官方接口文档
https://www.volcengine.com/docs/6561/1329505

## 安装依赖

建议使用 Python 3.8 及以上版本。

```bash
pip install -r requirements.txt
```

主要依赖：

- websockets
- numpy
- sounddevice
- fastrand

## 快速开始

1. **配置参数**

   在 `tests/test_api.py` 中，填写你自己的 `uid`、`app_id`、`token`、`url` 和 `speaker`。

2. **运行测试**

   推荐在项目根目录下运行：

   ```bash
   python -m tests.test_api
   ```

   或者：

   ```bash
   PYTHONPATH=. python tests/test_api.py
   ```

3. **效果**

   程序会连接字节跳动 TTS 服务，合成语音并自动播放。

## 使用示例

`tests/test_api.py` 文件提供了一个完整的使用示例。以下是其核心逻辑：

```python
# tests/test_api.py 核心代码摘录
# 注意：此代码片段依赖于该文件中定义的音频播放器和 audio_buffer
# 完整代码请参考 tests/test_api.py

from api import DoubaoTTSClient

class ResultCallback:
    def on_open(self): print("TTS连接已打开")
    def on_complete(self): print("TTS合成完成")
    def on_error(self, message): print(f"TTS错误: {message}")
    def on_close(self): print("TTS连接已关闭")
    def on_event(self, message): print(f"TTS事件: {message}")
    def on_data(self, data):
        # 将音频数据放入播放缓冲区
        audio_buffer.append(data)

async def main():
    # 填写你的参数
    uid = ""
    app_id = ""
    token = ""
    url = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
    speaker = "zh_female_wanwanxiaohe_moon_bigtts"

    callback = ResultCallback()
    client = DoubaoTTSClient(uid, app_id, token, url, speaker, callback)
    await client.streaming_call("你好，我是字节跳动的语音合成系统，很高兴为您服务！")
    await client.streaming_complete()

if __name__ == "__main__":
    # 完整的 `tests/test_api.py` 中还包含了音频播放的初始化逻辑
    asyncio.run(main())
```

## 主要类说明

- `DoubaoTTSClient`
  封装了 TTS WebSocket 连接、事件处理、音频流接收等功能。

- `ResultCallback`
  回调接口，处理连接、数据、错误等事件。

## 注意事项

- 请确保你的 `app_id`、`token`、`uid` 有效且有 TTS 权限。
- 网络需能访问 `openspeech.bytedance.com`，如遇连接问题请尝试更换网络环境。
- 仅供学习和测试使用，生产环境请遵循字节跳动官方 API 文档和合规要求。

