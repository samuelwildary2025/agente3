#!/usr/bin/env python3
"""
Verificar os novos imports corretos do LangChain
"""

try:
    from langchain.agents import create_agent
    print("✅ create_agent disponível")
except ImportError as e:
    print(f"❌ Erro ao importar create_agent: {e}")

try:
    from langchain_core.agents import AgentExecutor
    print("✅ AgentExecutor disponível em langchain_core.agents")
except ImportError as e:
    print(f"❌ Erro ao importar AgentExecutor de langchain_core.agents: {e}")

try:
    from langchain import agents
    print(f"\n📦 Módulos disponíveis em langchain.agents:")
    print([attr for attr in dir(agents) if not attr.startswith('_') and 'agent' in attr.lower()])
except Exception as e:
    print(f"❌ Erro ao verificar langchain.agents: {e}")

# Verificar langchain_core
try:
    import langchain_core.agents as core_agents
    print(f"\n📦 Módulos disponíveis em langchain_core.agents:")
    print([attr for attr in dir(core_agents) if not attr.startswith('_') and 'agent' in attr.lower()])
except Exception as e:
    print(f"❌ Erro ao verificar langchain_core.agents: {e}")