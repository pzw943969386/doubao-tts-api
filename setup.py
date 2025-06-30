from setuptools import setup, find_packages

setup(
    name="doubao-tts-api",
    version="0.1.0",
    description="豆包语音合成 API，基于字节跳动 TTS WebSocket",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="pzw",
    author_email="943969386@qq.com",
    url="https://github.com/pzw943969386/doubao-tts-api",  # 可选
    packages=find_packages(),
    install_requires=[
        "websockets",
        "numpy",
        "sounddevice",
        "fastrand"
    ],
    python_requires=">=3.8",
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)