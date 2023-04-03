import argparse
import datetime
import queue
import subprocess
import threading

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bilibili_api import live, sync
from transformers import AutoTokenizer, AutoModel

print("=====================================================================")
print("让AI帮你回复弹幕，这样你就可以快乐玩游戏了！")
print("我重写了整个代码，现在她可以异步处理弹幕了，这将大幅降低回复延迟")
print("现在也支持扮演和会话记忆设置，喜欢的话给个三连吧！")
print("ChatGLM-6B：                https://github.com/THUDM/ChatGLM-6B")
print("注意你需要至少6G以上的N卡，另外，我没有也不打算弄粉丝群 by 领航员未鸟")
print("=====================================================================\n")

QuestionList = queue.Queue(10)  # 定义问题 用户名 回复 播放列表 四个先进先出队列
QuestionName = queue.Queue(10)
AnswerList = queue.Queue()
MpvList = queue.Queue()
LogsList = queue.Queue()
history = []
is_ai_ready = True  # 定义chatglm是否转换完成标志
is_tts_ready = True  # 定义语音是否生成完成标志
is_mpv_ready = True  # 定义是否播放完成标志
AudioCount = 0
enable_history = False  # 是否启用记忆
history_count = 4  # 定义最大对话记忆轮数,请注意这个数值不包括扮演设置消耗的轮数，只有当enable_history为True时生效
enable_role = True  # 是否启用扮演模式


def initialize():
    """
    初始化设定
    :return:
    """
    global enable_history
    global history_count
    global enable_role
    parser = argparse.ArgumentParser(description='AI-Vtuber-ChatGLM')
    parser.add_argument('-m', '--memory', help='启用会话记忆', action='store_true')  # 默认为False
    parser.add_argument('-c', '--count', type=int, help='设定记忆轮数，只在启用会话记忆后有效，不指定默认为4', default='4')
    parser.add_argument('-r', '--role', help='启用扮演模式', action='store_true')
    args = parser.parse_args()
    enable_history = args.memory
    enable_role = args.role
    history_count = args.count
    print(f'\n扮演模式启动状态为：{enable_role}')
    if enable_history:
        print(f'会话记忆启动状态为：{enable_history}')
        print(f'会话记忆轮数为：{history_count}\n')
    else:
        print(f'会话记忆启动状态为：{enable_history}\n')


def role_set():
    """
    读取扮演设置
    :return:
    """
    global history
    print("\n开始初始化扮演设定")
    print("请注意：此时会读取并写入Role_setting.txt里的设定，行数越多占用的对话轮数就越多，请根据配置酌情设定\n")
    with open("Role_setting.txt", "r", encoding="utf-8") as f:
        role_setting = f.readlines()
    for setting in role_setting:
        role_response, history = model.chat(tokenizer, setting.strip(), history=history)
        print(f'\033[32m[设定]\033[0m：{setting.strip()}')
        print(f'\033[31m[回复]\033[0m：{role_response}\n')
    return history


initialize()
print("=====================================================================\n")
print(f'开始导入ChatGLM模型\n')
tokenizer = AutoTokenizer.from_pretrained("THUDM/chatglm-6b-int4-qe", cache_dir="./", trust_remote_code=True)  # 导入chatglm 你可以换你喜欢的版本模型
model = AutoModel.from_pretrained("THUDM/chatglm-6b-int4-qe", cache_dir="./", trust_remote_code=True).half().cuda()
model = model.eval()
if enable_role:
    print("\n=====================================================================")
    Role_history = role_set()
else:
    Role_history = []

print("--------------------")
print("启动成功！")
print("--------------------")

room_id = int(input("输入你的直播间编号: "))  # 输入直播间编号
room = live.LiveDanmaku(room_id)  # 连接弹幕服务器

sched1 = AsyncIOScheduler(timezone="Asia/Shanghai")


@room.on('DANMU_MSG')  # 弹幕消息事件回调函数
async def on_danmaku(event):
    """
     处理弹幕消息
    """
    global QuestionList
    global QuestionName
    global LogsList
    content = event["data"]["info"][1]  # 获取弹幕内容
    user_name = event["data"]["info"][2][1]  # 获取用户昵称
    print(f"\033[36m[{user_name}]\033[0m:{content}")  # 打印弹幕信息
    if not QuestionList.full():
        QuestionName.put(user_name)  # 将用户名放入队列
        QuestionList.put(content)  # 将弹幕消息放入队列
        time1 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        LogsList.put(f"[{time1}] [{user_name}]：{content}")
        print('\033[32mSystem>>\033[0m已将该条弹幕添加入问题队列')
    else:
        print('\033[32mSystem>>\033[0m队列已满，该条弹幕被丢弃')


