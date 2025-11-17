"""
Script de validação da estrutura do projeto
Verifica se todos os componentes estão corretamente configurados
"""
import sys
import os
from pathlib import Path

def check_file_exists(filepath: str, description: str) -> bool:
    """Verifica se um arquivo existe"""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description} não encontrado: {filepath}")
        return False

def check_directory_exists(dirpath: str, description: str) -> bool:
    """Verifica se um diretório existe"""
    if Path(dirpath).is_dir():
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description} não encontrado: {dirpath}")
        return False

def check_imports() -> bool:
    """Verifica se as importações principais funcionam"""
    print("\n📦 Verificando importações...")
    
    all_ok = True
    
    # Config
    try:
        from config.settings import settings
        print("✅ config.settings importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar config.settings: {e}")
        all_ok = False
    
    # Tools
    try:
        from tools.time_tool import get_current_time
        print("✅ tools.time_tool importado com sucesso")
    except Exception as e:
        print(f"❌ Erro ao importar tools.time_tool: {e}")
        all_ok = False
    
    # Agent (pode falhar se .env não estiver configurado)
    try:
        import agent
        print("✅ agent importado com sucesso")
    except Exception as e:
        print(f"⚠️ Aviso ao importar agent (pode ser normal se .env não estiver configurado): {e}")
    
    return all_ok

def main():
    """Função principal de validação"""
    print("=" * 60)
    print("🔍 VALIDAÇÃO DO PROJETO - AGENTE DE SUPERMERCADO")
    print("=" * 60)
    
    all_checks_passed = True
    
    # Verificar arquivos principais
    print("\n📄 Verificando arquivos principais...")
    all_checks_passed &= check_file_exists("agent.py", "Agente principal")
    all_checks_passed &= check_file_exists("server.py", "Servidor FastAPI")
    all_checks_passed &= check_file_exists("test_agent.py", "Script de teste")
    all_checks_passed &= check_file_exists("requirements.txt", "Dependências")
    all_checks_passed &= check_file_exists("README.md", "Documentação")
    all_checks_passed &= check_file_exists("Dockerfile", "Dockerfile")
    all_checks_passed &= check_file_exists("docker-compose.yml", "Docker Compose")
    all_checks_passed &= check_file_exists(".env.example", "Exemplo de .env")
    
    # Verificar diretórios
    print("\n📁 Verificando diretórios...")
    all_checks_passed &= check_directory_exists("config", "Diretório de configuração")
    all_checks_passed &= check_directory_exists("tools", "Diretório de ferramentas")
    all_checks_passed &= check_directory_exists("logs", "Diretório de logs")
    
    # Verificar arquivos de configuração
    print("\n⚙️ Verificando módulos de configuração...")
    all_checks_passed &= check_file_exists("config/__init__.py", "Config __init__")
    all_checks_passed &= check_file_exists("config/settings.py", "Settings")
    all_checks_passed &= check_file_exists("config/logger.py", "Logger")
    
    # Verificar ferramentas
    print("\n🔧 Verificando ferramentas...")
    all_checks_passed &= check_file_exists("tools/__init__.py", "Tools __init__")
    all_checks_passed &= check_file_exists("tools/http_tools.py", "HTTP Tools")
    all_checks_passed &= check_file_exists("tools/redis_tools.py", "Redis Tools")
    all_checks_passed &= check_file_exists("tools/time_tool.py", "Time Tool")
    all_checks_passed &= check_file_exists("tools/kb_tools.py", "Knowledge Base Tool")
    
    # Verificar importações
    imports_ok = check_imports()
    
    # Verificar .env
    print("\n🔐 Verificando configuração de ambiente...")
    if Path(".env").exists():
        print("✅ Arquivo .env encontrado")
        print("⚠️ IMPORTANTE: Verifique se todas as credenciais estão preenchidas!")
    else:
        print("⚠️ Arquivo .env não encontrado")
        print("💡 Copie .env.example para .env e preencha as credenciais:")
        print("   cp .env.example .env")
    
    # Resultado final
    print("\n" + "=" * 60)
    if all_checks_passed and imports_ok:
        print("✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)
        print("\n📝 Próximos passos:")
        print("1. Configure o arquivo .env com suas credenciais")
        print("2. Execute: python test_agent.py (para testar localmente)")
        print("3. Execute: python server.py (para iniciar o servidor)")
        print("4. Ou use: docker-compose up -d (para deploy completo)")
        return 0
    else:
        print("❌ VALIDAÇÃO FALHOU - Verifique os erros acima")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
