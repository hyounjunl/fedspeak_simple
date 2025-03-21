import pg8000
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration from environment variables
DB_PARAMS = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = pg8000.connect(
            host=DB_PARAMS['host'],
            port=DB_PARAMS['port'],
            database=DB_PARAMS['database'],
            user=DB_PARAMS['user'],
            password=DB_PARAMS['password']
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise

def get_next_unlabeled_qna():
    """Get the next unlabeled QnA pair"""
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        # Get next unlabeled QnA with statement info
        cursor.execute("""
            SELECT q.id, q.questioner, q.question, q.responder, q.response, 
                   s.date, s.filename
            FROM fomc_qna q
            JOIN fomc_statements s ON q.statement_id = s.id
            WHERE q.is_labeled IS NOT TRUE OR q.is_labeled IS NULL
            ORDER BY RANDOM()
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        
        if not row:
            return None
            
        # Create a dictionary from the row
        result = {
            'id': row[0],
            'questioner': row[1],
            'question': row[2],
            'responder': row[3],
            'response': row[4],
            'date': row[5],  # Use the date directly without formatting
            'filename': row[6]
        }
        
        return result
    finally:
        cursor.close()
        conn.close()

        
def label_qna(qna_id, label_value, user_id):
    """Label a QnA pair and record the user who labeled it"""
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        # Convert boolean to text for the label column
        label_text = 'true' if label_value else 'false'
        
        # Update the QnA record
        cursor.execute("""
            UPDATE fomc_qna
            SET is_labeled = TRUE, 
                label = %s,
                labeled_by = %s,
                labeled_at = NOW()
            WHERE id = %s
        """, (label_text, user_id, qna_id))
        
        conn.commit()
        
        # Get the number of remaining unlabeled QnAs
        cursor.execute("""
            SELECT COUNT(*) FROM fomc_qna WHERE is_labeled IS NOT TRUE OR is_labeled IS NULL
        """)
        remaining = cursor.fetchone()[0]
        
        # Get labeling statistics for this user
        cursor.execute("""
            SELECT COUNT(*) FROM fomc_qna 
            WHERE labeled_by = %s
        """, (user_id,))
        user_count = cursor.fetchone()[0]
        
        return {
            'success': True,
            'remaining': remaining,
            'user_count': user_count
        }
    finally:
        cursor.close()
        conn.close()

def get_user_stats(user_id):
    """Get labeling statistics for a user"""
    conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        # Get total labeled by this user
        cursor.execute("""
            SELECT COUNT(*) FROM fomc_qna 
            WHERE labeled_by = %s
        """, (user_id,))
        total = cursor.fetchone()[0]
        
        # Use text comparison since label is a text field
        cursor.execute("""
            SELECT COUNT(*) FROM fomc_qna 
            WHERE labeled_by = %s AND label = 'true'
        """, (user_id,))
        relevant = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM fomc_qna 
            WHERE labeled_by = %s AND label = 'false'
        """, (user_id,))
        irrelevant = cursor.fetchone()[0]
        
        # Get overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_labeled = TRUE) as labeled,
                COUNT(*) FILTER (WHERE is_labeled IS NOT TRUE OR is_labeled IS NULL) as unlabeled
            FROM fomc_qna
        """)
        overall = cursor.fetchone()
        
        return {
            'user': {
                'total': total,
                'relevant': relevant,
                'irrelevant': irrelevant
            },
            'overall': {
                'total': overall[0],
                'labeled': overall[1],
                'unlabeled': overall[2]
            }
        }
    finally:
        cursor.close()
        conn.close()