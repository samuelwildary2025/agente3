#!/usr/bin/env python3
"""
Teste do agente com capacidade de entender timestamps de mensagens
"""

import os
import sys
import datetime
import pytz
from pathlib import Path

# Adicionar o diretório atual ao path
sys.path.append(str(Path(__file__).parent))

from agent_langgraph import run_agent
from memory.limited_postgres_memory import LimitedPostgresChatMessageHistory
from config.settings import settings
from tools.time_tool import format_timestamp, get_time_diff_description

def test_time_formatting():
    """Testa as funções de formatação de tempo"""
    print("=== Testando Formatação de Tempo ===")
    
    # Testar formatação de timestamp
    test_time = datetime.datetime.now(pytz.utc)
    formatted = format_timestamp(test_time)
    print(f"Timestamp atual formatado: {formatted}")
    
    # Testar diferença de tempo
    old_time = test_time - datetime.timedelta(hours=2, minutes=30)
    diff_desc = get_time_diff_description(test_time, old_time)
    print(f"Diferença de tempo (2h30min): {diff_desc}")
    
    print()

def test_memory_with_timestamps():
    """Testa o sistema de memória com timestamps"""
    print("=== Testando Sistema de Memória com Timestamps ===")
    
    # Criar histórico de teste
    session_id = "test_time_aware_123"
    
    history = LimitedPostgresChatMessageHistory(
        connection_string=settings.postgres_connection_string,
        session_id=session_id,
        table_name=settings.postgres_table_name,
        max_messages=10
    )
    
    # Limpar histórico anterior
    history.clear()
    
    # Adicionar algumas mensagens de teste
    from langchain_core.messages import HumanMessage, AIMessage
    
    # Simular mensagens com diferentes horários
    msg1 = HumanMessage(content="Olá, quero comprar arroz")
    history.add_message(msg1)
    
    msg2 = AIMessage(content="Claro! Que tipo de arroz você procura?")
    history.add_message(msg2)
    
    msg3 = HumanMessage(content="Arroz parboilizado 5kg")
    history.add_message(msg3)
    
    # Aguardar um pouco para simular diferença de tempo
    import time
    time.sleep(2)
    
    msg4 = AIMessage(content="Perfeito! Temos arroz parboilizado 5kg disponível.")
    history.add_message(msg4)
    
    # Testar recuperação com timestamps
    messages_with_time = history.get_messages_with_timestamp_info()
    print(f"Recuperadas {len(messages_with_time)} mensagens com timestamps")
    
    for i, msg_info in enumerate(messages_with_time):
        print(f"Mensagem {i+1}:")
        print(f"  Tipo: {msg_info['message'].get('type', 'unknown')}")
        print(f"  Conteúdo: {msg_info['message'].get('content', '')[:50]}...")
        print(f"  Horário: {msg_info['formatted_time']}")
        print(f"  Tempo atrás: {msg_info['time_ago']}")
        print()
    
    # Testar contexto com tempo
    time_aware_context = history.get_time_aware_context()
    print(f"Contexto com informações de tempo: {len(time_aware_context)} mensagens")
    
    for msg in time_aware_context:
        print(f"Mensagem: {msg.content[:50]}...")
        if hasattr(msg, 'additional_kwargs') and msg.additional_kwargs:
            print(f"  Timestamp: {msg.additional_kwargs.get('timestamp', 'N/A')}")
            print(f"  Tempo atrás: {msg.additional_kwargs.get('time_ago', 'N/A')}")
        print()
    
    # Limpar histórico de teste
    history.clear()
    print("✅ Teste de memória concluído")
    print()

def test_agent_with_time_awareness():
    """Testa o agente com perguntas sobre tempo"""
    print("=== Testando Agente com Consciência de Tempo ===")
    
    # Testar com uma conversa simulada
    telefone_teste = "5511999998888"
    
    # Primeira mensagem - estabelecer contexto
    print("Cliente: Olá, quero comprar pão francês")
    resposta1 = run_agent(telefone_teste, "Olá, quero comprar pão francês")
    print(f"Ana: {resposta1['output']}")
    print()
    
    # Aguardar um momento
    import time
    time.sleep(3)
    
    # Segunda mensagem - perguntar sobre horário
    print("Cliente: Que horas são agora?")
    resposta2 = run_agent(telefone_teste, "Que horas são agora?")
    print(f"Ana: {resposta2['output']}")
    print()
    
    # Terceira mensagem - perguntar sobre histórico
    print("Cliente: Qual foi minha primeira mensagem?")
    resposta3 = run_agent(telefone_teste, "Qual foi minha primeira mensagem?")
    print(f"Ana: {resposta3['output']}")
    print()
    
    # Testar consulta direta de histórico
    print("=== Testando Ferramenta de Histórico ===")
    from agent_langgraph import historico_tool
    
    historico_result = historico_tool(telefone_teste, 3)
    print("Histórico recuperado:")
    print(historico_result)
    print()

def main():
    """Executa todos os testes"""
    print("🧪 Iniciando testes do agente com consciência de tempo\n")
    
    try:
        test_time_formatting()
        test_memory_with_timestamps()
        test_agent_with_time_awareness()
        
        print("✅ Todos os testes concluídos com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()