def ai_response():
    """
    从问题队列中提取一条，生成回复并存入回复队列中
    :return:
    """
    global is_ai_ready
    global QuestionList
    global AnswerList
    global QuestionName
    global LogsList
    global history
    prompt = QuestionList.get()
    user_name = QuestionName.get()
    ques = LogsList.get()
    if len(history) >= len(Role_history)+history_count and enable_history:  # 如果启用记忆且达到最大记忆长度
        history = Role_history + history[-history_count:]
        response, history = model.chat(tokenizer, prompt, history=history)
    elif enable_role and not enable_history:                                # 如果没有启用记忆且启用扮演
        history = Role_history
        response, history = model.chat(tokenizer, prompt, history=history)
    elif enable_history:                                                    # 如果启用记忆
        response, history = model.chat(tokenizer, prompt, history=history)
    elif not enable_history:                                                # 如果没有启用记忆
        response, history = model.chat(tokenizer, prompt, history=[])
    else:
        response = ['Error：记忆和扮演配置错误！请检查相关设置']
        print(response)
    answer = f'回复{user_name}：{response}'
    AnswerList.put(answer)
    current_question_count = QuestionList.qsize()
    print(f"\033[31m[ChatGLM]\033[0m{answer}")  # 打印AI回复信息
    print(f'\033[32mSystem>>\033[0m[{user_name}]的回复已存入队列，当前剩余问题数:{current_question_count}')
    time2 = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open("./logs.txt", "a", encoding="utf-8") as f:  # 将问答写入logs
        f.write(f"{ques}\n[{time2}] {answer}\n========================================================\n")
    is_ai_ready = True  # 指示AI已经准备好回复下一个问题


def check_answer():
    """
    如果AI没有在生成回复且队列中还有问题 则创建一个生成的线程
    :return:
    """
    global is_ai_ready
    global QuestionList
    global AnswerList
    if not QuestionList.empty() and is_ai_ready:
        is_ai_ready = False
        answers_thread = threading.Thread(target=ai_response())
        answers_thread.start()


def check_tts():
    """
    如果语音已经放完且队列中还有回复 则创建一个生成并播放TTS的线程
    :return:
    """
    global is_tts_ready
    if not AnswerList.empty() and is_tts_ready:
        is_tts_ready = False
        tts_thread = threading.Thread(target=tts_generate())
        tts_thread.start()


def tts_generate():
    """
    从回复队列中提取一条，通过edge-tts生成语音对应AudioCount编号语音
    :return:
    """
    global is_tts_ready
    global AnswerList
    global MpvList
    global AudioCount
    response = AnswerList.get()
    with open("./output/output.txt", "w", encoding="utf-8") as f:
        f.write(f"{response}")  # 将要读的回复写入临时文件
    subprocess.run(f'edge-tts.exe --voice zh-CN-XiaoyiNeural --f .\output\output.txt --write-media .\output\output{AudioCount}.mp3 2>nul', shell=True)  # 执行命令行指令
    begin_name = response.find('回复')
    end_name = response.find("：")
    name = response[begin_name+2:end_name]
    print(f'\033[32mSystem>>\033[0m对[{name}]的回复已成功转换为语音并缓存为output{AudioCount}.mp3')
    MpvList.put(AudioCount)
    AudioCount += 1
    is_tts_ready = True  # 指示TTS已经准备好回复下一个问题


def check_mpv():
    """
    若mpv已经播放完毕且播放列表中有数据 则创建一个播放音频的线程
    :return:
    """
    global is_mpv_ready
    global MpvList
    if not MpvList.empty() and is_mpv_ready:
        is_mpv_ready = False
        tts_thread = threading.Thread(target=mpv_read())
        tts_thread.start()


def mpv_read():
    """
    按照MpvList内的名单播放音频直到播放完毕
    :return:
    """
    global MpvList
    global is_mpv_ready
    while not MpvList.empty():
        temp1 = MpvList.get()
        current_mpvlist_count = MpvList.qsize()
        print(f'\033[32mSystem>>\033[0m开始播放output{temp1}.mp3，当前待播语音数：{current_mpvlist_count}')
        subprocess.run(f'mpv.exe -vo null .\output\output{temp1}.mp3 1>nul', shell=True)  # 执行命令行指令
        subprocess.run(f'del /f .\output\output{temp1}.mp3 1>nul', shell=True)
    is_mpv_ready = True


def main():
    sched1.add_job(check_answer, 'interval', seconds=1, id=f'answer', max_instances=4)
    sched1.add_job(check_tts, 'interval', seconds=1, id=f'tts', max_instances=4)
    sched1.add_job(check_mpv, 'interval', seconds=1, id=f'mpv', max_instances=4)
    sched1.start()
    sync(room.connect())  # 开始监听弹幕流


if __name__ == '__main__':
    main()
