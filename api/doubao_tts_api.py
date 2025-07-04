import websockets
import json
import uuid
import asyncio

# import fastrand
from websockets.protocol import State

PROTOCOL_VERSION = 0b0001
DEFAULT_HEADER_SIZE = 0b0001

# Message Type:
FULL_CLIENT_REQUEST = 0b0001
AUDIO_ONLY_RESPONSE = 0b1011
FULL_SERVER_RESPONSE = 0b1001
ERROR_INFORMATION = 0b1111

# Message Type Specific Flags
MsgTypeFlagNoSeq = 0b0000  # Non-terminal packet with no sequence
MsgTypeFlagPositiveSeq = 0b1  # Non-terminal packet with sequence > 0
MsgTypeFlagLastNoSeq = 0b10  # last packet with no sequence
MsgTypeFlagNegativeSeq = 0b11  # Payload contains event number (int32)
MsgTypeFlagWithEvent = 0b100
# Message Serialization
NO_SERIALIZATION = 0b0000
JSON = 0b0001
# Message Compression
COMPRESSION_NO = 0b0000
COMPRESSION_GZIP = 0b0001

EVENT_NONE = 0
EVENT_Start_Connection = 1

EVENT_FinishConnection = 2

EVENT_ConnectionStarted = 50  # 成功建连

EVENT_ConnectionFailed = 51  # 建连失败（可能是无法通过权限认证）

EVENT_ConnectionFinished = 52  # 连接结束

# 上行Session事件
EVENT_StartSession = 100

EVENT_FinishSession = 102
# 下行Session事件
EVENT_SessionStarted = 150
EVENT_SessionFinished = 152

EVENT_SessionFailed = 153

# 上行通用事件
EVENT_TaskRequest = 200

# 下行TTS事件
EVENT_TTSSentenceStart = 350

EVENT_TTSSentenceEnd = 351

EVENT_TTSResponse = 352


class Header:
    def __init__(
        self,
        protocol_version=PROTOCOL_VERSION,
        header_size=DEFAULT_HEADER_SIZE,
        message_type: int = 0,
        message_type_specific_flags: int = 0,
        serial_method: int = NO_SERIALIZATION,
        compression_type: int = COMPRESSION_NO,
        reserved_data=0,
    ):
        self.header_size = header_size
        self.protocol_version = protocol_version
        self.message_type = message_type
        self.message_type_specific_flags = message_type_specific_flags
        self.serial_method = serial_method
        self.compression_type = compression_type
        self.reserved_data = reserved_data

    def as_bytes(self) -> bytes:
        return bytes(
            [
                (self.protocol_version << 4) | self.header_size,
                (self.message_type << 4) | self.message_type_specific_flags,
                (self.serial_method << 4) | self.compression_type,
                self.reserved_data,
            ]
        )


class Optional:
    def __init__(
        self, event: int = EVENT_NONE, sessionId: str = None, sequence: int = None
    ):
        self.event = event
        self.sessionId = sessionId
        self.errorCode: int = 0
        self.connectionId: str | None = None
        self.response_meta_json: str | None = None
        self.sequence = sequence

    # 转成 byte 序列
    def as_bytes(self) -> bytes:
        option_bytes = bytearray()
        if self.event != EVENT_NONE:
            option_bytes.extend(self.event.to_bytes(4, "big", signed=True))
        if self.sessionId is not None:
            session_id_bytes = str.encode(self.sessionId)
            size = len(session_id_bytes).to_bytes(4, "big", signed=True)
            option_bytes.extend(size)
            option_bytes.extend(session_id_bytes)
        if self.sequence is not None:
            option_bytes.extend(self.sequence.to_bytes(4, "big", signed=True))
        return option_bytes


class Response:
    def __init__(self, header: Header, optional: Optional):
        self.optional = optional
        self.header = header
        self.payload: bytes | None = None
        self.payload_json: str | None = None

    def __str__(self):
        return super().__str__()


class ResultCallback:
    def on_open(self) -> None:
        pass

    def on_complete(self) -> None:
        pass

    def on_error(self, message) -> None:
        pass

    def on_close(self) -> None:
        pass

    def on_event(self, message: str) -> None:
        pass

    def on_data(self, data: bytes) -> None:
        pass


