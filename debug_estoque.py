#!/usr/bin/env python3
"""
Teste para debugar o que está vindo da API de estoque/preco
"""

import os
import requests
import json
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def debug_estoque_preco():
    """Debug detalhado da API de estoque/preço"""
    
    base_url = os.getenv("ESTOQUE_EAN_BASE_URL")
    ean = "7896220900359"  # Arroz Alteza 1kg que você testou
    
    url = f"{base_url}/{ean}"
    
    print(f"🌐 URL: {url}")
    
    try:
        response = requests.get(url, headers={"Accept": "application/json"}, timeout=10)
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Headers: {dict(response.headers)}")
        print(f"📨 Response Raw: {response.text[:1000]}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ JSON Parseado: {json.dumps(data, indent=2, ensure_ascii=False)}")
                
                # Analisar campos disponíveis
                if isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    print(f"\n🔍 Campos disponíveis no primeiro item:")
                    for key, value in item.items():
                        print(f"  - {key}: {value} (tipo: {type(value).__name__})")
                        
                    # Verificar se tem os campos que o código procura
                    campos_preco = ["vl_produto", "vl_produto_normal", "preco", "preco_venda", "valor", "valor_unitario", "preco_unitario", "atacadoPreco"]
                    campos_estoque = ["estoque", "qtd", "qtde", "qtd_estoque", "quantidade", "quantidade_disponivel", "qtdDisponivel", "qtdEstoque", "estoqueAtual", "saldo"]
                    campos_status = ["situacao", "situacaoEstoque", "status", "statusEstoque", "disponibilidade", "disponivel"]
                    
                    print(f"\n💰 Campos de PREÇO encontrados:")
                    for campo in campos_preco:
                        if campo in item:
                            print(f"  ✅ {campo}: {item[campo]}")
                            
                    print(f"\n📦 Campos de ESTOQUE encontrados:")
                    for campo in campos_estoque:
                        if campo in item:
                            print(f"  ✅ {campo}: {item[campo]}")
                            
                    print(f"\n📋 Campos de STATUS encontrados:")
                    for campo in campos_status:
                        if campo in item:
                            print(f"  ✅ {campo}: {item[campo]}")
                            
                    # Testar disponibilidade
                    tem_preco = any(campo in item for campo in campos_preco)
                    tem_estoque = any(campo in item for campo in campos_estoque)
                    tem_status_positivo = False
                    
                    if "ativo" in item and item["ativo"] == True:
                        tem_status_positivo = True
                        
                    print(f"\n📊 Análise de disponibilidade:")
                    print(f"  - Tem campos de preço: {tem_preco}")
                    print(f"  - Tem campos de estoque: {tem_estoque}")
                    print(f"  - Tem status positivo (ativo=true): {tem_status_positivo}")
                    
                else:
                    print(f"⚠️  Data não é lista ou está vazia: {type(data)}")
                    
            except json.JSONDecodeError as e:
                print(f"❌ Erro ao parsear JSON: {e}")
                
        else:
            print(f"❌ Erro: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    print("🧪 Debug detalhado da API de Estoque/Preço...")
    print("=" * 60)
    debug_estoque_preco()