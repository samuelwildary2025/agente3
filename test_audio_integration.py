#!/usr/bin/env python3
"""
Teste de integração do sistema de áudio
"""
import asyncio
import json
from datetime import datetime
from tools.audio_tools import (
    is_audio_message,
    process_audio_message,
    download_audio_file,
    get_audio_info,
    transcribe_audio_openai
)
from config.logger import setup_logger

logger = setup_logger(__name__)

def test_audio_detection():
    """Testa detecção de mensagens de áudio"""
    print("🎤 Testando detecção de mensagens de áudio...")
    
    # Testes de tipos de áudio
    test_cases = [
        ("audio", True),
        ("audioMessage", True),
        ("ptt", True),
        ("voice", True),
        ("text", False),
        ("image", False),
        ("video", False),
    ]
    
    for message_type, expected in test_cases:
        result = is_audio_message(message_type)
        status = "✅" if result == expected else "❌"
        print(f"{status} {message_type}: {result} (esperado: {expected})")
    
    # Teste com content-type
    print("\n🎤 Testando com content-type:")
    content_type_tests = [
        ("audio/mp3", True),
        ("audio/ogg", True),
        ("audio/wav", True),
        ("audio/mpeg", True),
        ("text/plain", False),
        ("image/jpeg", False),
    ]
    
    for content_type, expected in content_type_tests:
        result = is_audio_message("", content_type)
        status = "✅" if result == expected else "❌"
        print(f"{status} {content_type}: {result} (esperado: {expected})")

def test_webhook_normalization():
    """Testa normalização de webhooks com áudio"""
    print("\n📱 Testando normalização de webhooks...")
    
    # Simular webhook UAZ
    uaz_payload = {
        "messages": [{
            "sender": "5511987654321@s.whatsapp.net",
            "type": "audioMessage",
            "content": {
                "type": "audio",
                "url": "https://example.com/audio.ogg"
            }
        }]
    }
    
    # Simular webhook Cloud API
    cloud_api_payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "5511987654321",
                        "type": "audio",
                        "audio": {
                            "id": "audio123"
                        }
                    }],
                    "contacts": [{
                        "wa_id": "5511987654321"
                    }]
                }
            }]
        }]
    }
    
    # Importar função do servidor
    import sys
    sys.path.append('.')
    from server import _extract_incoming
    
    print("Testando UAZ webhook:")
    result = _extract_incoming(uaz_payload)
    print(f"Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    print("\nTestando Cloud API webhook:")
    result = _extract_incoming(cloud_api_payload)
    print(f"Resultado: {json.dumps(result, indent=2, ensure_ascii=False)}")

def test_audio_formats():
    """Testa suporte a diferentes formatos de áudio"""
    print("\n🎵 Testando formatos de áudio suportados...")
    
    from tools.audio_tools import SUPPORTED_AUDIO_FORMATS, SUPPORTED_EXTENSIONS
    
    print("Formatos MIME suportados:")
    for mime_type, extension in SUPPORTED_AUDIO_FORMATS.items():
        print(f"  {mime_type} → {extension}")
    
    print(f"\nExtensões suportadas: {', '.join(SUPPORTED_EXTENSIONS)}")

def test_mock_audio_processing():
    """Testa processamento de áudio com mock"""
    print("\n🔄 Testando processamento de áudio (mock)...")
    
    # Testar com URL mock (vai falhar no download, mas testa o fluxo)
    mock_url = "https://example.com/test-audio.ogg"
    mock_api_key = "sk-test-key"
    
    try:
        result = process_audio_message(mock_url, mock_api_key)
        print(f"Resultado do processamento: {json.dumps(result, indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"Erro esperado (mock): {e}")

def test_agent_integration():
    """Testa integração com o agente"""
    print("\n🤖 Testando integração com agente...")
    
    try:
        from agent_langgraph_simple import audio_info_tool, historico_tool
        
        print("Testando audio_info_tool:")
        audio_info = audio_info_tool()
        print(audio_info)
        
        print("\nTestando historico_tool:")
        hist_info = historico_tool()
        print(hist_info)
        
    except Exception as e:
        print(f"Erro na integração: {e}")

def main():
    """Executa todos os testes"""
    print("🚀 Iniciando testes de integração de áudio")
    print("=" * 50)
    
    test_audio_detection()
    test_webhook_normalization()
    test_audio_formats()
    test_mock_audio_processing()
    test_agent_integration()
    
    print("\n" + "=" * 50)
    print("✅ Testes de integração de áudio concluídos!")
    print("\n📋 Resumo do sistema implementado:")
    print("• Detecção automática de mensagens de áudio")
    print("• Extração de URLs de áudio de diferentes webhooks")
    print("• Suporte a múltiplos formatos de áudio (MP3, OGG, WAV, M4A, OPUS)")
    print("• Transcrição com OpenAI Whisper")
    print("• Integração com agente LangGraph")
    print("• Ferramentas de áudio e histórico temporal")
    print("• Processamento assíncrono em background")

if __name__ == "__main__":
    main()