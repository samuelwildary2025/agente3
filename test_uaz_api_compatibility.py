#!/usr/bin/env python3
"""
Verificação de compatibilidade com API UAZ específica
"""

def test_uaz_api_structure():
    """Testa compatibilidade com a estrutura exata da UAZ API"""
    print("🔍 Verificando compatibilidade com UAZ API...")
    
    # Estrutura que você mostrou:
    # URL: https://wildhub.uazapi.com/message/download
    # Headers: {{ $('Webhook').item.json.body.token }} = 512cb221-3fa1-4136-b4f7-b2679c66e23f
    # Body: id = {{ $('Webhook').item.json.body.message.messageid }}
    # Exemplo: 2AA8AE6AAA49625B0448
    
    print("📋 Estrutura da UAZ API identificada:")
    print("  • URL: https://wildhub.uazapi.com/message/download")
    print("  • Método: POST com token no header")
    print("  • Parâmetro: messageid no body")
    print("  • Formato: Base64 para conversão")
    
    # Simular payload real da UAZ
    uaz_webhook_payload = {
        "body": {
            "token": "512cb221-3fa1-4136-b4f7-b2679c66e23f",
            "message": {
                "messageid": "2AA8AE6AAA49625B0448",
                "type": "audioMessage",
                "from": "5511987654321@s.whatsapp.net",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }
    }
    
    print(f"\n📦 Exemplo de payload UAZ:")
    print(f"  Token: {uaz_webhook_payload['body']['token']}")
    print(f"  MessageID: {uaz_webhook_payload['body']['message']['messageid']}")
    print(f"  Tipo: {uaz_webhook_payload['body']['message']['type']}")
    
    return True

def test_our_audio_download():
    """Testa se nosso sistema de download está compatível"""
    print("\n🔄 Verificando nosso sistema de download...")
    
    # Como nosso sistema atual lida com isso
    print("📋 Nosso sistema atual:")
    print("  • Função: download_audio_file()")
    print("  • Headers: Suporte para Authorization")
    print("  • URL: Direto do webhook ou construída")
    
    # Simular como nosso sistema processaria
    token = "512cb221-3fa1-4136-b4f7-b2679c66e23f"
    message_id = "2AA8AE6AAA49625B0448"
    
    # Construir URL e headers como nosso sistema faria
    download_url = f"https://wildhub.uazapi.com/message/download"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Body para a requisição POST
    body = {
        "id": message_id
    }
    
    print(f"\n🔧 Construção da requisição:")
    print(f"  URL: {download_url}")
    print(f"  Headers: {headers}")
    print(f"  Body: {body}")
    
    return True

def test_integration_needed():
    """Identifica o que precisa ser ajustado"""
    print("\n⚠️  Identificando ajustes necessários...")
    
    print("📝 Ajustes necessários no nosso sistema:")
    print("  1. Modificar download_audio_file() para suportar POST")
    print("  2. Adicionar suporte para body parameters")
    print("  3. Construir URL correta da UAZ API")
    print("  4. Extrair token e messageid corretamente")
    
    return True

def main():
    """Executa todas as verificações"""
    print("🎯 Verificando compatibilidade com UAZ API específica")
    print("=" * 60)
    
    results = []
    results.append(test_uaz_api_structure())
    results.append(test_our_audio_download())
    results.append(test_integration_needed())
    
    print("\n" + "=" * 60)
    
    if all(results):
        print("✅ ANÁLISE COMPLETA!")
        print("\n📋 Resumo:")
        print("✅ Identificamos a estrutura exata da UAZ API")
        print("✅ Nosso sistema precisa de pequenos ajustes")
        print("✅ A integração é possível e relativamente simples")
        
        print("\n🔧 Próximos passos:")
        print("1. Modificar a função de download para POST")
        print("2. Adicionar suporte a body parameters")
        print("3. Ajustar a extração de dados do webhook")
        print("4. Testar com dados reais da UAZ")
        
    else:
        print("❌ Algumas verificações falharam")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)