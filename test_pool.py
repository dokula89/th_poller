import mysql.connector
from mysql.connector import pooling

config = {
    'host': '172.104.206.182',
    'port': 3306,
    'user': 'seattlelisted_usr',
    'password': 'T@5z6^pl}',
    'database': 'offta',
    'connect_timeout': 10
}

print('Testing direct connection...')
try:
    conn = mysql.connector.connect(**config)
    print(f'  Direct connection: SUCCESS')
    conn.close()
except Exception as e:
    print(f'  Direct connection FAILED: {e}')

print('Testing connection pool...')
try:
    pool = pooling.MySQLConnectionPool(
        pool_name='test_pool',
        pool_size=5,
        pool_reset_session=True,
        **config
    )
    print(f'  Pool created: SUCCESS')
    conn = pool.get_connection()
    print(f'  Got connection from pool: SUCCESS')
    conn.close()
except Exception as e:
    print(f'  Pool FAILED: {e}')
