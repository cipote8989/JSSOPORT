import psycopg2

def conectar():
    try:
        conexion = psycopg2.connect(
            user="postgres",
            password="123456",
            host="localhost",
            port="5432",
            database="tienda"
        )
        return conexion
    except (Exception, psycopg2.Error) as error:
        print("Error al conectar a PostgreSQL:", error)
        return None

def desconectar(conexion):
    if conexion is not None:
        conexion.close()
        print("Conexión a PostgreSQL cerrada")



conexion = conectar()

if conexion is not None:
    print("Conexión a PostgreSQL establecida correctamente")
    
    desconectar(conexion)  
else:
    print("Error al conectar a PostgreSQL. No se pudo establecer la conexión.")
