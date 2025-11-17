"""
Ferramenta para obter data e hora atual e formatar timestamps
"""
import datetime
import pytz
from typing import Optional
from config.logger import setup_logger

logger = setup_logger(__name__)


def format_timestamp(timestamp: datetime.datetime, timezone: str = "America/Sao_Paulo") -> str:
    """
    Formata um timestamp para exibição legível.
    
    Args:
        timestamp: Timestamp a ser formatado
        timezone: Fuso horário para conversão
    
    Returns:
        String formatada com data e hora legível
    """
    try:
        if timestamp.tzinfo is None:
            # Assume UTC se não tiver timezone
            timestamp = pytz.utc.localize(timestamp)
        
        tz = pytz.timezone(timezone)
        local_time = timestamp.astimezone(tz)
        
        # Formato amigável
        formatted_time = local_time.strftime("%d/%m/%Y às %H:%M:%S")
        
        # Dia da semana
        day_of_week = local_time.strftime("%A")
        day_names = {
            "Monday": "Segunda-feira",
            "Tuesday": "Terça-feira", 
            "Wednesday": "Quarta-feira",
            "Thursday": "Quinta-feira",
            "Friday": "Sexta-feira",
            "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        day_pt = day_names.get(day_of_week, day_of_week)
        
        return f"{day_pt}, {formatted_time}"
        
    except Exception as e:
        logger.error(f"Erro ao formatar timestamp: {e}")
        return timestamp.strftime("%d/%m/%Y %H:%M:%S")


def get_time_diff_description(timestamp1: datetime.datetime, timestamp2: datetime.datetime) -> str:
    """
    Calcula e descreve a diferença entre dois timestamps.
    
    Args:
        timestamp1: Timestamp mais recente
        timestamp2: Timestamp mais antigo
    
    Returns:
        Descrição legível da diferença de tempo
    """
    try:
        diff = timestamp1 - timestamp2
        
        if diff.days > 0:
            if diff.days == 1:
                return "há 1 dia"
            else:
                return f"há {diff.days} dias"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            if hours == 1:
                return "há 1 hora"
            else:
                return f"há {hours} horas"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            if minutes == 1:
                return "há 1 minuto"
            else:
                return f"há {minutes} minutos"
        else:
            return "agora mesmo"
            
    except Exception as e:
        logger.error(f"Erro ao calcular diferença de tempo: {e}")
        return "em momento desconhecido"


def get_current_time(timezone: str = "America/Sao_Paulo") -> str:
    """
    Retorna a data e hora atual no fuso horário especificado.
    
    Args:
        timezone: Fuso horário (padrão: America/Sao_Paulo)
    
    Returns:
        String formatada com data e hora
    """
    try:
        tz = pytz.timezone(timezone)
        now = datetime.datetime.now(tz)
        
        # Formato amigável
        formatted_time = now.strftime("%d/%m/%Y às %H:%M:%S (%Z)")
        
        # Informações adicionais
        day_of_week = now.strftime("%A")
        day_names = {
            "Monday": "Segunda-feira",
            "Tuesday": "Terça-feira",
            "Wednesday": "Quarta-feira",
            "Thursday": "Quinta-feira",
            "Friday": "Sexta-feira",
            "Saturday": "Sábado",
            "Sunday": "Domingo"
        }
        day_pt = day_names.get(day_of_week, day_of_week)
        
        result = f"📅 {day_pt}, {formatted_time}"
        
        logger.info(f"Hora atual consultada: {result}")
        return result
    
    except pytz.exceptions.UnknownTimeZoneError:
        error_msg = f"❌ Erro: Fuso horário '{timezone}' desconhecido."
        logger.error(error_msg)
        return error_msg
    
    except Exception as e:
        error_msg = f"❌ Erro ao obter hora atual: {str(e)}"
        logger.error(error_msg)
        return error_msg
