#!/usr/bin/env python3
"""
Teste de extração de áudio do webhook UAZ
"""

import json

# Payload real que você recebeu
payload = {
    'BaseUrl': ' `https://wildhub.uazapi.com` ',
    'EventType': 'messages',
    'chat': {
        'chatbot_agentResetMemoryAt': 0,
        'chatbot_disableUntil': 0,
        'chatbot_lastTriggerAt': 0,
        'chatbot_lastTrigger_id': '',
        'id': 'r51220bca3c378b',
        'image': '',
        'imagePreview': ' `https://pps.whatsapp.net/v/t61.24694-24/553729438_1120474096355299_7270513533649740356_n.jpg?stp=dst-jpg_s96x96_tt6&ccb=11-4&oh=01_Q5Aa3AFadSVqyOePC4l1m4ZBIGNGhirjWX4jDylxRCxKAdV9Zg&oe=6922F138&_nc_sid=5e03e0&_nc_cat=110` ',
        'wa_lastMessageType': 'AudioMessage',
        'wa_lastMsgTimestamp': 1763392439000,
    },
    'instanceName': 'teste',
    'message': {
        'chatid': '558587520060@s.whatsapp.net',
        'content': {
            'URL': ' `https://mmg.whatsapp.net/v/t62.7117-24/584323793_1160838339488809_8107292549655175983_n.enc?ccb=11-4&oh=01_Q5Aa3AGs8cnK-16SZaGY-eK2LGaIC_M0t2ugp4UP_KgKfBlrQQ&oe=69429AA5&_nc_sid=5e03e0&mms3=true` ',
            'mimetype': 'audio/ogg; codecs=opus',
            'fileSHA256': 'v+gXLVu9GlmyLZBALOnBCQEdWr/M1ZtaMkcdyYyh2bo=',
            'fileLength': 9532,
            'seconds': 4,
            'PTT': True,
            'mediaKey': 'YFulTthzu0+IS7a+srw0SQlG1wE/KYegpkdpOVlra5A=',
            'fileEncSHA256': 'gNgAqRE3NvlVkWklonbLGn1ptSMiks5Y9wO7VNdgkOI=',
            'directPath': '/v/t62.7117-24/584323793_1160838339488809_8107292549655175983_n.enc?ccb=11-4&oh=01_Q5Aa3AGs8cnK-16SZaGY-eK2LGaIC_M0t2ugp4UP_KgKfBlrQQ&oe=69429AA5&_nc_sid=5e03e0',
            'mediaKeyTimestamp': 1763392436,
            'waveform': 'AA0oOS4sKiw3N1ZeXlxZS1VgWFdNVVdcXVtNQDI4PDg8NTI4NDA0Ny8xVVxbWVxdW1c2MikqKzMwMy8sKi8dAA=='
        },
        'fromMe': False,
        'messageType': 'AudioMessage',
        'messageid': 'ACD375D44C430F013ED556D342540603',
        'sender': '558587520060@s.whatsapp.net',
        'type': 'media'
    },
    'owner': '5585920002076',
    'token': 'c253a5fe-131b-4ab1-bd2a-62f812bc8856'
}

# Simular a função _extract_incoming ATUALIZADA
def _extract_incoming_test(payload):
    """Versão de teste da função de extração - igual ao server.py atualizado"""
    try:
        # 0) Estrutura UAZ Webhook direta (payload tem 'message' direto)
        m0 = payload.get("message", {})
        content = m0.get("content", {})

        # telefone pode vir em 'sender' ou 'chatid' (ex.: "5585987520060@s.whatsapp.net")
        telefone = m0.get("sender") or m0.get("chatid") or m0.get("from")
        if isinstance(telefone, str):
            import re
            telefone = re.sub(r"\D", "", telefone.split("@")[0])

        message_type = content.get("type") or m0.get("type") or m0.get("messageType") or "text"
        
        # Verificação adicional: se wa_lastMessageType indicar áudio, usar isso
        chat_data = payload.get("chat", {})
        wa_last_type = chat_data.get("wa_lastMessageType")
        if wa_last_type == "AudioMessage" and message_type == "media":
            message_type = "audioMessage"
            
        mensagem_texto = content.get("text") or m0.get("text")
        
        # Para mensagens de áudio, definir um texto placeholder se não houver texto
        if not mensagem_texto and message_type in ["audio", "audioMessage", "ptt", "voice"]:
            mensagem_texto = "[Áudio recebido - aguardando transcrição]"
            
        message_id = m0.get("messageid") or m0.get("id")
        from_me = bool(m0.get("fromMe") or m0.get("wasSentByApi") or False)
        
        # Extrair URL de áudio - nova estrutura detectada
        audio_url = None
        if message_type in ["audio", "audioMessage", "ptt", "voice"]:
            # Tentar diferentes campos para URL de áudio
            audio_url = (
                content.get("URL") or  # Nova estrutura: content.URL
                content.get("url") or 
                m0.get("url") or 
                content.get("mediaUrl") or 
                m0.get("mediaUrl")
            )
            
            # Se não encontrar URL direta, usar o messageid como referência para download
            if not audio_url and message_id:
                audio_url = message_id

        if telefone:
            return {
                "telefone": telefone,
                "mensagem_texto": mensagem_texto,
                "message_type": message_type,
                "message_id": message_id,
                "from_me": from_me,
                "audio_url": audio_url,
            }
    except Exception as e:
        print(f"Erro na extração: {e}")
        import traceback
        traceback.print_exc()
        
    return None

# Testar extração
resultado = _extract_incoming_test(payload)
print("=== RESULTADO DA EXTRAÇÃO ===")
if resultado:
    print(f"Telefone: {resultado['telefone']}")
    print(f"Message Type: {resultado['message_type']}")
    print(f"Message ID: {resultado['message_id']}")
    print(f"Audio URL: {resultado['audio_url']}")
    print(f"Texto: {resultado['mensagem_texto']}")
    print(f"From Me: {resultado['from_me']}")
else:
    print("Falha na extração")

# Testar detecção de áudio
def is_audio_message(message_type):
    return message_type in ["audio", "audioMessage", "ptt", "voice"]

if resultado:
    print(f"\n=== DETECÇÃO DE ÁUDIO ===")
    print(f"É áudio? {is_audio_message(resultado['message_type'])}")
    print(f"Tipo detectado: {resultado['message_type']}")