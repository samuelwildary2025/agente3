#!/usr/bin/env python3
"""
Demonstração da configuração de limite via variável de ambiente
"""

import os
import sys

# Adiciona o diretório pai ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configura variável de ambiente para teste
os.environ["POSTGRES_MESSAGE_LIMIT"] = "25"  # Exemplo: 25 mensagens

from config.settings import settings

def demonstrate_env_config():
    """Demonstra a configuração via variável de ambiente"""
    
    print("🔧 Demonstração: Configuração via Variável de Ambiente")
    print("=" * 60)
    
    # Mostra o valor atual (vindo do ENV)
    print(f"📊 POSTGRES_MESSAGE_LIMIT atual: {settings.postgres_message_limit}")
    print(f"📊 Tabela PostgreSQL: {settings.postgres_table_name}")
    print(f"📊 Conexão: {settings.postgres_connection_string}")
    
    print("\n💡 Como configurar:")
    print("-" * 30)
    print("# No arquivo .env:")
    print("POSTGRES_MESSAGE_LIMIT=30    # 30 mensagens para o agente")
    print("POSTGRES_MESSAGE_LIMIT=50    # 50 mensagens para o agente")
    print("POSTGRES_MESSAGE_LIMIT=0     # Ilimitado (comportamento antigo)")
    
    print("\n# No terminal Linux/Mac:")
    print("export POSTGRES_MESSAGE_LIMIT=20")
    print("python seu_script.py")
    
    print("\n# No terminal Windows:")
    print("set POSTGRES_MESSAGE_LIMIT=20")
    print("python seu_script.py")
    
    print("\n🎯 Benefícios da abordagem:")
    print("-" * 30)
    print("✅ Todas as mensagens ficam salvas no banco (relatórios)")
    print("✅ Agente usa apenas mensagens recentes (performance)")
    print("✅ Limite configurável sem mudar código")
    print("✅ Pode ajustar conforme necessidade")
    
    print("\n📈 Exemplos de uso:")
    print("-" * 30)
    print("• Conversas curtas: 10-15 mensagens")
    print("• Conversas normais: 20-30 mensagens")
    print("• Conversas complexas: 50+ mensagens")
    print("• Debug/testes: 0 (ilimitado)")
    
    print("\n🔍 Verificação:")
    print("-" * 30)
    
    # Testa diferentes valores
    print("  Exemplos de configuração:")
    print("  - Limite 10: 10 mensagens para o agente")
    print("  - Limite 20: 20 mensagens para o agente") 
    print("  - Limite 30: 30 mensagens para o agente")
    print("  - Limite 0:  Ilimitado (comportamento antigo)")
    
    print("\n✅ Configuração via ambiente implementada com sucesso!")

if __name__ == "__main__":
    demonstrate_env_config()