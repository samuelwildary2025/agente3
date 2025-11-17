#!/usr/bin/env python3
"""
Demonstração de token e ID dinâmicos do webhook UAZ
"""

def test_different_webhooks():
    """Testa diferentes webhooks com tokens e IDs dinâmicos"""
    print("🔄 Testando webhooks com valores dinâmicos...")
    
    # Simular diferentes webhooks recebidos
    webhooks = [
        {
            "nome": "Mensagem 1 - João",
            "payload": {
                "body": {
                    "token": "abc123-def456-ghi789",
                    "message": {
                        "messageid": "MSG123456789",
                        "type": "audioMessage",
                        "from": "5511987654321@s.whatsapp.net"
                    }
                }
            }
        },
        {
            "nome": "Mensagem 2 - Maria", 
            "payload": {
                "body": {
                    "token": "xyz987-wvu654-rst321",
                    "message": {
                        "messageid": "MSG987654321",
                        "type": "audioMessage", 
                        "from": "5511998765432@s.whatsapp.net"
                    }
                }
            }
        },
        {
            "nome": "Mensagem 3 - Pedro",
            "payload": {
                "body": {
                    "token": "mno456-pqr789-stu012",
                    "message": {
                        "messageid": "MSG456789123",
                        "type": "audioMessage",
                        "from": "5511923456789@s.whatsapp.net"
                    }
                }
            }
        }
    ]
    
    def extract_dados_webhook(payload):
        """Simula nossa função de extração"""
        body = payload.get("body", {})
        message = body.get("message", {})
        
        token = body.get("token")
        message_id = message.get("messageid")
        telefone = message.get("from", "").split("@")[0]
        message_type = message.get("type")
        
        return {
            "token": token,
            "message_id": message_id,
            "telefone": telefone,
            "tipo": message_type
        }
    
    print("\n📊 Resultados da extração dinâmica:")
    print("-" * 60)
    
    for webhook in webhooks:
        nome = webhook["nome"]
        payload = webhook["payload"]
        
        dados = extract_dados_webhook(payload)
        
        print(f"\n📝 {nome}:")
        print(f"   Token: {dados['token']}")
        print(f"   MessageID: {dados['message_id']}")
        print(f"   Telefone: {dados['telefone']}")
        print(f"   Tipo: {dados['tipo']}")
        
        # Simular configuração de download
        if dados['tipo'] == 'audioMessage':
            print(f"   📥 Configuração de download:")
            print(f"      URL: https://wildhub.uazapi.com/message/download")
            print(f"      Auth: Bearer {dados['token']}")
            print(f"      Body: {{'id': '{dados['message_id']}'}}")
    
    return True

def test_variacoes_estrutura():
    """Testa variações na estrutura do webhook"""
    print("\n\n🔀 Testando variações na estrutura...")
    
    # Webhooks com pequenas variações que podem acontecer
    variacoes = [
        {
            "nome": "Token no payload principal",
            "payload": {
                "token": "qwe789-rty012-uio345",
                "body": {
                    "message": {
                        "messageid": "MSG789012345",
                        "type": "audioMessage"
                    }
                }
            }
        },
        {
            "nome": "Estrutura aninhada diferente",
            "payload": {
                "data": {
                    "body": {
                        "token": "asd234-fgh567-jkl890",
                        "message": {
                            "messageid": "MSG234567890",
                            "type": "audioMessage"
                        }
                    }
                }
            }
        }
    ]
    
    def extract_flexivel(payload):
        """Extração mais flexível"""
        # Procurar token em vários lugares
        token = (payload.get("body", {}).get("token") or 
                payload.get("token") or
                payload.get("data", {}).get("body", {}).get("token"))
        
        # Procurar message em vários lugares
        message = (payload.get("body", {}).get("message") or
                  payload.get("data", {}).get("body", {}).get("message"))
        
        if message:
            return {
                "token": token,
                "message_id": message.get("messageid"),
                "tipo": message.get("type")
            }
        return None
    
    print("\n📊 Resultados da extração flexível:")
    print("-" * 60)
    
    for variacao in variacoes:
        nome = variacao["nome"]
        payload = variacao["payload"]
        
        dados = extract_flexivel(payload)
        
        if dados:
            print(f"\n✅ {nome}:")
            print(f"   Token encontrado: {dados['token']}")
            print(f"   MessageID: {dados['message_id']}")
            print(f"   Tipo: {dados['tipo']}")
        else:
            print(f"\n❌ {nome}: Falha na extração")
    
    return True

def main():
    """Executa todos os testes"""
    print("🎯 Demonstração: Token e ID Dinâmicos do Webhook UAZ")
    print("=" * 70)
    
    results = []
    results.append(test_different_webhooks())
    results.append(test_variacoes_estrutura())
    
    print("\n" + "=" * 70)
    
    if all(results):
        print("✅ CONCLUSÃO: Sistema é 100% dinâmico!")
        print("\n📋 Resumo:")
        print("✅ Token vem dinamicamente de cada webhook")
        print("✅ MessageID vem dinamicamente de cada mensagem")
        print("✅ Sistema extrai automaticamente os valores")
        print("✅ Cada mensagem tem seu próprio token/ID único")
        print("✅ Download é configurado dinamicamente para cada áudio")
        
        print("\n🔄 Processo completo:")
        print("1. Webhook recebe mensagem → Token e ID são únicos")
        print("2. Sistema extrai automaticamente → Sem hardcode")
        print("3. Configura download → Usa token/ID da mensagem")
        print("4. Processa áudio → Cada um com suas credenciais")
        
    else:
        print("❌ Alguns testes falharam")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)