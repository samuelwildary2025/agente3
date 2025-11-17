"""
Servidor FastAPI para receber mensagens do WhatsApp e processar com o agente
# touch: reload marker
"""
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import requests
from datetime import datetime
import time
import threading

from config.settings import settings
from config.logger import setup_logger
from agent_langgraph_simple import run_agent_langgraph as run_agent, get_session_history
from tools.redis_tools import (
    push_message_to_buffer,
    get_buffer_length,
    pop_all_messages,
    set_agent_cooldown,
    is_agent_in_cooldown,
)
from tools.audio_tools import (
    process_audio_message,
    download_audio_file,
    is_audio_message,
)

logger = setup_logger(__name__)

# ============================================
# Inicialização do FastAPI
# ============================================

app = FastAPI(
    title="Agente de Supermercado",
    description="API para atendimento automatizado via WhatsApp",
    version="1.0.0"
)


# ============================================
# Modelos de Dados
# ============================================

class WhatsAppMessage(BaseModel):
    """Modelo de mensagem recebida do WhatsApp"""
    telefone: str = Field(..., description="Número de telefone do cliente")
    mensagem: str = Field(..., description="Texto da mensagem")
    message_id: Optional[str] = Field(None, description="ID da mensagem")
    timestamp: Optional[str] = Field(None, description="Timestamp da mensagem")
    message_type: Optional[str] = Field("text", description="Tipo de mensagem (text, audio, image)")


class AgentResponse(BaseModel):
    """Modelo de resposta do agente"""
    success: bool
    response: str
    telefone: str
    timestamp: str
    error: Optional[str] = None


class PresenceRequest(BaseModel):
    """Modelo para atualização de presença"""
    number: str = Field(..., description="Número no formato internacional, ex: 5511999999999")
    presence: str = Field(..., description="Tipo de presença: composing, recording, paused")
    delay: Optional[int] = Field(None, description="Duração em ms (máx 300000). Reenvio a cada 10s")


# ============================================
# Funções Auxiliares
# ============================================

