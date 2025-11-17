#!/usr/bin/env python3
"""
Verificar onde está o create_openai_tools_agent na nova versão
"""

try:
    from langchain_openai import create_openai_tools_agent
    print("✅ create_openai_tools_agent disponível em langchain_openai")
except ImportError as e:
    print(f"❌ Erro ao importar create_openai_tools_agent de langchain_openai: {e}")

try:
    from langchain.agents import create_openai_tools_agent
    print("✅ create_openai_tools_agent disponível em langchain.agents")
except ImportError as e:
    print(f"❌ Erro ao importar create_openai_tools_agent de langchain.agents: {e}")

try:
    from langchain_core.agents import create_openai_tools_agent
    print("✅ create_openai_tools_agent disponível em langchain_core.agents")
except ImportError as e:
    print(f"❌ Erro ao importar create_openai_tools_agent de langchain_core.agents: {e}")

# Verificar também o create_tool_calling_agent
try:
    from langchain.agents import create_tool_calling_agent
    print("✅ create_tool_calling_agent disponível")
except ImportError as e:
    print(f"❌ Erro ao importar create_tool_calling_agent: {e}")

try:
    from langchain_openai import create_tool_calling_agent
    print("✅ create_tool_calling_agent disponível em langchain_openai")
except ImportError as e:
    print(f"❌ Erro ao importar create_tool_calling_agent de langchain_openai: {e}")