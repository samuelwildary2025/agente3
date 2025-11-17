#!/usr/bin/env python3
"""
Script para inspecionar a estrutura real da tabela PostgreSQL
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from config.settings import settings

def inspect_table_structure():
    """Inspeciona a estrutura da tabela PostgreSQL"""
    
    print("🔍 Inspecionando estrutura da tabela PostgreSQL...")
    print(f"Tabela: {settings.postgres_table_name}")
    print(f"Conexão: {settings.postgres_connection_string}")
    print("-" * 60)
    
    try:
        # Connect to PostgreSQL
        with psycopg2.connect(settings.postgres_connection_string) as conn:
            with conn.cursor() as cursor:
                
                # Check if table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                    );
                """, (settings.postgres_table_name,))
                
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    print(f"❌ Tabela '{settings.postgres_table_name}' não existe!")
                    return
                
                print(f"✅ Tabela '{settings.postgres_table_name}' encontrada!")
                
                # Get column information
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                    ORDER BY ordinal_position;
                """, (settings.postgres_table_name,))
                
                columns = cursor.fetchall()
                
                print(f"\n📋 Colunas da tabela ({len(columns)} colunas):")
                print("-" * 60)
                for col in columns:
                    column_name, data_type, is_nullable, column_default = col
                    print(f"  {column_name:<20} {data_type:<15} {'NULL' if is_nullable == 'YES' else 'NOT NULL':<8} {column_default or ''}")
                
                # Get sample data
                print(f"\n📝 Amostra de dados (primeiras 5 linhas):")
                print("-" * 60)
                
                cursor.execute(f"""
                    SELECT * FROM {settings.postgres_table_name}
                    LIMIT 5;
                """)
                
                rows = cursor.fetchall()
                
                if not rows:
                    print("  (tabela vazia)")
                else:
                    # Get column names for header
                    col_names = [desc[0] for desc in cursor.description]
                    print("  " + " | ".join(col_names))
                    print("  " + "-" * (len(" | ".join(col_names))))
                    
                    for row in rows:
                        print("  " + " | ".join(str(val)[:20] for val in row))
                
                # Count total messages
                cursor.execute(f"""
                    SELECT COUNT(*) FROM {settings.postgres_table_name};
                """)
                
                total_count = cursor.fetchone()[0]
                print(f"\n📊 Estatísticas:")
                print(f"  → Total de mensagens: {total_count}")
                
                # Count messages per session
                cursor.execute(f"""
                    SELECT session_id, COUNT(*) as message_count
                    FROM {settings.postgres_table_name}
                    GROUP BY session_id
                    ORDER BY message_count DESC;
                """)
                
                sessions = cursor.fetchall()
                print(f"  → Sessões ativas: {len(sessions)}")
                
                for session_id, count in sessions:
                    print(f"    {session_id}: {count} mensagens")
                
                # Check for created_at or timestamp columns
                timestamp_columns = [col[0] for col in columns if 'time' in col[0].lower() or 'created' in col[0].lower()]
                if timestamp_columns:
                    print(f"  → Colunas de timestamp encontradas: {timestamp_columns}")
                else:
                    print("  → ⚠️  Nenhuma coluna de timestamp encontrada!")
                
    except Exception as e:
        print(f"❌ Erro ao conectar ao PostgreSQL: {e}")

if __name__ == "__main__":
    inspect_table_structure()