def _extract_incoming(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza payloads de diferentes provedores (UAZ/Cloud API) para um formato comum.
    Retorna dict com: telefone, mensagem_texto, message_type, message_id, from_me (bool), audio_url (opcional).
    """
    # 0) Estrutura UAZ Webhook direta (payload tem 'message' direto)
    try:
        m0 = payload.get("message", {})
        content = m0.get("content", {})

        # telefone pode vir em 'sender' ou 'chatid' (ex.: "5585987520060@s.whatsapp.net")
        telefone = m0.get("sender") or m0.get("chatid") or m0.get("from")
        if isinstance(telefone, str):
            # extrair apenas dígitos; remover sufixos como "@s.whatsapp.net"
            import re
            telefone = re.sub(r"\D", "", telefone.split("@")[0])

        message_type = content.get("type") or m0.get("type") or m0.get("messageType") or "text"
        
        # Verificação adicional: se wa_lastMessageType indicar áudio, usar isso
        chat_data = payload.get("chat", {})
        wa_last_type = chat_data.get("wa_lastMessageType")
        if wa_last_type == "AudioMessage" and message_type == "media":
            message_type = "audioMessage"
            
        mensagem_texto = content.get("text") or m0.get("text")
        
        # Para mensagens de áudio, definir um texto placeholder se não houver texto ou se for vazio
        if (not mensagem_texto or mensagem_texto.strip() == '') and message_type in ["audio", "audioMessage", "ptt", "voice"]:
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
    except Exception:
        pass
    # 1) Estrutura UAZ específica (body.message/chat/data/token)
    try:
        body = payload.get("body", {})
        message = body.get("message", {})
        chat = body.get("chat", {})
        data = body.get("data", {})

        telefone = chat.get("wa_id") or message.get("from")
        message_type = data.get("messageType") or message.get("type") or "textMessage"
        from_me = bool(message.get("fromMe") or message.get("wasSentByApi") or False)

        mensagem_texto = None
        # Tentativas de extração de texto
        if message_type in ("textMessage", "text", "txt"):
            mensagem_texto = (message.get("text") or {}).get("body") or message.get("body")
        elif message_type in ("imageMessage", "image"):
            mensagem_texto = message.get("image", {}).get("caption", "[Imagem recebida]")
        elif message_type in ("audioMessage", "audio"):
            mensagem_texto = "[Mensagem de áudio recebida - transcrição não implementada]"

        message_id = message.get("messageid") or message.get("id")
        
        # Extrair URL de áudio - para UAZ API, o messageid é usado como identificador
        audio_url = None
        if message_type in ["audioMessage", "audio", "ptt", "voice"]:
            # Para UAZ API, o messageid é o identificador do áudio
            audio_url = message.get("messageid") or message.get("id") or message.get("url") or message.get("mediaUrl")
            
            # Se não tiver URL direta, usar o messageid como referência
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
    except Exception:
        pass

    # 2) Estrutura WhatsApp Cloud API oficial (entry -> changes -> value)
    try:
        entry = payload.get("entry", [])
        if entry:
            changes = entry[0].get("changes", [])
            value = changes[0].get("value", {}) if changes else {}
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])
            msg = messages[0] if messages else {}

            telefone = (contacts[0].get("wa_id") if contacts else None) or msg.get("from")
            message_type = msg.get("type") or "text"
            mensagem_texto = None

            if message_type == "text":
                mensagem_texto = (msg.get("text") or {}).get("body")
            elif message_type == "image":
                mensagem_texto = (msg.get("image") or {}).get("caption", "[Imagem recebida]")
            elif message_type == "audio":
                mensagem_texto = "[Mensagem de áudio recebida - transcrição não implementada]"

            # Extrair URL de áudio
            audio_url = None
            if message_type == "audio":
                audio_data = msg.get("audio", {})
                audio_url = audio_data.get("id")  # Cloud API usa ID que precisa ser resolvido posteriormente

            return {
                "telefone": telefone,
                "mensagem_texto": mensagem_texto,
                "message_type": message_type,
                "message_id": msg.get("id"),
                "from_me": False,
                "audio_url": audio_url,
            }
    except Exception:
        pass

    # 3) Fallback robusto para formato UAZ com campos de topo (message/chat)
    import re

    def _sanitize_phone(raw: Any) -> Optional[str]:
        if raw is None:
            return None
        s = str(raw)
        # remover sufixo do domínio do WhatsApp
        if "@" in s:
            s = s.split("@")[0]
        # em wa_fastid, o formato é "owner:phone" -> pegar a parte de phone
        if ":" in s:
            parts = s.split(":")
            s = parts[-1]
        digits = re.sub(r"\D", "", s)
        return digits or None

    chat = payload.get("chat") or {}
    message_any = payload.get("message")
    from_me = False

    # message/text/type/id defaults
    mensagem_texto = payload.get("text")
    message_type = payload.get("messageType") or "text"
    message_id = payload.get("id") or payload.get("messageid")

    # Extração do texto e tipo a partir de message_any
    if isinstance(message_any, dict):
        message_type = message_any.get("type") or message_type

        # content pode ser string ou dict
        content = message_any.get("content")
        if isinstance(content, str) and not mensagem_texto:
            mensagem_texto = content
        elif isinstance(content, dict):
            mensagem_texto = content.get("text") or mensagem_texto
            message_type = content.get("type") or message_type

        # Campo text pode ser string ou dict { body: "..." }
        txt = message_any.get("text")
        if mensagem_texto is None:
            if isinstance(txt, dict):
                mensagem_texto = txt.get("body")
            else:
                mensagem_texto = txt or message_any.get("body")

        # ID da mensagem
        message_id = message_any.get("messageid") or message_any.get("id") or message_id
        # Flag de self-message
        from_me = bool(message_any.get("fromMe") or message_any.get("wasSentByApi") or False)

    # Extração do telefone a partir de múltiplas fontes
    # Se for uma mensagem enviada pelo agente (from_me=True), priorizamos o número do CLIENTE (chat.wa_id)
    # para que a memória de conversação use sempre o mesmo session_id do cliente.
    if from_me:
        telefone_candidates = [
            chat.get("wa_id"),
            chat.get("phone"),
            chat.get("wa_chatid"),
            chat.get("wa_fastid"),
            payload.get("wa_id"),
            payload.get("sender"),
            payload.get("chatid"),
            payload.get("from"),  # último: número do agente
        ]
        if isinstance(message_any, dict):
            telefone_candidates.extend([
                message_any.get("sender"),
                message_any.get("sender_pn"),
                message_any.get("chatid"),
                message_any.get("from"),
            ])
    else:
        telefone_candidates = [
            payload.get("from"),
            payload.get("wa_id"),
            payload.get("sender"),
            payload.get("chatid"),
            chat.get("phone"),
            chat.get("wa_chatid"),
            chat.get("wa_fastid"),
        ]
        if isinstance(message_any, dict):
            telefone_candidates.extend([
                message_any.get("sender"),
                message_any.get("sender_pn"),
                message_any.get("chatid"),
                message_any.get("from"),
            ])

    telefone: Optional[str] = None
    for cand in telefone_candidates:
        cand_digits = _sanitize_phone(cand)
        if cand_digits:
            telefone = cand_digits
            break

    # Tipo de mídia padrão para texto
    if message_type in (None, "", "textMessage"):
        message_type = "text"

    # Ajuste de mensagens de mídia
    audio_url = None
    if isinstance(message_any, dict):
        if message_type in ("imageMessage", "image") and not mensagem_texto:
            img = message_any.get("image")
            if isinstance(img, dict):
                mensagem_texto = img.get("caption") or "[Imagem recebida]"
            else:
                mensagem_texto = "[Imagem recebida]"
        elif message_type in ("audioMessage", "audio") and (not mensagem_texto or mensagem_texto.strip() == ''):
            mensagem_texto = "[Mensagem de áudio recebida - transcrição não implementada]"
            # Extrair URL de áudio
            audio_data = message_any.get("audio", {})
            audio_url = audio_data.get("url") or audio_data.get("mediaUrl") or message_any.get("url") or message_any.get("mediaUrl")

    return {
        "telefone": telefone,
        "mensagem_texto": mensagem_texto,
        "message_type": message_type,
        "message_id": message_id,
        "from_me": from_me,
        "audio_url": audio_url,
    }

def send_whatsapp_message(telefone: str, mensagem: str) -> bool:
    """
    Envia mensagem de resposta para o WhatsApp via API UAZ
    
    Args:
        telefone: Número de telefone do destinatário
        mensagem: Texto da mensagem a enviar
    
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    # Construção flexível do endpoint
    # Se `WHATSAPP_API_URL` já inclui um caminho além do domínio, usa-o como endpoint completo.
    # Caso contrário, usa o padrão `/message/send`.
    base = (settings.whatsapp_api_url or "").rstrip("/")
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base)
        # Se não há caminho definido ("" ou "/"), acrescenta o caminho padrão
        if not parsed.path or parsed.path == "/":
            url = f"{base}/message/send"
        else:
            # Já é um endpoint completo (com caminho), usar como está
            url = base
    except Exception:
        # Fallback simples se parsing falhar
        url = f"{base}/message/send"
    
    # Alguns provedores aceitam 'token' como header próprio, outros exigem Bearer
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        # UAZ API: endpoints regulares usam apenas header 'token'
        "token": (settings.whatsapp_token or "").strip(),
    }
    
    # Dividir mensagem em partes se for muito longa (limite do WhatsApp: ~4096 caracteres)
    max_length = 4000
    mensagens = []
    
    if len(mensagem) > max_length:
        # Dividir por parágrafos
        paragrafos = mensagem.split('\n\n')
        mensagem_atual = ""
        
        for paragrafo in paragrafos:
            if len(mensagem_atual) + len(paragrafo) + 2 <= max_length:
                mensagem_atual += paragrafo + "\n\n"
            else:
                if mensagem_atual:
                    mensagens.append(mensagem_atual.strip())
                mensagem_atual = paragrafo + "\n\n"
        
        if mensagem_atual:
            mensagens.append(mensagem_atual.strip())
    else:
        mensagens = [mensagem]
    
    # Enviar cada parte
    try:
        for i, msg in enumerate(mensagens):
            # Determinar formato de payload com base no endpoint
            from urllib.parse import urlparse
            import re
            parsed_url = urlparse(url)
            use_number_text = parsed_url.path.endswith("/send/text")
            numero_sanitizado = re.sub(r"\D", "", telefone or "")

            payload_main = {"number": numero_sanitizado, "text": msg} if use_number_text else {"phone": telefone, "message": msg}
            payload_alt = {"phone": telefone, "message": msg} if use_number_text else {"number": numero_sanitizado, "text": msg}
            
            method = getattr(settings, "whatsapp_method", "POST").upper()
            # Log suave do token para depuração (parcialmente mascarado)
            try:
                tok = (settings.whatsapp_token or "").strip()
                masked = (tok[:8] + "..." + tok[-4:]) if tok else "<vazio>"
                logger.info(f"Auth UAZ token (masked): {masked} len={len(tok)}")
            except Exception:
                pass

            if method == "GET":
                logger.info(f"Enviando para UAZ API (GET): url={url} params={payload_main}")
                response = requests.get(url, headers=headers, params=payload_main, timeout=10)
                preview_body = (response.text or "")[:800]
                logger.info(f"UAZ API retorno (GET): status={response.status_code} body={preview_body}")
            else:
                logger.info(f"Enviando para UAZ API (POST): url={url} payload={payload_main}")
                response = requests.post(url, headers=headers, json=payload_main, timeout=10)
                preview_body = (response.text or "")[:800]
                logger.info(f"UAZ API retorno (POST): status={response.status_code} body={preview_body}")

            # Fallback em payload dentro do mesmo método
            if response.status_code >= 400:
                if method == "GET":
                    logger.warning(f"GET falhou com status {response.status_code}. Tentando GET com payload alternativo.")
                    response = requests.get(url, headers=headers, params=payload_alt, timeout=10)
                    preview_body = (response.text or "")[:800]
                    logger.info(f"UAZ API retorno (GET alt): status={response.status_code} body={preview_body}")
                else:
                    logger.warning(f"POST falhou com status {response.status_code}. Tentando POST com payload alternativo.")
                    response = requests.post(url, headers=headers, json=payload_alt, timeout=10)
                    preview_body = (response.text or "")[:800]
                    logger.info(f"UAZ API retorno (POST alt): status={response.status_code} body={preview_body}")

            # Fallback automático de método (trocar POST/GET) usando payload principal
            if response.status_code >= 400:
                if method == "POST":
                    logger.warning(f"POST ainda falhou com status {response.status_code}. Tentando GET com payload principal.")
                    response = requests.get(url, headers=headers, params=payload_main, timeout=10)
                    preview_body = (response.text or "")[:800]
                    logger.info(f"UAZ API retorno (GET): status={response.status_code} body={preview_body}")
                else:
                    logger.warning(f"GET ainda falhou com status {response.status_code}. Tentando POST com payload principal.")
                    response = requests.post(url, headers=headers, json=payload_main, timeout=10)
                    preview_body = (response.text or "")[:800]
                    logger.info(f"UAZ API retorno (POST): status={response.status_code} body={preview_body}")

            # Último fallback: método alternativo com payload alternativo
            if response.status_code >= 400:
                if method == "POST":
                    logger.warning(f"GET com payload principal falhou. Tentando GET com payload alternativo.")
                    response = requests.get(url, headers=headers, params=payload_alt, timeout=10)
                    preview_body = (response.text or "")[:800]
                    logger.info(f"UAZ API retorno (GET alt): status={response.status_code} body={preview_body}")
                else:
                    logger.warning(f"POST com payload principal falhou. Tentando POST com payload alternativo.")
                    response = requests.post(url, headers=headers, json=payload_alt, timeout=10)
                    preview_body = (response.text or "")[:800]
                    logger.info(f"UAZ API retorno (POST alt): status={response.status_code} body={preview_body}")
                params = {"phone": telefone, "message": msg}
                # Alguns provedores esperam token no query; manter no header por segurança
                response_get = requests.get(url, headers=headers, params=params, timeout=10)
                preview_body_get = (response_get.text or "")[:800]
                logger.info(
                    f"UAZ API retorno (GET): status={response_get.status_code} body={preview_body_get}"
                )
                response_get.raise_for_status()
            
            logger.info(f"Mensagem {i+1}/{len(mensagens)} enviada para {telefone}")
        
        return True
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar mensagem para WhatsApp: {e}")
        return False


