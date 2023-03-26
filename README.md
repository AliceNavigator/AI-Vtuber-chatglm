# **AI-Vtuber-chatglm**

## **介绍**
- 本地部署chatglm-6b生成并以语音回复你的bilibili直播弹幕 

- Use chatglm-6b to generate and reply your bilibili live danmu with voice

- 重写了整个代码，将接收弹幕，生成回复，生成语音，播放语音全部异步处理，在弹幕多的时候大幅降低响应延迟

### 运行环境
- Python 3.10

 此外你可能需要下载并配置[ChatGLM-6B-INT4-QE](https://huggingface.co/THUDM/chatglm-6b-int4-qe)
 
### 使用
1. 在命令行中运行以下命令启动程序：
```bash
python main-async.py
```

### 许可证
- MIT许可证。详情请参阅LICENSE文件。
