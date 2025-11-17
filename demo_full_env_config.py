#!/usr/bin/env python3
"""
Demonstração da configuração de tabela e limite via variáveis de ambiente
"""

import os
import sys

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configura variáveis de ambiente para teste
os.environ["POSTGRES_TABLE_NAME"] = "memoria"  # Tabela correta
os.environ["POSTGRES_MESSAGE_LIMIT"] = "25"   # Limite de teste

from config.settings import settings

def demonstrate_full_env_config():
    """Demonstra a configuração completa via variáveis de ambiente"""
    
    print("🔧 Configuração Completa via Variáveis de Ambiente")
    print("=" * 60)
    
    print("📋 Configurações atuais:")
    print(f"  → Tabela PostgreSQL: {settings.postgres_table_name}")
    print(f"  → Limite de mensagens: {settings.postgres_message_limit}")
    print(f"  → Conexão: {settings.postgres_connection_string}")
    
    print("\n💡 Como configurar tudo no arquivo .env:")
    print("-" * 50)
    print("# PostgreSQL Configuration")
    print("POSTGRES_CONNECTION_STRING=postgresql://user:pass@host:port/db?sslmode=disable")
    print("POSTGRES_TABLE_NAME=memoria              # Nome da tabela de histórico")
    print("POSTGRES_MESSAGE_LIMIT=20                # Número de mensagens para o agente")
    print("")
    print("# Exemplos de configuração:")
    print("POSTGRES_TABLE_NAME=chat_history         # Tabela customizada")
    print("POSTGRES_TABLE_NAME=conversas            # Outro nome")
    print("POSTGRES_MESSAGE_LIMIT=30                # 30 mensagens recentes")
    print("POSTGRES_MESSAGE_LIMIT=0                 # Ilimitado (comportamento antigo)")
    
    print("\n🎯 Exemplos práticos:")
    print("-" * 30)
    
    print("\n📊 Para análise de dados (relatórios):")
    print("  POSTGRES_TABLE_NAME=memoria")
    print("  POSTGRES_MESSAGE_LIMIT=50    # Mais contexto para o agente")
    
    print("\n⚡ Para performance:")
    print("  POSTGRES_TABLE_NAME=memoria") 
    print("  POSTGRES_MESSAGE_LIMIT=15    # Menos contexto, mais rápido")
    
    print("\n🔍 Para debug:")
    print("  POSTGRES_TABLE_NAME=debug_conversations")
    print("  POSTGRES_MESSAGE_LIMIT=0     # Ver tudo que o agente recebe")
    
    print("\n💰 Para economizar tokens:")
    print("  POSTGRES_TABLE_NAME=memoria")
    print("  POSTGRES_MESSAGE_LIMIT=10    # Mínimo necessário")
    
    print("\n📈 Tabelas disponíveis no seu banco:")
    print("  - memoria (atual)")
    print("  - chatmemoria")
    print("  - chatmemoria2")
    print("  - basemercadaoklkgg")
    print("  - dados_cliente")
    print("  - n8n_chat_histories")
    
    print("\n✅ Resumo da implementação:")
    print("-" * 30)
    print("✅ Tabela configurável via POSTGRES_TABLE_NAME")
    print("✅ Limite configurável via POSTGRES_MESSAGE_LIMIT")
    print("✅ Todas as mensagens permanecem no banco")
    print("✅ Agente usa apenas mensagens recentes")
    print("✅ Sem necessidade de alterar código")
    
    print("\n🔧 Para aplicar mudanças:")
    print("1. Edite o arquivo .env")
    print("2. Reinicie o servidor/agente")
    print("3. Pronto! Novas configurações ativas")

if __name__ == "__main__":
    demonstrate_full_env_config()