# ============================================
# Presença (digitando/gravação/pausa)
# ============================================

# Controle simples de sessões de presença por número
presence_sessions: Dict[str, Dict[str, Any]] = {}
# Buffer de mensagens por telefone (evita múltiplos agregadores simultâneos)
buffer_sessions: Dict[str, Dict[str, Any]] = {}


def _sanitize_number(num: Optional[str]) -> Optional[str]:
    if not num:
        return None
    import re
    s = str(num)
    if "@" in s:
        s = s.split("@")[0]
    if ":" in s:
        s = s.split(":")[-1]
    digits = re.sub(r"\D", "", s)
    return digits or None


def send_presence_signal(number: str, presence: str) -> bool:
    """
    Envia um único sinal de presença para a UAZ com fallbacks.
    presence: composing | recording | paused
    """
    base = (settings.whatsapp_api_url or "").rstrip("/")
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base)
        # Usar apenas domínio para presença; caminho de mensagem (ex.: /send/text) não serve
        base_domain = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else base
        # Priorizar o endpoint que comprovadamente retorna 200 na UAZ
        url_candidates = [
            f"{base_domain}/message/presence",
            f"{base_domain}/presence/send",
            f"{base_domain}/send/presence",
            f"{base_domain}/presence",
        ]
    except Exception:
        url_candidates = [f"{base}/presence/send"]

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "token": (settings.whatsapp_token or "").strip(),
    }

    numero_sanitizado = _sanitize_number(number) or ""
    payload_main = {"number": numero_sanitizado, "presence": presence}
    payload_alt = {"phone": number, "presence": presence}

    method = getattr(settings, "whatsapp_method", "POST").upper()

    # Log token parcialmente mascarado
    try:
        tok = (settings.whatsapp_token or "").strip()
        masked = (tok[:8] + "..." + tok[-4:]) if tok else "<vazio>"
        logger.info(f"Auth UAZ token (masked): {masked} len={len(tok)}")
    except Exception:
        pass

    last_status = None
    last_body = ""
    for url in url_candidates:
        try:
            if method == "GET":
                logger.info(f"Presença (GET): url={url} params={payload_main}")
                response = requests.get(url, headers=headers, params=payload_main, timeout=10)
            else:
                logger.info(f"Presença (POST): url={url} payload={payload_main}")
                response = requests.post(url, headers=headers, json=payload_main, timeout=10)
            last_status = response.status_code
            last_body = (response.text or "")[:400]
            logger.info(f"UAZ retorno presença: status={last_status} body={last_body}")
            if response.status_code < 400:
                return True

            # tenta payload alternativo
            if method == "GET":
                response = requests.get(url, headers=headers, params=payload_alt, timeout=10)
            else:
                response = requests.post(url, headers=headers, json=payload_alt, timeout=10)
            last_status = response.status_code
            last_body = (response.text or "")[:400]
            logger.info(f"UAZ retorno presença (alt): status={last_status} body={last_body}")
            if response.status_code < 400:
                return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Falha ao enviar presença em {url}: {e}")

    logger.error(f"Falha ao enviar presença: status={last_status} body={last_body}")
    return False


