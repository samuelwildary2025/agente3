#!/usr/bin/env python3
"""
Teste isolado das funções de tempo
"""

import datetime
import pytz

def format_timestamp(timestamp, timezone="America/Sao_Paulo"):
    """
    Formata um timestamp para exibição legível.
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
        return timestamp.strftime("%d/%m/%Y %H:%M:%S")

def get_time_diff_description(timestamp1, timestamp2):
    """
    Calcula e descreve a diferença entre dois timestamps.
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
        return "em momento desconhecido"

def test_time_functions():
    """Testa as funções de formatação de tempo"""
    print("=== Testando Funções de Tempo ===")
    
    # Testar formatação de timestamp atual
    now = datetime.datetime.now(pytz.utc)
    formatted = format_timestamp(now)
    print(f"📅 Timestamp atual formatado: {formatted}")
    
    # Testar diferenças de tempo
    test_cases = [
        ("30 segundos atrás", now - datetime.timedelta(seconds=30)),
        ("5 minutos atrás", now - datetime.timedelta(minutes=5)),
        ("1 hora atrás", now - datetime.timedelta(hours=1)),
        ("3 horas atrás", now - datetime.timedelta(hours=3)),
        ("1 dia atrás", now - datetime.timedelta(days=1)),
        ("3 dias atrás", now - datetime.timedelta(days=3)),
    ]
    
    for desc, past_time in test_cases:
        diff_desc = get_time_diff_description(now, past_time)
        print(f"⏰ {desc}: {diff_desc}")
    
    print("\n✅ Funções de tempo testadas com sucesso!")

def test_timestamp_formatting():
    """Testa formatação de diferentes timestamps"""
    print("\n=== Testando Formatação de Timestamps ===")
    
    # Testar diferentes horários do dia
    test_times = [
        datetime.datetime(2024, 1, 15, 8, 30, 0, tzinfo=pytz.utc),  # Manhã
        datetime.datetime(2024, 1, 15, 14, 45, 30, tzinfo=pytz.utc),  # Tarde
        datetime.datetime(2024, 1, 15, 21, 15, 45, tzinfo=pytz.utc),  # Noite
    ]
    
    for test_time in test_times:
        formatted = format_timestamp(test_time)
        print(f"🕐 {test_time.strftime('%H:%M:%S')} UTC → {formatted}")
    
    print("\n✅ Formatação de timestamps testada!")

if __name__ == "__main__":
    print("🧪 Testando sistema de timestamps do agente\n")
    test_time_functions()
    test_timestamp_formatting()
    print("\n🎉 Testes concluídos!")
    
    # Exemplo de como o agente usaria isso
    print("\n=== Exemplo de Uso no Agente ===")
    print("Cliente: 'Quando foi que eu te falei sobre o arroz?'")
    
    # Simular mensagem do passado
    mensagem_passada = datetime.datetime.now(pytz.utc) - datetime.timedelta(hours=2, minutes=15)
    tempo_desc = get_time_diff_description(datetime.datetime.now(pytz.utc), mensagem_passada)
    horario_fmt = format_timestamp(mensagem_passada)
    
    print(f"Ana: 'Você mencionou o arroz {tempo_desc}, às {horario_fmt}. '")
    print("     'Ainda está procurando arroz ou posso te ajudar com outra coisa?'")