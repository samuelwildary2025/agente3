"""
Ferramentas de processamento de áudio para transcrição e download
"""
import os
import tempfile
import requests
import mimetypes
from typing import Optional, Dict, Any, Union
from pathlib import Path
import io
from config.logger import setup_logger

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import pydub
    from pydub import AudioSegment
    AUDIO_PROCESSING_AVAILABLE = True
except ImportError:
    AUDIO_PROCESSING_AVAILABLE = False

logger = setup_logger(__name__)

# Formatos de áudio suportados
SUPPORTED_AUDIO_FORMATS = {
    'audio/mpeg': '.mp3',
    'audio/mp3': '.mp3',
    'audio/mp4': '.m4a',
    'audio/ogg': '.ogg',
    'audio/opus': '.opus',
    'audio/wav': '.wav',
    'audio/x-wav': '.wav',
    'audio/webm': '.webm',
    'audio/aac': '.aac',
    'audio/3gpp': '.3gp',
    'audio/3gpp2': '.3g2',
}

# Extensões suportadas
SUPPORTED_EXTENSIONS = ['.mp3', '.mp4', '.m4a', '.ogg', '.opus', '.wav', '.webm', '.aac', '.3gp', '.3g2']


def download_audio_file(url: str, headers: Optional[Dict[str, str]] = None, 
                       method: str = "GET", body: Optional[Dict[str, Any]] = None) -> Optional[bytes]:
    """
    Baixa arquivo de áudio de uma URL.
    
    Args:
        url: URL do arquivo de áudio
        headers: Headers opcionais para o download
        method: Método HTTP (GET ou POST)
        body: Body para requisições POST
    
    Returns:
        Bytes do arquivo de áudio ou None em caso de erro
    """
    try:
        logger.info(f"Baixando áudio de: {url} (método: {method})")
        
        if method.upper() == "POST":
            response = requests.post(url, headers=headers or {}, json=body, stream=True, timeout=30)
        else:
            response = requests.get(url, headers=headers or {}, stream=True, timeout=30)
        
        response.raise_for_status()
        
        # Verificar tamanho do arquivo (máximo 50MB)
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 50 * 1024 * 1024:
            logger.error(f"Arquivo muito grande: {content_length} bytes")
            return None
        
        # Ler arquivo em chunks para não sobrecarregar memória
        audio_data = io.BytesIO()
        for chunk in response.iter_content(chunk_size=8192):
            audio_data.write(chunk)
            
            # Verificar limite enquanto baixa
            if audio_data.tell() > 50 * 1024 * 1024:
                logger.error("Arquivo excedeu limite de 50MB durante download")
                return None
        
        audio_data.seek(0)
        audio_bytes = audio_data.getvalue()
        
        logger.info(f"Áudio baixado com sucesso: {len(audio_bytes)} bytes")
        return audio_bytes
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao baixar áudio: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado ao baixar áudio: {e}")
        return None


def get_audio_info(audio_data: bytes) -> Dict[str, Any]:
    """
    Obtém informações sobre o arquivo de áudio.
    
    Args:
        audio_data: Bytes do arquivo de áudio
    
    Returns:
        Dict com informações do áudio
    """
    try:
        if not AUDIO_PROCESSING_AVAILABLE:
            return {
                "format": "unknown",
                "duration": 0,
                "size": len(audio_data),
                "error": "pydub não disponível"
            }
        
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp_file:
            tmp_file.write(audio_data)
            tmp_path = tmp_file.name
        
        try:
            # Detectar formato automaticamente
            audio = AudioSegment.from_file(tmp_path)
            
            info = {
                "format": audio.format if hasattr(audio, 'format') else 'unknown',
                "duration": len(audio) / 1000.0,  # duração em segundos
                "size": len(audio_data),
                "channels": audio.channels,
                "frame_rate": audio.frame_rate,
                "sample_width": audio.sample_width,
                "frame_count": len(audio),
            }
            
            logger.info(f"Informações do áudio: {info}")
            return info
            
        finally:
            # Limpar arquivo temporário
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
                
    except Exception as e:
        logger.error(f"Erro ao obter informações do áudio: {e}")
        return {
            "format": "unknown",
            "duration": 0,
            "size": len(audio_data),
            "error": str(e)
        }