def cancel_presence(number: str):
    n = _sanitize_number(number) or number
    # Sinalizar cancelamento de forma idempotente, mesmo se o loop ainda não tiver inicializado sua sessão
    sess = presence_sessions.get(n)
    if not sess:
        presence_sessions[n] = {"cancel": True}
    else:
        sess["cancel"] = True

    # Enviar pausa imediatamente para refletir o cancelamento no cliente
    send_presence_signal(n, "paused")


def presence_loop(number: str, presence: str, delay_ms: Optional[int] = None):
    """
    Loop de presença assíncrono:
    - reenvia a presença a cada 10s
    - duração máxima 300000ms
    - cancela automaticamente ao enviar mensagem (via cancel_presence)
    """
    n = _sanitize_number(number) or number
    max_ms = 300000
    tick_s = 10
    duration_ms = delay_ms if (isinstance(delay_ms, int) and delay_ms > 0) else max_ms
    if duration_ms > max_ms:
        duration_ms = max_ms

    # se for paused, apenas cancela imediatamente
    if str(presence).lower() == "paused":
        # Garante que qualquer loop existente seja sinalizado como cancelado
        presence_sessions.setdefault(n, {"cancel": False})
        presence_sessions[n]["cancel"] = True
        send_presence_signal(n, "paused")
        # Não remover a sessão aqui para permitir que loops ativos detectem o cancelamento
        return

    # Se já houver cancelamento marcado, não enviar 'composing' inicial
    existing = presence_sessions.get(n)
    if existing and existing.get("cancel"):
        try:
            send_presence_signal(n, "paused")
        except Exception:
            pass
        presence_sessions.pop(n, None)
        return

    # Não sobrescrever um cancelamento que possa ter sido disparado antes do loop iniciar
    presence_sessions.setdefault(n, {"cancel": False})

    end_time = time.time() + (duration_ms / 1000.0)
    # envia imediatamente e então a cada 10s
    send_presence_signal(n, presence)
    while time.time() < end_time:
        # Checar cancelamento antes e depois do sleep para evitar um envio extra
        if presence_sessions.get(n, {}).get("cancel"):
            break
        time.sleep(tick_s)
        if presence_sessions.get(n, {}).get("cancel"):
            break
        send_presence_signal(n, presence)

    # encerra presença
    send_presence_signal(n, "paused")
    presence_sessions.pop(n, None)


