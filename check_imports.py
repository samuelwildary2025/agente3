#!/usr/bin/env python3
"""
Verificar imports disponíveis do LangChain
"""

try:
    from langchain.agents import AgentExecutor, create_openai_tools_agent
    print("✅ AgentExecutor e create_openai_tools_agent disponíveis")
except ImportError as e:
    print(f"❌ Erro ao importar AgentExecutor: {e}")
    
try:
    from langchain.agents import create_tool_calling_agent
    print("✅ create_tool_calling_agent disponível")
except ImportError as e:
    print(f"❌ Erro ao importar create_tool_calling_agent: {e}")
    
try:
    from langchain.agents import AgentExecutor as AgentExecutorNew
    print("✅ AgentExecutor disponível com alias")
except ImportError as e:
    print(f"❌ Erro ao importar AgentExecutor com alias: {e}")

# Verificar o que tem disponível em langchain.agents
try:
    import langchain.agents as agents
    print(f"\n📦 Módulos disponíveis em langchain.agents:")
    print([attr for attr in dir(agents) if not attr.startswith('_')])
except Exception as e:
    print(f"❌ Erro ao verificar langchain.agents: {e}")