class Request:
    def __init__(self, uid: str):
        self.uid = uid

    def get_payload_bytes(
        self,
        event=EVENT_NONE,
        text="",
        speaker="",
        audio_format="pcm",
        audio_sample_rate=24000,
    ):
        return str.encode(
            json.dumps(
                {
                    "user": {"uid": self.uid},
                    "event": event,
                    "namespace": "BidirectionalTTS",
                    "req_params": {
                        "text": text,
                        "speaker": speaker,
                        "audio_params": {
                            "format": audio_format,
                            "sample_rate": audio_sample_rate,
                        },
                    },
                }
            )
        )

    async def start_connection(self):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
        ).as_bytes()
        optional = Optional(event=EVENT_Start_Connection).as_bytes()
        payload = str.encode("{}")
        return (header, optional, payload)

    async def start_session(self, speaker, session_id: str):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
            serial_method=JSON,
        ).as_bytes()
        optional = Optional(event=EVENT_StartSession, sessionId=session_id).as_bytes()
        payload = self.get_payload_bytes(event=EVENT_StartSession, speaker=speaker)
        return (header, optional, payload)

    async def finish_session(self, session_id):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
            serial_method=JSON,
        ).as_bytes()
        optional = Optional(event=EVENT_FinishSession, sessionId=session_id).as_bytes()
        payload = str.encode("{}")
        return (header, optional, payload)

    async def finish_connection(self):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
            serial_method=JSON,
        ).as_bytes()
        optional = Optional(event=EVENT_FinishConnection).as_bytes()
        payload = str.encode("{}")
        return (header, optional, payload)