def process_audio_message_async(telefone: str, audio_url: str, message_id: Optional[str] = None, 
                               audio_headers: Optional[Dict[str, str]] = None, 
                               download_method: str = "GET", 
                               download_body: Optional[Dict[str, Any]] = None):
    """
    Processa mensagem de áudio: transcreve e envia para o agente (execução assíncrona).
    Suporta tanto GET direto quanto POST com body (UAZ API).
    """
    logger.info(f"Processando mensagem de áudio de {telefone} (método: {download_method})")
    
    try:
        # Verificar se temos chave OpenAI
        openai_api_key = getattr(settings, "openai_api_key", None)
        if not openai_api_key:
            logger.error("Chave OpenAI não configurada para transcrição de áudio")
            send_whatsapp_message(
                telefone,
                "🎤 Desculpe, não consegui processar seu áudio. Por favor, envie uma mensagem de texto."
            )
            return
        
        # Enviar status de gravação
        try:
            numero = _sanitize_number(telefone) or telefone
            send_presence_signal(numero, "recording")
        except Exception:
            pass
        
        # Processar áudio com os novos parâmetros
        audio_result = process_audio_message(audio_url, openai_api_key, audio_headers, download_method, download_body)
        
        if audio_result.get("success") and audio_result.get("transcription"):
            transcription = audio_result["transcription"]
            audio_info = audio_result.get("audio_info", {})
            
            logger.info(f"Áudio transcrito com sucesso: {len(transcription)} caracteres")
            
            # Enviar confirmação com transcrição
            duration = audio_info.get("duration", 0)
            duration_str = f"({int(duration)}s)" if duration > 0 else ""
            
            send_whatsapp_message(
                telefone,
                f"🎤 Áudio recebido {duration_str}! Transcrição: \"{transcription}\"\n\nProcessando sua mensagem..."
            )
            
            # Processar transcrição com o agente
            process_message_async(telefone, transcription, message_id)
            
        else:
            error_msg = audio_result.get("error", "Erro desconhecido na transcrição")
            logger.error(f"Falha na transcrição: {error_msg}")
            
            send_whatsapp_message(
                telefone,
                "🎤 Desculpe, não consegui entender seu áudio. Por favor, tente novamente ou envie uma mensagem de texto."
            )
            
    except Exception as e:
        logger.error(f"Erro ao processar áudio: {e}", exc_info=True)
        send_whatsapp_message(
            telefone,
            "🎤 Desculpe, ocorreu um erro ao processar seu áudio. Por favor, tente novamente."
        )
    finally:
        # Cancelar presença
        try:
            cancel_presence(telefone)
        except Exception:
            pass


def process_message_async(telefone: str, mensagem: str, message_id: Optional[str] = None):
    """
    Processa a mensagem com o agente e envia resposta (execução assíncrona).
    Garante cancelamento da presença mesmo quando a saída do agente é vazia.
    """
    logger.info(f"Processando mensagem assíncrona de {telefone}")

    try:
        # Executar agente
        result = run_agent(telefone, mensagem)

        # Normalizar saída: evitar string vazia ou None
        final_text = result.get("output") if isinstance(result, dict) else None
        if not isinstance(final_text, str) or not final_text.strip():
            final_text = "Desculpe, não consegui processar sua mensagem. Por favor, tente novamente."

        # Enviar resposta
        success = send_whatsapp_message(telefone, final_text)

        if success:
            logger.info(f"✅ Resposta enviada com sucesso para {telefone}")
        else:
            logger.error(f"❌ Falha ao enviar resposta para {telefone}")

    except Exception as e:
        logger.error(f"Erro no processamento assíncrono: {e}", exc_info=True)
        # Tentar enviar mensagem de erro
        try:
            send_whatsapp_message(
                telefone,
                "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."
            )
        except Exception:
            pass
    finally:
        # Cancelar presença em qualquer caso (com ou sem resposta)
        try:
            cancel_presence(telefone)
        except Exception:
            pass


