# Doubao TTS API - Python 客户端

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

一个用于[豆包-火山引擎双向流式语音合成服务](https://www.volcengine.com/docs/6561/1329505)的非官方 Python 客户端。

An unofficial Python client for Doubao's (Volcano Engine) bidirectional streaming Text-to-Speech (TTS) service.

本项目基于 `asyncio` 和 `websockets`，提供了一个简单、高效的异步接口，用于实现实时文本到语音的转换，方便你将其集成到自己的 Python 应用中。

## ✨ 核心特性

- **完全异步**: 基于 `asyncio`，为高并发、非阻塞的 I/O 操作而设计。
- **实时流式传输**: 支持实时的双向流式数据传输，低延迟获取音频流。
- **简洁易用**: 封装了复杂的 WebSocket 协议，提供简单的客户端和回调接口。
- **事件驱动**: 通过回调函数处理连接、数据、错误和各类事件。

## ⚙️ 安装

推荐使用 Python 3.8 或更高版本。

```bash
# 安装依赖
pip install -r requirements.txt
```

主要依赖项包括:
- `websockets`: 用于处理 WebSocket 连接。
- `fastrand`: 用于生成随机数。

## 🚀 快速上手

下面是一个最小化的使用示例。你需要先从火山引擎控制台获取你的 `uid`, `app_id`, 和 `token`。

```python
# 引入 DoubaoTTSClient 和 ResultCallback
import asyncio
from api.doubao_tts_api import DoubaoTTSClient, ResultCallback

# 1. 实现你自己的回调处理类
class MyCallbackHandler(ResultCallback):
    def on_open(self):
        print("✅ 连接成功，TTS 会话开始。")

    def on_complete(self):
        print("✅ TTS 流式合成完成。")

    def on_error(self, message):
        print(f"❌ 发生错误: {message}")

    def on_close(self):
        print("🔒 连接关闭。")

    def on_event(self, message):
        # 接收服务端的元信息事件，例如句子的开始和结束
        print(f"🔔 收到事件: {message}")

    def on_data(self, data: bytes):
        # 接收音频数据。你可以在这里将数据写入文件或进行播放。
        print(f"🎵 收到 {len(data)} 字节的音频数据。")
        # 示例：将音频数据追加到本地文件
        with open("output.pcm", "ab") as f:
            f.write(data)

async def main():
    # 2. 配置并实例化客户端
    # 请替换为你的真实密钥和信息
    client = DoubaoTTSClient(
        uid="YOUR_UID",
        app_id="YOUR_APP_ID",
        token="YOUR_TOKEN",
        url="wss://openspeech.bytedance.com/api/v3/tts/bidirection",
        speaker="zh_female_wanwanxiaohe_moon_bigtts", # 示例音色
        callback=MyCallbackHandler()
    )

    try:
        # 3. 发送文本并等待合成完成
        text_to_synthesize = "你好，我是字节跳动的语音合成系统。很高兴为您服务！"
        await client.streaming_call(text_to_synthesize)
        await client.streaming_complete()

    except Exception as e:
        print(f"主程序出错: {e}")

if __name__ == "__main__":
    # 确保在项目的根目录下运行，或已正确设置 PYTHONPATH
    # 例如: PYTHONPATH=. python your_script.py
    asyncio.run(main())

```

## 🧪 运行官方测试

项目中提供了一个更完整的测试文件 `tests/test_api.py`，它包含了使用 `sounddevice` 和 `numpy` 进行实时音频播放的逻辑。

1.  **配置参数**
    在 `tests/test_api.py` 文件中，填入你自己的 `uid`、`app_id`、`token` 等信息。

2.  **运行测试**
    在项目根目录下执行以下命令：
    ```bash
    python -m tests.test_api
    ```
    程序将连接服务，合成语音并通过你的默认音频设备播放。

## 📋 API 参考

### `DoubaoTTSClient`
与 TTS 服务交互的核心类。

- `__init__(self, uid, app_id, token, url, speaker, callback)`:
  初始化客户端。参数包括用户ID、应用ID、访问令牌、服务URL、音色和回调处理器。

- `async streaming_call(self, text: str)`:
  异步发送文本到服务端进行合成。首次调用时会自动建立连接。你可以多次调用此方法以流式发送长文本。

- `async streaming_complete(self)`:
  通知服务端当前会话的所有文本已发送完毕。服务端在完成所有音频合成后会关闭流。

- `async streaming_cancel(self)`:
  立即终止当前会话并关闭连接。

### `ResultCallback`
用于处理客户端事件的回调接口。你需要继承此类并实现其方法。

- `on_open()`: 当 WebSocket 连接成功并且会话准备就绪时调用。
- `on_data(data: bytes)`: 当收到音频数据块时调用。
- `on_complete()`: 当服务端确认所有音频已发送完毕时调用。
- `on_error(message)`: 当发生错误时调用。
- `on_close()`: 当 WebSocket 连接关闭时调用。
- `on_event(message: str)`: 当收到服务端的元事件时调用（例如 `TTSSentenceStart`），`message` 是一个包含事件详情的 JSON 字符串。

## ⚠️ 注意事项

- 本项目为非官方客户端，请遵循火山引擎（字节跳动）的服务条款。
- 请确保你的密钥 (`app_id`, `token`) 有效且拥有 TTS 服务的访问权限。
- 本项目主要用于学习和测试目的。