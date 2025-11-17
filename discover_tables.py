#!/usr/bin/env python3
"""
Script para descobrir as tabelas reais no PostgreSQL
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from config.settings import settings

def discover_tables():
    """Descobre todas as tabelas no PostgreSQL"""
    
    print("🔍 Descobrindo tabelas no PostgreSQL...")
    print(f"Conexão: {settings.postgres_connection_string}")
    print("-" * 60)
    
    try:
        # Connect to PostgreSQL
        with psycopg2.connect(settings.postgres_connection_string) as conn:
            with conn.cursor() as cursor:
                
                # Get all tables in public schema
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name;
                """)
                
                tables = cursor.fetchall()
                
                if not tables:
                    print("❌ Nenhuma tabela encontrada no schema 'public'!")
                    return
                
                print(f"✅ Encontradas {len(tables)} tabelas:")
                
                for table in tables:
                    table_name = table[0]
                    print(f"\n📋 Tabela: {table_name}")
                    
                    # Get column information for this table
                    cursor.execute("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'public' 
                        AND table_name = %s
                        ORDER BY ordinal_position;
                    """, (table_name,))
                    
                    columns = cursor.fetchall()
                    
                    print(f"  Colunas ({len(columns)}):")
                    for col in columns:
                        column_name, data_type, is_nullable = col
                        nullable_str = "NULL" if is_nullable == 'YES' else "NOT NULL"
                        print(f"    {column_name:<20} {data_type:<15} {nullable_str}")
                    
                    # Count rows in this table
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM "{table_name}";
                    """)
                    
                    row_count = cursor.fetchone()[0]
                    print(f"  Total de linhas: {row_count}")
                    
                    # Look for message-like columns
                    message_columns = [col[0] for col in columns if 'message' in col[0].lower() or 'session' in col[0].lower()]
                    if message_columns:
                        print(f"  🔍 Colunas relevantes: {message_columns}")
                
                # Check if there are any tables with 'message' in the name
                message_tables = [t[0] for t in tables if 'message' in t[0].lower()]
                if message_tables:
                    print(f"\n🎯 Tabelas com 'message' no nome: {message_tables}")
                
    except Exception as e:
        print(f"❌ Erro ao conectar ao PostgreSQL: {e}")

if __name__ == "__main__":
    discover_tables()