def buffer_loop(telefone: str):
    """Agrega mensagens em janelas de 5s até 3 tentativas sem novas mensagens."""
    try:
        numero = _sanitize_number(telefone) or telefone
        prev_len = get_buffer_length(numero)
        consecutive_no_new = 0
        while consecutive_no_new < 3:
            time.sleep(5)
            cur_len = get_buffer_length(numero)
            if cur_len > prev_len:
                prev_len = cur_len
                consecutive_no_new = 0
            else:
                consecutive_no_new += 1

        msgs = pop_all_messages(numero)
        combined = " ".join([m for m in msgs if isinstance(m, str) and m.strip()])
        if not combined.strip():
            combined = msgs[-1] if msgs else ""
        if combined:
            process_message_async(numero, combined)
    except Exception as e:
        logger.error(f"Erro no buffer_loop: {e}", exc_info=True)
    finally:
        try:
            n = _sanitize_number(telefone) or telefone
            buffer_sessions.pop(n, None)
        except Exception:
            pass


# ============================================
# Endpoints
# ============================================

@app.get("/")
async def root():
    """Endpoint raiz para verificação de saúde"""
    return {
        "status": "online",
        "service": "Agente de Supermercado",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Endpoint de health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/")
async def root_post(request: Request, background_tasks: BackgroundTasks):
    """
    Alias para POST na raiz. Algumas integrações enviam POST para "/".
    Delegamos para o mesmo fluxo do webhook oficial em "/webhook/whatsapp".
    """
    return await webhook_whatsapp(request, background_tasks)


@app.post("/webhook/whatsapp")
async def webhook_whatsapp(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook para receber mensagens do WhatsApp
    
    Este endpoint recebe mensagens do WhatsApp via UAZ API e processa com o agente.
    O processamento é feito em background para retornar resposta rápida ao webhook.
    Agora com suporte completo para mensagens de áudio com transcrição.
    """
    try:
        # Receber payload e normalizar
        payload = await request.json()
        logger.info(f"Webhook recebido: {payload}")

        normalized = _extract_incoming(payload)
        telefone = normalized.get("telefone")
        mensagem_texto = normalized.get("mensagem_texto")
        message_type = normalized.get("message_type")
        message_id = normalized.get("message_id")
        from_me = bool(normalized.get("from_me") or False)
        audio_url = normalized.get("audio_url")

        # Construir preview seguro para log
        if isinstance(mensagem_texto, str):
            texto_preview = mensagem_texto[:120]
        elif mensagem_texto is None:
            if is_audio_message(message_type):
                texto_preview = "[Áudio recebido - será processado]"
            else:
                texto_preview = ""
        else:
            texto_preview = str(mensagem_texto)[:120]

        logger.info(
            f"Normalizado: telefone={telefone} type={message_type} message_id={message_id} audio_url={audio_url} texto_preview={texto_preview}"
        )

        if not telefone:
            logger.error("Telefone não encontrado no payload")
            raise HTTPException(status_code=400, detail="Telefone não encontrado")
        
        # Verificar se é mensagem de áudio
        if is_audio_message(message_type) and audio_url:
            logger.info(f"Mensagem de áudio detectada de {telefone}")
            
            # Extrair informações específicas da UAZ API
            audio_download_url = None
            audio_headers = {}
            audio_method = "GET"
            audio_body = None
            
            try:
                # Verificar se é estrutura UAZ com token e messageid
                body_data = payload.get("body", {})
                token = body_data.get("token") or payload.get("token")
                
                if token and audio_url and "uazapi.com" in audio_url:
                    # É UAZ API - usar POST com messageid no body
                    audio_download_url = "https://wildhub.uazapi.com/message/download"
                    audio_headers = {
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                    audio_method = "POST"
                    audio_body = {"id": audio_url}  # audio_url contém o messageid
                    
                    logger.info(f"Detectado UAZ API - usando POST com messageid: {audio_url}")
                else:
                    # Outro formato - usar URL direta
                    audio_download_url = audio_url
                    if token:
                        audio_headers["Authorization"] = f"Bearer {token}"
                        
            except Exception as e:
                logger.warning(f"Erro ao extrair dados UAZ, usando fallback: {e}")
                audio_download_url = audio_url
            
            # Processar áudio em background
            background_tasks.add_task(
                process_audio_message_async,
                telefone,
                audio_download_url,
                message_id,
                audio_headers,
                audio_method,
                audio_body
            )
            
            return JSONResponse(
                status_code=200,
                content={
                    "status": "processing_audio",
                    "message": "Áudio recebido e será processado em segundos",
                }
            )
        
        # Para mensagens de texto normais (ignorar se for áudio)
        if not mensagem_texto and not is_audio_message(message_type):
            logger.error("Mensagem de texto não encontrada no payload")
            raise HTTPException(status_code=400, detail="Mensagem não encontrada")

        # Filtro: ignorar mensagens marcadas como 'fromMe' pelo provedor, mas salvar no histórico
        if from_me:
            try:
                logger.info("Mensagem ignorada: flag fromMe=True no payload (auto-mensagem)")
                # Persistir no histórico do cliente como mensagem do agente (AI)
                try:
                    hist = get_session_history(telefone)
                    hist.add_ai_message(mensagem_texto or "")
                    logger.info("Mensagem fromMe salva no histórico como AI")
                except Exception as e:
                    logger.warning(f"Falha ao salvar fromMe no histórico: {e}")
                # Ativar cooldown por 60s para o cliente
                try:
                    numero = _sanitize_number(telefone) or telefone
                    set_agent_cooldown(numero, ttl_seconds=60)
                    logger.info(f"Cooldown ativado para {numero} por 60s após envio do agente")
                except Exception as e:
                    logger.warning(f"Falha ao ativar cooldown: {e}")
            except Exception:
                pass
            return JSONResponse(
                status_code=200,
                content={
                    "status": "ignored",
                    "reason": "self_message",
                    "message": "Mensagem marcada como fromMe não dispara automação"
                },
            )

        # Filtro: ignorar mensagens vindas do próprio número do agente
        try:
            incoming_num = _sanitize_number(telefone) or telefone
            agent_raw = getattr(settings, "whatsapp_agent_number", None)
            agent_num = _sanitize_number(agent_raw) if agent_raw else None
            try:
                logger.info(f"Filtro auto-mensagem: incoming={incoming_num} agent={agent_num}")
            except Exception:
                pass
            if agent_num and incoming_num == agent_num:
                logger.info(f"Mensagem ignorada: veio do próprio número do agente ({agent_num})")
                # Persistir no histórico do cliente como mensagem do agente (AI)
                try:
                    hist = get_session_history(telefone)
                    hist.add_ai_message(mensagem_texto or "")
                    logger.info("Mensagem do próprio número salva no histórico como AI")
                except Exception as e:
                    logger.warning(f"Falha ao salvar auto-mensagem no histórico: {e}")
                # Ativar cooldown por 60s
                try:
                    numero = _sanitize_number(telefone) or telefone
                    set_agent_cooldown(numero, ttl_seconds=60)
                    logger.info(f"Cooldown ativado para {numero} por 60s após auto-mensagem do agente")
                except Exception as e:
                    logger.warning(f"Falha ao ativar cooldown: {e}")
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "ignored",
                        "reason": "self_message",
                        "message": "Mensagem do número do agente não dispara automação"
                    },
                )
        except Exception:
            # Não bloquear fluxo em caso de falha ao sanitizar/comparar
            pass

        # Checar cooldown antes de iniciar presença/agregação
        try:
            numero = _sanitize_number(telefone) or telefone
            active, ttl = is_agent_in_cooldown(numero)
            if active:
                logger.info(f"Cooldown ativo para {numero} (TTL restante ~{ttl}s). Pausando automação.")
                # Empilhar mensagem para não perder contexto
                try:
                    push_message_to_buffer(numero, mensagem_texto)
                except Exception:
                    pass
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": "cooldown",
                        "reason": "agent_paused",
                        "ttl": ttl,
                        "message": "Automação pausada por até 60s após envio do agente",
                    },
                )
        except Exception:
            pass

        # Iniciar indicação de digitando enquanto processa (evitar threads duplicadas)
        try:
            numero = _sanitize_number(telefone) or telefone
            sess = presence_sessions.get(numero)
            if (not sess) or sess.get("cancel"):
                # Marcar sessão antes de iniciar para evitar corrida e múltiplas threads
                presence_sessions[numero] = {"cancel": False, "running": True}
                threading.Thread(
                    target=presence_loop,
                    args=(numero, "composing", 30000),  # 30s de presença enquanto agregamos
                    daemon=True,
                ).start()
            else:
                logger.info(f"Ignorando nova presença: sessão já existente/cancelada para {numero}")
        except Exception:
            # Se houver falha ao iniciar presença, não bloquear o restante do fluxo
            pass

        # Empilhar no buffer e iniciar agregação 5s x 3
        try:
            numero = _sanitize_number(telefone) or telefone
            ok_push = push_message_to_buffer(numero, mensagem_texto)
            if not ok_push:
                # fallback: processar imediatamente
                background_tasks.add_task(
                    process_message_async,
                    telefone,
                    mensagem_texto,
                    message_id
                )
            else:
                if not buffer_sessions.get(numero):
                    buffer_sessions[numero] = {"running": True}
                    # Usar o número sanitizado para consistência
                    threading.Thread(target=buffer_loop, args=(numero,), daemon=True).start()
        except Exception as e:
            logger.error(f"Erro ao agendar agregação: {e}")
            background_tasks.add_task(
                process_message_async,
                telefone,
                mensagem_texto,
                message_id
            )

        # Retornar resposta imediata (estamos agregando mensagens)
        return JSONResponse(
            status_code=200,
            content={
                "status": "buffering",
                "message": "Aguardando até 15s para agrupar mensagens do cliente",
            }
        )

    except HTTPException:
        # Propagar erros de validação do payload
        raise

    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


# Aliases UAZ para compatibilidade com integrações existentes
@app.post("/webhook/uaz")
async def webhook_uaz_post(request: Request, background_tasks: BackgroundTasks):
    """
    Alias de POST para o webhook oficial do WhatsApp.
    Algumas integrações enviam para "/webhook/uaz"; delegamos para o mesmo fluxo.
    """
    return await webhook_whatsapp(request, background_tasks)


@app.get("/webhook/uaz")
async def webhook_uaz_get():
    """
    GET informativo para o alias do webhook UAZ.
    Útil para verificações de disponibilidade.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "endpoint": "/webhook/uaz",
            "alias_of": "/webhook/whatsapp",
            "message": "Use POST para enviar eventos de mensagem.",
            "health": "/health",
        },
    )


