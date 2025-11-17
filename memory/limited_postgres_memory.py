from typing import List, Optional, Dict, Any
from langchain_community.chat_message_histories import PostgresChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.chat_history import BaseChatMessageHistory
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    # Fallback para psycopg 3.x
    import psycopg as psycopg2
    from psycog import sql
import datetime
import pytz
from config.settings import settings
from tools.time_tool import format_timestamp, get_time_diff_description


class LimitedPostgresChatMessageHistory(BaseChatMessageHistory):
    """PostgreSQL chat message history that stores all messages but limits agent context to recent messages."""
    
    def __init__(
        self,
        session_id: str,
        connection_string: str,
        table_name: str = "message_store",
        max_messages: int = 20,
        **kwargs
    ):
        """
        Initialize limited PostgreSQL chat history.
        
        Args:
            session_id: Unique identifier for the chat session
            connection_string: PostgreSQL connection string
            table_name: Name of the table to store messages
            max_messages: Maximum number of recent messages to return to the agent (default: 20)
        """
        self.session_id = session_id
        self.connection_string = connection_string
        self.table_name = table_name
        self.max_messages = max_messages
        
        # Initialize the base PostgreSQL history (stores all messages)
        self._postgres_history = PostgresChatMessageHistory(
            session_id=session_id,
            connection_string=connection_string,
            table_name=table_name,
            **kwargs
        )
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Get optimized messages for the agent context."""
        return self.get_optimized_context()
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the database (all messages are stored)."""
        self._postgres_history.add_message(message)
        # No limit enforcement - all messages are stored for reporting
    
    def clear(self) -> None:
        """Clear all messages for this session."""
        self._postgres_history.clear()
    
    def _enforce_message_limit(self) -> None:
        """Keep only the most recent max_messages messages."""
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    # Get message IDs ordered by ID (oldest first)
                    cursor.execute(f"""
                        SELECT id FROM {self.table_name}
                        WHERE session_id = %s
                        ORDER BY id ASC
                    """, (self.session_id,))
                    
                    message_ids = cursor.fetchall()
                    
                    # If we have more messages than the limit, delete the oldest ones
                    if len(message_ids) > self.max_messages:
                        messages_to_delete = len(message_ids) - self.max_messages
                        ids_to_delete = [msg[0] for msg in message_ids[:messages_to_delete]]
                        
                        cursor.execute(f"""
                            DELETE FROM {self.table_name}
                            WHERE id = ANY(%s)
                        """, (ids_to_delete,))
                        
                        conn.commit()
                        
                        print(f"Limited messages for session {self.session_id}: "
                              f"deleted {messages_to_delete} oldest messages, "
                              f"keeping {self.max_messages} most recent")
                              
        except Exception as e:
            print(f"Error enforcing message limit: {e}")
    
    def get_message_count(self) -> int:
        """Get the current number of messages for this session."""
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM {self.table_name}
                        WHERE session_id = %s
                    """, (self.session_id,))
                    
                    return cursor.fetchone()[0]
        except Exception as e:
            print(f"Error getting message count: {e}")
            return 0
    
    def get_session_info(self) -> dict:
        """Get information about the current session."""
        return {
            "session_id": self.session_id,
            "message_count": self.get_message_count(),
            "max_messages": self.max_messages,
            "table_name": self.table_name
        }
    
    def should_clear_context(self, recent_messages: List[BaseMessage]) -> bool:
        """
        Determine if context should be cleared based on recent messages.
        Returns True if agent is struggling to identify products.
        """
        if len(recent_messages) < 3:
            return False
            
        # Check if last few messages show agent confusion
        confusion_patterns = [
            "não identifiquei",
            "não consegui identificar",
            "informar o nome principal",
            "desculpe, não",
            "pode informar"
        ]
        
        recent_text = " ".join([msg.content.lower() for msg in recent_messages[-3:]])
        
        confusion_count = sum(1 for pattern in confusion_patterns if pattern in recent_text)
        
        # If 2+ confusion patterns in last 3 messages, suggest clearing
        return confusion_count >= 2
    
    def get_messages_with_timestamp_info(self) -> List[Dict[str, Any]]:
        """
        Recupera mensagens com informações de timestamp do banco de dados.
        
        Returns:
            Lista de dicionários com mensagem e informações de tempo
        """
        try:
            with psycopg2.connect(self.connection_string) as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(f"""
                        SELECT message, created_at 
                        FROM {self.table_name}
                        WHERE session_id = %s
                        ORDER BY id ASC
                    """, (self.session_id,))
                    
                    results = cursor.fetchall()
                    
                    # Processar cada mensagem com informações de tempo
                    processed_messages = []
                    current_time = datetime.datetime.now(pytz.utc)
                    
                    for result in results:
                        message_data = result['message']
                        created_at = result['created_at']
                        
                        # Converter created_at para datetime se necessário
                        if isinstance(created_at, str):
                            created_at = datetime.datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        
                        # Formatar timestamp
                        formatted_time = format_timestamp(created_at)
                        time_diff = get_time_diff_description(current_time, created_at)
                        
                        processed_messages.append({
                            'message': message_data,
                            'created_at': created_at,
                            'formatted_time': formatted_time,
                            'time_ago': time_diff
                        })
                    
                    return processed_messages
                    
        except Exception as e:
            print(f"Erro ao recuperar mensagens com timestamp: {e}")
            return []
    
    def get_time_aware_context(self) -> List[BaseMessage]:
        """
        Retorna mensagens contextuais com informações de tempo para o agente.
        """
        messages_with_time = self.get_messages_with_timestamp_info()
        
        if not messages_with_time:
            return []
        
        # Pegar as mensagens recentes (últimas max_messages)
        recent_messages = messages_with_time[-self.max_messages:]
        
        # Converter de volta para BaseMessage com informações de tempo
        base_messages = []
        
        for msg_info in recent_messages:
            message_data = msg_info['message']
            time_ago = msg_info['time_ago']
            formatted_time = msg_info['formatted_time']
            
            # Recriar a mensagem original
            if message_data.get('type') == 'human':
                original_msg = HumanMessage(content=message_data.get('content', ''))
            elif message_data.get('type') == 'ai':
                original_msg = AIMessage(content=message_data.get('content', ''))
            elif message_data.get('type') == 'system':
                original_msg = SystemMessage(content=message_data.get('content', ''))
            else:
                # Tentar determinar tipo pela estrutura
                if 'HumanMessage' in str(message_data):
                    original_msg = HumanMessage(content=message_data.get('content', ''))
                elif 'AIMessage' in str(message_data):
                    original_msg = AIMessage(content=message_data.get('content', ''))
                else:
                    original_msg = BaseMessage(content=message_data.get('content', ''))
            
            # Adicionar metadata com informações de tempo
            original_msg.additional_kwargs['timestamp'] = formatted_time
            original_msg.additional_kwargs['time_ago'] = time_ago
            
            base_messages.append(original_msg)
        
        return base_messages
    
    def get_optimized_context(self) -> List[BaseMessage]:
        """
        Get optimized context for product identification.
        Focuses on recent product-related messages.
        """
        # Usar contexto com informações de tempo
        time_aware_messages = self.get_time_aware_context()
        
        if not time_aware_messages:
            # Fallback para método original
            all_messages = self._postgres_history.messages
            
            if len(all_messages) <= self.max_messages:
                return all_messages
            
            # Get recent messages
            recent_messages = all_messages[-self.max_messages:]
            
            # Check if we should clear context due to confusion
            if self.should_clear_context(recent_messages):
                print(f"🔄 Detectada confusão do agente. Recomendação: limpar contexto para {self.session_id}")
                # Return only the very last messages to reset context
                return recent_messages[-3:]  # Only last 3 messages
            
            return recent_messages
        
        return time_aware_messages