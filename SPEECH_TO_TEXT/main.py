import os 
import asyncio
from dotenv import load_dotenv

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone
)

load_dotenv()

API_KEY = os.getenv("DEEPGRAM_API_KEY")

class Merge_Transcript:
    def reset(self):
        self.trancript_parts = []

    def __init__(self):
        self.reset()
    
    def add_new_sentence(self, sentence):
        self.trancript_parts.append(sentence)

    def get_full_sentence(self):
        return "，".join(self.trancript_parts)
    
merge_transcript = Merge_Transcript()


async def get_transcript():

    try:
        dg_config = DeepgramClientOptions(
            options={
                "keepalive": "true"      #避免一直跳出連線失敗
            }
        )

        deepgram = DeepgramClient(API_KEY, dg_config)

        dg_connection = deepgram.listen.asynclive.v("1")


        async def message_on(self, result, **kwargs):   #非同步執行
            sentence = result.channel.alternatives[0].transcript
            print(sentence)

            if not result.speech_final:    #談話尚未完成
                merge_transcript.add_new_sentence(sentence)
            else:                          #談話已完成
                merge_transcript.add_new_sentence(sentence)
                full_sentence = merge_transcript.get_full_sentence()
                print(f"speaker: {full_sentence}")

                merge_transcript.reset()     #結束後重設


        async def error_on(self, error, **kwargs):     #非同步執行
            print(f"\n\n{error}\n\n")

        dg_connection.on(LiveTranscriptionEvents.Transcript, message_on)
        dg_connection.on(LiveTranscriptionEvents.Error, error_on)


        options = LiveOptions(
            model="nova-2",
            language="zh-TW",
            #language="en-US",
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            smart_format=True,    #可較精準分段、區分數字、停頓
            endpointing=380      #停頓500ms，先將資料送出
        )

        await dg_connection.start(options)

        microphone = Microphone(dg_connection.send)

        microphone.start()

        while True:
            if not microphone.is_active():
                break
            await asyncio.sleep(1)  #睡1秒

        microphone.finish()

        dg_connection.finish()

        print("Finished")

    except Exception as error:
        print(f"Failed to connected: {error}")
        return


#程式運行即進行轉譯
if __name__ == "__main__":
    asyncio.run(get_transcript())