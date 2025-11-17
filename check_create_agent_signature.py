#!/usr/bin/env python3
"""
Verificar a assinatura correta do create_agent
"""

import inspect
from langchain.agents import create_agent

# Verificar a assinatura da função
signature = inspect.signature(create_agent)
print(f"Assinatura do create_agent: {signature}")

# Verificar documentação
print(f"\nDocumentação: {create_agent.__doc__}")

# Verificar parâmetros
print(f"\nParâmetros:")
for param_name, param in signature.parameters.items():
    print(f"  {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'} = {param.default if param.default != inspect.Parameter.empty else 'required'}")