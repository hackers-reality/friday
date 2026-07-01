import os, sys, asyncio
sys.path.insert(0, 'E:/open-interpreter')
from dotenv import load_dotenv
load_dotenv('.env')

from google import genai
from google.genai import types

API_KEY = os.environ['GOOGLE_API_KEY']
MODEL = os.getenv('GEMINI_LIVE_MODEL', 'gemini-3.1-flash-live-preview')

async def test():
    client = genai.Client(api_key=API_KEY, http_options={'api_version': 'v1alpha'})
    config = types.LiveConnectConfig(
        response_modalities=['AUDIO'],
        system_instruction=types.Content(
            parts=[types.Part(text='You are FRIDAY. Speak concisely.')]
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Leda')
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )
    print('Connecting...', flush=True)
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print('Connected! Sending...', flush=True)
        await session.send(input='Say hi to Rohit in one short sentence', end_of_turn=True)
        texts = []
        try:
            async for msg in asyncio.wait_for(session.receive(), timeout=10):
                if msg.text:
                    texts.append(msg.text)
                    print(f'TEXT: {msg.text}', flush=True)
        except asyncio.TimeoutError:
            pass
        if texts:
            full = ''.join(texts)
            print(f'FULL TRANSCRIPTION: {full}', flush=True)
        else:
            print('No text received via msg.text', flush=True)

asyncio.run(test())
