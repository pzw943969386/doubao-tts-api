import threading
import sounddevice as sd
import numpy as np
from collections import deque
import time
import uuid
import websockets
import asyncio
from api import DoubaoTTSClient

SAMPLE_RATE = 24000
CHANNELS = 1
audio_buffer = deque()
playing = True


def audio_player():
    """音频播放线程函数"""
    try:
        with sd.OutputStream(
            samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16", blocksize=1024
        ) as stream:
            while playing:
                if audio_buffer:
                    try:
                        data = audio_buffer.popleft()
                        if len(data) > 0:
                            audio_data = np.frombuffer(data, dtype=np.int16)
                            if len(audio_data) > 0:
                                stream.write(audio_data)
                                print(f"播放音频块: {len(audio_data)} 样本")
                    except Exception as e:
                        print(f"播放音频块时出错: {e}")
                else:
                    time.sleep(0.01)  # 避免CPU占用过高
    except Exception as e:
        print(f"音频播放线程出错: {e}")


audio_thread = threading.Thread(target=audio_player, daemon=True)
audio_thread.start()


class ResultCallback:
    def on_open(self) -> None:
        print("TTS连接已打开")

    def on_complete(self) -> None:
        print("TTS合成完成")

    def on_error(self, message) -> None:
        print(f"TTS错误: {message}")

    def on_close(self) -> None:
        print("TTS连接已关闭")

    def on_event(self, message: str) -> None:
        print(f"TTS事件: {message}")

    def on_data(self, data: bytes) -> None:
        try:
            if data and len(data) > 0:
                audio_buffer.append(data)
        except Exception as e:
            print(f"音频数据处理错误: {e}")


async def main():
    print("启动字节跳动TTS测试...")

    # 需要替换为你的实际参数
    uid = ""
    app_id = ""
    token = ""
    url = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
    speaker = "zh_female_wanwanxiaohe_moon_bigtts"

    callback = ResultCallback()
    client = DoubaoTTSClient(uid, app_id, token, url, speaker, callback)

    try:
        # 发送文本进行TTS合成
        await client.streaming_call(
            "你好，我是字节跳动的语音合成系统，很高兴为您服务！"
        )
        await asyncio.sleep(2)  # 等待处理

        await client.streaming_complete()

        # 等待播放完成
        print("等待音频播放完成...")
        await asyncio.sleep(20)

    except Exception as e:
        print(f"测试出错: {e}")
    finally:
        print("测试完成")

async def test_connect():
    headers = {
        "X-Api-App-Key": "",
        "X-Api-Access-Key": "",
        "X-Api-Resource-Id": "volc.service_type.10029",
        "X-Api-Connect-Id": str(uuid.uuid4()),
    }
    await websockets.connect(
        "wss://openspeech.bytedance.com/api/v3/tts/bidirection",
        additional_headers=headers,
        max_size=1024 * 1024 * 100,
    )

if __name__ == "__main__":
    asyncio.run(main())
    # asyncio.run(test_connect())