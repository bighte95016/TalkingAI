import os
import shutil
import subprocess
import requests
from dotenv import load_dotenv
import asyncio
from langchain_groq import ChatGroq
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveOptions,
    LiveTranscriptionEvents,
    Microphone
)

load_dotenv()
API_KEY = os.getenv("DEEPGRAM_API_KEY")

class ModelProcessor:
    def __init__(self):
        
        self.llm = ChatGroq(
            model="llama3-70b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.1
        )

        system = SystemMessagePromptTemplate.from_template(
                    """
                        Your name is Emma.
                        That is very important.
                        Your response must be under 20 words.
                    """
                )
        human = HumanMessagePromptTemplate.from_template("{text}")
        
        self.prompt = ChatPromptTemplate.from_messages([
               system,
               human
            ])
        
        self.conversation = self.prompt | self.llm

    def process(self, text):
        
        response = self.conversation.invoke({"text": text})

        return response

class Merge_Transcript:

    def __init__(self):
        self.reset()
    
    def reset(self):
        self.transcipt_parts = []

    def add_new_sentence(self, sentence):
        self.transcipt_parts.append(sentence)

    def get_full_sentence(self):
        return " ".join(self.transcipt_parts)
    
merge_transcript = Merge_Transcript()

class TextToSpeech:
    model = "aura-athena-en"

    @staticmethod
    def is_installed(lib_name: str):
        lib = shutil.which(lib_name)
        return lib is not None

    def speak(self, text):
        if not self.is_installed("ffplay"):
            raise ValueError("ffplay not found. if you need to use stream audio, please install it.")
        
        DEEPGRAM_URL = f"https://api.deepgram.com/v1/speak?model={self.model}"

        headers = {
            "Authorization": f"Token {API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {"text": text}

        player_command = ["ffplay", "-autoexit", "-", '-nodisp']
        player_process = subprocess.Popen(
            player_command,
            stdin = subprocess.PIPE,
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL
        )

        with requests.post(DEEPGRAM_URL, headers=headers, json=payload, stream=True) as request:
            for chunk in request.iter_content(chunk_size=1024):
                if chunk:
                    player_process.stdin.write(chunk)
                    player_process.stdin.flush()

        if player_process.stdin:
            player_process.stdin.close()
        player_process.wait()

tts = TextToSpeech()

async def get_transcript(callback):
    
    transcription_complete = asyncio.Event()

    try:
        dg_config = DeepgramClientOptions(
            options={"keepalive": "true"}
        )

        deepgram = DeepgramClient(
            API_KEY,
            dg_config
        )

        dg_connection = deepgram.listen.asynclive.v("1")
        print("Listening...")

        async def message_on(self, result, **kwargs):
            
            sentence = result.channel.alternatives[0].transcript

            if not result.speech_final:
                merge_transcript.add_new_sentence(sentence)
            else:
                merge_transcript.add_new_sentence(sentence)
                full_sentence = merge_transcript.get_full_sentence()

                if len(full_sentence.strip()) > 0:
                    full_sentence = full_sentence.strip()
                    print(f"Human: {full_sentence}")

                    callback(full_sentence)
                    merge_transcript.reset()
                    transcription_complete.set()

        async def error_on(self, error, **kwargs):
            print(f"\n\n{error}\n\n")

        dg_connection.on(LiveTranscriptionEvents.Transcript, message_on)
        dg_connection.on(LiveTranscriptionEvents.Error, error_on)

        options = LiveOptions(
            model="nova-2",
            language="en-US",
            encoding="linear16",
            channels=1,
            sample_rate=16000,
            smart_format=True,
            endpointing=380
        )

        await dg_connection.start(options)

        microphone = Microphone(dg_connection.send)
        microphone.start()

        # while True: 
        #     if not microphone.is_active():
        #         break
        #     await asyncio.sleep(5)
        await transcription_complete.wait()
        
        microphone.finish()
        await dg_connection.finish()

        print("Finished.")

        
    except Exception as error:
        print(f"Could not open web socket: {error}")
        return
        
class AiManager:
    def __init__(self):
        self.transcription_response = ""
        self.llm = ModelProcessor()

    async def start(self):
        def handle_full_sentence(full_sentence):
            self.transcription_response = full_sentence

        while True:
            await get_transcript(handle_full_sentence)

            if "goodbye" in self.transcription_response.lower():
                break

            llm_response = self.llm.process(self.transcription_response)

            # print(llm_response.content)
            tts.speak(llm_response.content)

            self.transcription_response = ""


if __name__ == "__main__":
    manager = AiManager()
    asyncio.run(manager.start())