class DoubaoTTSClient:
    def __init__(
        self,
        uid: str,
        app_id: str,
        token: str,
        url: str,
        speaker: str,
        callback: ResultCallback,
    ):
        self.uid = uid
        self.app_id = app_id
        self.token = token
        self.url = url
        self.speaker = speaker
        self.callback = callback
        self.websocket = None
        self.websocket_task = None

        self.request = Request(uid=self.uid)

        self._lock = asyncio.Lock()
        self._send_lock = asyncio.Lock()

        self._is_started = False
        self._is_stopped = False
        self._is_first = True

        self.session_id = str(uuid.uuid4())

        self.start_connection_event = asyncio.Event()
        self.start_session_event = asyncio.Event()
        self.complete_event = asyncio.Event()

    # def gen_log_id(self):
    #     ts = int(time.time() * 1000)
    #     r = fastrand.pcg32bounded(1 << 24) + (1 << 20)
    #     local_ip = "00000000000000000000000000000000"
    #     return f"02{ts}{local_ip}{r:08x}"

    async def __send_event(
        self, header: bytes, optional: bytes | None = None, payload: bytes = None
    ):
        async with self._send_lock:
            if self.websocket and self.websocket.state == State.OPEN:
                full_client_request = bytearray(header)
                if optional is not None:
                    full_client_request.extend(optional)
                if payload is not None:
                    payload_size = len(payload).to_bytes(4, "big", signed=True)
                    full_client_request.extend(payload_size)
                    full_client_request.extend(payload)
                await self.websocket.send(full_client_request)

    async def _message_loop(self):
        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    pass
                elif isinstance(message, bytes):
                    res = self.parser_response(message)
                    if res.optional.event == EVENT_ConnectionStarted:
                        self.start_connection_event.set()
                    elif res.optional.event == EVENT_SessionStarted:
                        self.start_session_event.set()
                    elif (
                        res.optional.event == EVENT_TTSResponse
                        and res.header.message_type == AUDIO_ONLY_RESPONSE
                    ):
                        if self.callback:
                            self.callback.on_data(res.payload)
                    elif res.optional.event == EVENT_TTSSentenceStart:
                        pass
                    elif res.optional.event == EVENT_TTSSentenceEnd:
                        self.complete_event.set()
                        if self.callback:
                            self.callback.on_complete()
                    elif res.optional.event in [
                        EVENT_ConnectionFinished,
                        EVENT_SessionFailed,
                    ]:
                        self._is_started = False
                        self._is_stopped = True
                        self.complete_event.set()
                        self.start_connection_event.set()
                        if self.callback:
                            self.callback.on_error(res.response_meta_json)
                    else:
                        if self.callback:
                            self.callback.on_event(res.payload_json)
        except websockets.exceptions.ConnectionClosed:
            self.websocket_task = None
            self.callback.on_close()
        except asyncio.CancelledError:
            self.websocket_task = None
            self.callback.on_close()
        except Exception as e:
            self.websocket_task = None
            self.callback.on_error(e)

    async def __start_task(self):
        if self.callback is None:
            raise Exception("callback is not set")

        if self._is_started:
            raise Exception("TTS is already started")

        try:
            # log_id = self.gen_log_id()
            headers = {
                "X-Api-App-Key": self.app_id,
                "X-Api-Access-Key": self.token,
                "X-Api-Resource-Id": "volc.service_type.10029",
                "X-Api-Connect-Id": str(uuid.uuid4()),
                # "X-Tt-Logid": log_id,
            }
            self.websocket = await websockets.connect(
                self.url,
                additional_headers=headers,
                max_size=1024 * 1024 * 100,
            )
            start_request = await self.request.start_connection()
            await self.__send_event(*start_request)

            self.websocket_task = asyncio.create_task(self._message_loop())

            await asyncio.wait_for(self.start_connection_event.wait(), timeout=5)

            self.session_id = str(uuid.uuid4())
            start_session_request = await self.request.start_session(
                self.speaker, self.session_id
            )
            await self.__send_event(*start_session_request)

            await asyncio.wait_for(self.start_session_event.wait(), timeout=5)

            self._is_started = True
            if self.callback:
                self.callback.on_open()
        except asyncio.TimeoutError:
            raise Exception("TTS is not started")
        except Exception as e:
            self.callback.on_error(e)

    async def __send_text(self, speaker: str, text: str, session_id):
        header = Header(
            message_type=FULL_CLIENT_REQUEST,
            message_type_specific_flags=MsgTypeFlagWithEvent,
            serial_method=JSON,
        ).as_bytes()
        optional = Optional(event=EVENT_TaskRequest, sessionId=session_id).as_bytes()
        payload = self.request.get_payload_bytes(
            event=EVENT_TaskRequest, text=text, speaker=speaker
        )
        return await self.__send_event(header, optional, payload)

    async def __submit_text(self, text: str):
        if not self._is_started:
            raise Exception("TTS is not started")

        if self._is_stopped:
            raise Exception("TTS is stopped")

        await self.__send_text(self.speaker, text, self.session_id)

    async def streaming_call(self, text: str):
        if self._is_first:
            self._is_first = False
            await self.__start_task()

        await self.__submit_text(text)

    async def streaming_complete(self):
        if not self._is_started:
            raise Exception("TTS is not started")

        if self._is_stopped:
            raise Exception("TTS is stopped")

        finish_session_request = await self.request.finish_session(self.session_id)
        await self.__send_event(*finish_session_request)

        finish_connection_request = await self.request.finish_connection()
        await self.__send_event(*finish_connection_request)

        await self.complete_event.wait()

        await self.close()
        self._is_stopped = True
        self._is_started = False

    async def streaming_cancel(self):
        if not self._is_started:
            raise Exception("TTS is not started")

        if self._is_stopped:
            return

        finish_session_request = await self.request.finish_session(self.session_id)
        await self.__send_event(*finish_session_request)

        finish_connection_request = await self.request.finish_connection()
        await self.__send_event(*finish_connection_request)

        await self.close()
        self._is_stopped = True
        self._is_started = False
        self.start_connection_event.set()
        self.complete_event.set()

    async def close(self):
        if self.websocket and self.websocket.state == State.OPEN:
            await self.websocket.close()
        if self.websocket_task:
            self.websocket_task.cancel()
            await self.websocket_task

    def read_res_content(self, res: bytes, offset: int):
        content_size = int.from_bytes(res[offset : offset + 4])
        offset += 4
        content = str(res[offset : offset + content_size], encoding="utf8")
        offset += content_size
        return content, offset

    def read_res_payload(self, res: bytes, offset: int):
        payload_size = int.from_bytes(res[offset : offset + 4])
        offset += 4
        payload = res[offset : offset + payload_size]
        offset += payload_size
        return payload, offset

    def parser_response(self, res) -> Response:
        response = Response(Header(), Optional())
        header = response.header
        num = 0b00001111
        header.protocol_version = res[0] >> 4 & num
        header.header_size = res[0] & 0x0F
        header.message_type = (res[1] >> 4) & num
        header.message_type_specific_flags = res[1] & 0x0F
        header.serialization_method = (res[2] >> 4) & num
        header.message_compression = res[2] & 0x0F
        header.reserved = res[3]

        offset = 4
        optional = response.optional
        if header.message_type in [FULL_SERVER_RESPONSE, AUDIO_ONLY_RESPONSE]:
            if header.message_type_specific_flags == MsgTypeFlagWithEvent:
                optional.event = int.from_bytes(res[offset : offset + 4], "big")
                offset += 4
                if optional.event == EVENT_NONE:
                    return response

                elif optional.event == EVENT_ConnectionStarted:
                    optional.connectionId, offset = self.read_res_content(res, offset)
                elif optional.event == EVENT_ConnectionFailed:
                    optional.response_meta_json, offset = self.read_res_content(
                        res, offset
                    )
                elif (
                    optional.event == EVENT_SessionStarted
                    or optional.event == EVENT_SessionFailed
                    or optional.event == EVENT_SessionFinished
                ):
                    optional.sessionId, offset = self.read_res_content(res, offset)
                    optional.response_meta_json, offset = self.read_res_content(
                        res, offset
                    )
                elif optional.event == EVENT_TTSResponse:
                    optional.sessionId, offset = self.read_res_content(res, offset)
                    response.payload, offset = self.read_res_payload(res, offset)
                elif (
                    optional.event == EVENT_TTSSentenceEnd
                    or optional.event == EVENT_TTSSentenceStart
                ):
                    optional.sessionId, offset = self.read_res_content(res, offset)
                    response.payload_json, offset = self.read_res_content(res, offset)

        elif header.message_type == ERROR_INFORMATION:
            optional.errorCode = int.from_bytes(
                res[offset : offset + 4], "big", signed=True
            )
            offset += 4
            response.payload, offset = self.read_res_payload(res, offset)
        return response