# Endpoints de dryrun para testes rápidos do agente
class DryRunRequest(BaseModel):
    telefone: str = Field(..., description="Número do cliente no formato internacional")
    mensagem: str = Field(..., description="Mensagem de teste para o agente")


@app.get("/agent/dryrun")
async def agent_dryrun_get():
    """
    Endpoint GET informativo para dryrun do agente.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "endpoint": "/agent/dryrun",
            "method": "POST",
            "body": {
                "telefone": "5511999999999",
                "mensagem": "Quero Coca 2L",
            },
        },
    )


@app.post("/agent/dryrun")
async def agent_dryrun_post(req: DryRunRequest) -> AgentResponse:
    """
    Executa o agente diretamente sem passar pelo WhatsApp.
    Útil para testes de fluxo.
    """
    try:
        result = run_agent(req.telefone, req.mensagem)
        return AgentResponse(
            success=result["error"] is None,
            response=result["output"],
            telefone=req.telefone,
            timestamp=datetime.now().isoformat(),
            error=result["error"],
        )
    except Exception as e:
        logger.error(f"Erro no dryrun do agente: {e}", exc_info=True)
        return AgentResponse(
            success=False,
            response="Erro ao executar dryrun do agente",
            telefone=req.telefone,
            timestamp=datetime.now().isoformat(),
            error=str(e),
        )


@app.post("/presence")
async def presence(request: PresenceRequest, background_tasks: BackgroundTasks):
    """Envia atualização de presença de forma assíncrona.
    - presence: composing | recording | paused
    - delay: duração em ms (máx 300000); reenvio a cada 10s
    - cancelamento automático ao enviar mensagem (se houver)
    """
    try:
        presence_type = (request.presence or "").lower()
        if presence_type not in {"composing", "recording", "paused"}:
            raise HTTPException(status_code=400, detail="presence inválida (composing|recording|paused)")

        numero = _sanitize_number(request.number) or request.number
        if presence_type == "paused":
            # Cancelar inline sem criar thread, para refletir imediatamente
            cancel_presence(numero)
        else:
            # Evitar threads duplicadas para o mesmo número
            sess = presence_sessions.get(numero)
            if sess:
                logger.info(f"Ignorando nova presença: sessão já existente/cancelada para {numero}")
            else:
                threading.Thread(
                    target=presence_loop,
                    args=(numero, presence_type, request.delay),
                    daemon=True,
                ).start()
        return JSONResponse(
            status_code=200,
            content={
                "status": "accepted",
                "number": _sanitize_number(request.number),
                "presence": presence_type,
                "duration_ms": min(request.delay or 300000, 300000),
                "tick_seconds": 10,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao agendar presença: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.post("/message")
async def send_message(message: WhatsAppMessage) -> AgentResponse:
    """
    Endpoint direto para enviar mensagem ao agente (para testes)
    
    Este endpoint permite testar o agente sem passar pelo WhatsApp.
    """
    logger.info(f"Mensagem direta recebida de {message.telefone}")
    
    try:
        # Executar agente
        result = run_agent(message.telefone, message.mensagem)
        
        return AgentResponse(
            success=result["error"] is None,
            response=result["output"],
            telefone=message.telefone,
            timestamp=datetime.now().isoformat(),
            error=result["error"]
        )
    
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}", exc_info=True)
        
        return AgentResponse(
            success=False,
            response="Erro ao processar mensagem",
            telefone=message.telefone,
            timestamp=datetime.now().isoformat(),
            error=str(e)
        )


# Endpoint para envio direto via WhatsApp (teste)
@app.post("/send_whatsapp")
async def send_whatsapp(message: WhatsAppMessage):
    """
    Envia uma mensagem diretamente via WhatsApp usando a UAZ API.
    Útil para testes de envio sem passar pelo webhook.
    """
    logger.info(f"Envio direto via WhatsApp para {message.telefone}")
    try:
        ok = send_whatsapp_message(message.telefone, message.mensagem)
        if not ok:
            raise HTTPException(status_code=502, detail="Falha ao enviar na API do WhatsApp")
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "status": "sent",
                "telefone": message.telefone,
                "timestamp": datetime.now().isoformat(),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no envio direto via WhatsApp: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

# ============================================
# Inicialização
# ============================================

@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar o servidor"""
    logger.info("=" * 60)
    logger.info("🚀 Iniciando Servidor do Agente de Supermercado")
    logger.info("=" * 60)
    logger.info(f"Ambiente: {'DEBUG' if settings.debug_mode else 'PRODUÇÃO'}")
    logger.info(f"Modelo LLM: {settings.llm_model}")
    logger.info(f"Host: {settings.server_host}:{settings.server_port}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Executado ao desligar o servidor"""
    logger.info("🛑 Desligando Servidor do Agente de Supermercado")


# ============================================
# Execução
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug_mode,
        log_level=settings.log_level.lower()
    )
