import os
from dotenv import load_dotenv
import asyncio
from langchain_groq import ChatGroq
from langchain.prompts import (
    SystemMessagePromptTemplate,
    ChatPromptTemplate,
    ChatMessagePromptTemplate,
    HumanMessagePromptTemplate
)

load_dotenv()

class ModelProcessor:
    def __init__(self):
        
        self.llm = ChatGroq(
            model="llama3-70b-8192",
            api_key=os.getenv("Groq_API_KEY"),
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

class AiManager:
    def __init__(self):
        self.llm = ModelProcessor()
    
    async def start(self):
        llm_response = self.llm.process("How are you?")

        print(llm_response)

if __name__ == "__main__":
    manager = AiManager()
    asyncio.run(manager.start())  