def convert_audio_to_wav(audio_data: bytes, original_format: str = None) -> Optional[bytes]:
    """
    Converte áudio para formato WAV compatível com OpenAI.
    
    Args:
        audio_data: Bytes do arquivo de áudio original
        original_format: Formato original (opcional)
    
    Returns:
        Bytes do arquivo WAV ou None em caso de erro
    """
    try:
        if not AUDIO_PROCESSING_AVAILABLE:
            logger.error("pydub não disponível para conversão")
            return None
        
        # Criar arquivo temporário para entrada
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{original_format or "tmp"}') as tmp_input:
            tmp_input.write(audio_data)
            input_path = tmp_input.name
        
        # Criar arquivo temporário para saída WAV
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_output:
            output_path = tmp_output.name
        
        try:
            # Carregar áudio original
            audio = AudioSegment.from_file(input_path)
            
            # Converter para formato compatível com OpenAI
            # - Taxa de amostragem: 16kHz
            # - Canais: mono
            # - Formato: WAV
            audio_converted = audio.set_frame_rate(16000).set_channels(1)
            
            # Exportar como WAV
            audio_converted.export(output_path, format='wav')
            
            # Ler arquivo WAV convertido
            with open(output_path, 'rb') as f:
                wav_data = f.read()
            
            logger.info(f"Áudio convertido: {len(audio_data)} → {len(wav_data)} bytes")
            return wav_data
            
        finally:
            # Limpar arquivos temporários
            try:
                os.unlink(input_path)
                os.unlink(output_path)
            except Exception:
                pass
                
    except Exception as e:
        logger.error(f"Erro ao converter áudio: {e}")
        return None


def transcribe_audio_openai(audio_data: bytes, api_key: str, language: str = "pt") -> Optional[str]:
    """
    Transcreve áudio usando OpenAI Whisper API.
    
    Args:
        audio_data: Bytes do arquivo de áudio
        api_key: Chave API da OpenAI
        language: Idioma do áudio (padrão: pt)
    
    Returns:
        Texto transcrito ou None em caso de erro
    """
    try:
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI não disponível")
            return None
        
        # Configurar cliente OpenAI
        client = openai.OpenAI(api_key=api_key)
        
        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(audio_data)
            tmp_path = tmp_file.name
        
        try:
            logger.info(f"Transcrevendo áudio com OpenAI Whisper (idioma: {language})")
            
            # Abrir arquivo para transcrição
            with open(tmp_path, 'rb') as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language,
                    response_format="text"
                )
            
            # A resposta já vem como string quando response_format="text"
            transcribed_text = response.strip() if response else ""
            
            logger.info(f"Transcrição concluída: {len(transcribed_text)} caracteres")
            return transcribed_text
            
        finally:
            # Limpar arquivo temporário
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
                
    except openai.OpenAIError as e:
        logger.error(f"Erro da API OpenAI: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro ao transcrever áudio: {e}")
        return None


def process_audio_message(audio_url: str, api_key: str, headers: Optional[Dict[str, str]] = None,
                         download_method: str = "GET", download_body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Processa mensagem de áudio completa: download, conversão e transcrição.
    
    Args:
        audio_url: URL do arquivo de áudio
        api_key: Chave API da OpenAI
        headers: Headers opcionais para download
        download_method: Método HTTP para download (GET ou POST)
        download_body: Body para requisições POST
    
    Returns:
        Dict com resultado do processamento
    """
    try:
        logger.info(f"Processando mensagem de áudio: {audio_url} (método: {download_method})")
        
        # 1. Baixar áudio
        audio_data = download_audio_file(audio_url, headers, download_method, download_body)
        if not audio_data:
            return {
                "success": False,
                "error": "Falha ao baixar áudio",
                "transcription": None,
                "audio_info": None
            }
        
        # 2. Obter informações do áudio
        audio_info = get_audio_info(audio_data)
        
        # 3. Converter para formato compatível (se necessário)
        if AUDIO_PROCESSING_AVAILABLE:
            wav_data = convert_audio_to_wav(audio_data)
            if wav_data:
                audio_data = wav_data
        
        # 4. Transcrever
        transcription = transcribe_audio_openai(audio_data, api_key)
        if not transcription:
            return {
                "success": False,
                "error": "Falha ao transcrever áudio",
                "transcription": None,
                "audio_info": audio_info
            }
        
        # 5. Retornar resultado completo
        return {
            "success": True,
            "transcription": transcription,
            "audio_info": audio_info,
            "processing_time": audio_info.get("duration", 0) if audio_info else 0
        }
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem de áudio: {e}")
        return {
            "success": False,
            "error": f"Erro ao processar áudio: {str(e)}",
            "transcription": None,
            "audio_info": None
        }


def is_audio_message(message_type: str, content_type: str = None) -> bool:
    """
    Verifica se uma mensagem é de áudio baseado no tipo e content-type.
    
    Args:
        message_type: Tipo da mensagem (audio, audioMessage, etc.)
        content_type: Content-Type do arquivo (opcional)
    
    Returns:
        True se for mensagem de áudio
    """
    audio_types = ['audio', 'audioMessage', 'ptt', 'voice']
    
    if message_type and message_type.lower() in audio_types:
        return True
    
    if content_type and content_type.startswith('audio/'):
        return True
    
    return False