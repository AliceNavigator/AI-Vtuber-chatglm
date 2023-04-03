# **AI-Vtuber-chatglm**

## **介绍**
- 本地部署chatglm-6b生成并以语音回复你的bilibili直播弹幕 

- Use chatglm-6b to generate and reply your bilibili live danmu with voice

- 重写了整个代码，将接收弹幕，生成回复，生成语音，播放语音全部异步处理，在弹幕多的时候大幅降低响应延迟

- 增加了记忆模式和扮演模式，可用命令行传参

### 运行环境
- Python 3.10

 此外你需要先按照[ChatGLM-6B](https://github.com/THUDM/ChatGLM-6B)配置环境
 
### 使用
1. 运行以下命令启动程序：
```bash
pip install -r requirements.txt
python main-async.py
```

- 此外，现在已经支持一些可选参数如下

-  -m, --memory :启用记忆模式，默认会记住最新的4轮问答
-  -c, --count  :指定记忆的轮数
-  -r, --role   :启用扮演模式，会从根目录下的Role_setting.txt中读取设定并逐行写入

- 示例：
```bash
python main-async.py -r -m -c 20
```


### 许可证
- MIT许可证。详情请参阅LICENSE文件。
