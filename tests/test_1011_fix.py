"""Test that the full SYSTEM_INSTRUCTION + tools works without 1011."""
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
    from friday.live import SYSTEM_INSTRUCTION, _build_full_system_text, _build_tool_reference, _build_tools

    full_text = _build_full_system_text()
    tool_ref = _build_tool_reference()

    # Step 1: connect with minimal config
    config = types.LiveConnectConfig(
        response_modalities=['AUDIO'],
        system_instruction=types.Content(
            parts=[types.Part(text='You are FRIDAY, a sovereign AI assistant. Full instructions follow.')]
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Leda')
            )
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )
    print(f'Step 1: Connecting with minimal config...', flush=True)
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        print(f'Step 1: CONNECTED!', flush=True)

        # Step 2: inject full system + tools
        print(f'Step 2: Injecting full system ({len(full_text)} chars)...', flush=True)
        await session.send_realtime_input(
            text=f'[FULL SYSTEM CONTEXT]\n{full_text}\n\n{tool_ref}'
        )
        print(f'Step 2: Injected!', flush=True)

        # Step 3: ask a question
        print(f'Step 3: Sending question...', flush=True)
        await session.send_realtime_input(text='Say hello to Rohit in one short sentence')
        texts = []
        async for msg in session.receive():
            if msg.text:
                texts.append(msg.text)
                print(f'RESPONSE: {msg.text}', flush=True)
                break
        print(f'Step 3: GOT RESPONSE!', flush=True)

    print(f'TEST PASSED - no 1011 error', flush=True)

asyncio.run(test())
