#!/usr/bin/env python3
"""
Teste simples das funções de tempo e formatação
"""

import datetime
import pytz
from tools.time_tool import format_timestamp, get_time_diff_description

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