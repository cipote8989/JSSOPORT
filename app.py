from flask import Flask, request, render_template, redirect, url_for, flash, session
from config import conectar, desconectar
import psycopg2
import os
from werkzeug.utils import secure_filename
import qrcode
import random
import string
from datetime import datetime, timedelta
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = "tu_clave_secreta"

UPLOAD_FOLDER = os.path.join('static', 'img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuración de correo para Gmail
GMAIL_USER = 'trsa21j@gmail.com'  # <-- Cambia por tu correo
GMAIL_APP_PASSWORD = 'bdfw hunr gfea viym'  # <-- Cambia por tu contraseña de aplicación

# Ruta del login / registro
@app.route("/JS_SPORT/registrar", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        telefono = request.form["telefono"]
        nombrecll = request.form["nombrecll"]
        nombre = request.form["nombre"]
        direccion = request.form["direccion"]
        apellido = request.form["apellido"]
        correo = request.form["correo"]
        confirmar_correo = request.form.get("confirmar_correo")
        codigopt = request.form["codigopt"]
        numeroidn = request.form["numeroidn"]
        clave = request.form["clave"]
        confirmar_clave = request.form.get("confirmar_clave")
        
        # Validar campos vacíos (incluyendo codigopt)
        if not telefono or not nombrecll or not nombre or not direccion or not apellido or not correo or not numeroidn or not codigopt:
            flash("⚠️ Todos los campos son obligatorios")
            return redirect(url_for("registrar"))
        
        # Validar que los correos coincidan
        if correo != confirmar_correo:
            flash("❌ Los correos no coinciden")
            return redirect(url_for("registrar"))
        
        # Validar que las contraseñas coincidan
        if clave != confirmar_clave:
            flash("❌ Las contraseñas no coinciden")
            return redirect(url_for("registrar"))
        
        try:
            conexion = conectar()
            cursor = conexion.cursor()
            consulta = """ 
                INSERT INTO cliente (telefono, nombrecll, nombre, direccion, apellido, correo, codigopt, numeroidn, clave, estado)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, '1')
            """
            datos = (telefono, nombrecll, nombre, direccion, apellido, correo, codigopt, numeroidn, clave)
            cursor.execute(consulta, datos)
            conexion.commit()
            cursor.close()
            conexion.close()

            flash("✅ Fuiste registrado correctamente")
            return redirect(url_for("registrar"))
        except (Exception, psycopg2.Error) as error:
            print("Error al registrar el usuario:", error)
            flash("❌ Error al registrar el usuario")
            return redirect(url_for("registrar"))
    else:
        return render_template("registrar.html")

@app.route("/JS_SPORT/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        numeroidn = request.form.get("numeroidn")
        clave = request.form.get("clave")

        if not numeroidn or not clave:
            flash("⚠️ Número de identificación y contraseña son obligatorios")
            return redirect(url_for("login"))

        # Admin login
        if numeroidn == "123323" and clave == "putinreydelcaos":
            return redirect(url_for("admin_inicio"))

        try:
            conexion = conectar()
            cursor = conexion.cursor()
            consulta = """
                SELECT * FROM cliente WHERE numeroidn = %s AND clave = %s
            """
            cursor.execute(consulta, (numeroidn, clave))
            usuario = cursor.fetchone()
            cursor.close()
            conexion.close()
            if usuario:
                session['idc'] = usuario[0]  # Guardar idc en sesión
                return redirect(url_for("inicio"))
            else:
                flash("❌ Datos incorrectos")
                return redirect(url_for("login"))
        except (Exception, psycopg2.Error) as error:
            print("Error al iniciar sesión:", error)
            flash("❌ Error en el servidor")
            return redirect(url_for("login"))
    else:
        return render_template("login.html")

@app.route('/admin', methods=['GET', 'POST'])
def admin_inicio():
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT idp, nombre, marca, precio, talla, stock FROM producto")
        productos = [
            {
                'idp': row[0],
                'nombre': row[1],
                'marca': row[2],
                'precio': row[3],
                'talla': row[4],
                'stock': row[5]
            }
            for row in cursor.fetchall()
        ]
        cursor.execute("SELECT idc, nombre, apellido, correo FROM cliente")
        clientes = [
            {
                'idc': row[0],
                'nombre': row[1],
                'apellido': row[2],
                'correo': row[3]
            }
            for row in cursor.fetchall()
        ]
        # Denegar compras no confirmadas después de 2 días
        hoy = datetime.now().date()
        cursor.execute("SELECT idv, fecha, confirmada, estado FROM venta WHERE confirmada = false AND estado = '1'")
        pendientes = cursor.fetchall()
        for idv, fecha, confirmada, estado in pendientes:
            if (hoy - fecha).days > 2:
                cursor.execute("UPDATE venta SET estado = '0' WHERE idv = %s", (idv,))
        conexion.commit()
        # Historial de compras (ahora incluye confirmada y estado)
        cursor.execute('''
            SELECT v.idv, c.nombre, c.apellido, v.fecha, v.hora, v.total,
                   p.nombre, d.cantidad, d.subtotal, v.confirmada, v.estado
            FROM venta v
            JOIN cliente c ON v.fk_idc = c.idc
            JOIN dtventa d ON d.fk_idv = v.idv
            JOIN producto p ON d.fk_idp = p.idp
            ORDER BY v.fecha DESC, v.hora DESC
        ''')
        historial = cursor.fetchall()
        cursor.close()
        conexion.close()
    except Exception as e:
        productos = []
        clientes = []
        historial = []
        flash("Error al cargar datos: " + str(e))
    edit_idp = request.args.get('edit_idp')
    return render_template('adinicio.html', productos=productos, clientes=clientes, historial=historial, edit_idp=edit_idp)

@app.route('/admin/agregarcliente', methods=['GET', 'POST'])
def agregar_cliente():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        correo = request.form['correo']
        telefono = request.form['telefono']
        try:
            conexion = conectar()
            cursor = conexion.cursor()
            cursor.execute(
                "INSERT INTO cliente (telefono, nombrecll, nombre, direccion, apellido, correo, codigopt, numeroidn, clave, estado) VALUES (%s, '', %s, '', %s, %s, 0, 0, '', '1')",
                (telefono, nombre, apellido, correo)
            )
            conexion.commit()
            cursor.close()
            conexion.close()
            flash("Cliente agregado correctamente")
        except Exception as e:
            flash("Error al agregar cliente")
        return redirect(url_for('admin_inicio'))
    return render_template('agregarproducto.html')

@app.route('/admin/borrarcliente', methods=['POST'])
def borrar_cliente():
    idc = request.form['idc']
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("DELETE FROM cliente WHERE idc = %s", (idc,))
        conexion.commit()
        cursor.close()
        conexion.close()
        flash("Cliente borrado correctamente")
    except Exception as e:
        flash("Error al borrar cliente")
    return redirect(url_for('admin_inicio'))
    
@app.route('/admin/agregarproducto', methods=['POST'])
def agregar_producto():
    nombre = request.form['nombre']
    marca = request.form['marca']
    precio = request.form['precio']
    talla = request.form['talla']
    stock = request.form['stock']
    imagen_file = request.files['imagen']

    if imagen_file and imagen_file.filename != '':
        filename = secure_filename(imagen_file.filename)
        imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagen_file.save(imagen_path)
    else:
        filename = None

    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO producto (nombre, marca, estado, stock, precio, talla, imagen)
            VALUES (%s, %s, '1', %s, %s, %s, %s)
            """,
            (nombre, marca, stock, precio, talla, filename)
        )
        conexion.commit()
        cursor.close()
        conexion.close()
        flash("Producto agregado correctamente")
    except Exception as e:
        flash(f"Error al agregar producto: {str(e)}")
    return redirect(url_for('admin_inicio'))


@app.route('/admin/borrarproducto', methods=['GET', 'POST'])
def borrar_producto():
    if request.method == 'POST':
        idp = request.form['idp']
        try:
            conexion = conectar()
            cursor = conexion.cursor()
            cursor.execute("DELETE FROM producto WHERE idp = %s", (idp,))
            conexion.commit()
            cursor.close()
            conexion.close()
            flash("Producto borrado correctamente")
        except Exception as e:
            flash("Error al borrar producto")
        return redirect(url_for('admin_inicio'))
    return render_template('borrarproducto.html')

@app.route('/admin/gestionclientes')
def gestion_clientes():
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("SELECT idc, nombre, apellido, correo FROM cliente")
        clientes = cursor.fetchall()
        cursor.close()
        conexion.close()
    except Exception as e:
        clientes = []
    return render_template('gestionclientes.html', clientes=clientes)

@app.route('/inicio')
def inicio():
    query = request.args.get('query', '').strip()
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        # Productos disponibles
        if query:
            cursor.execute("""
                SELECT idp, nombre, marca, precio, talla, stock, imagen
                FROM producto
                WHERE estado = '1' AND LOWER(nombre) LIKE %s
            """, ('%' + query.lower() + '%',))
        else:
            cursor.execute("""
                SELECT idp, nombre, marca, precio, talla, stock, imagen
                FROM producto
                WHERE estado = '1'
            """)
        productos = [
            dict(idp=row[0], nombre=row[1], marca=row[2], precio=row[3], talla=row[4], stock=row[5], imagen=row[6])
            for row in cursor.fetchall()
        ]
        # Productos más vendidos (top 3)
        cursor.execute("""
            SELECT p.idp, p.nombre, p.marca, p.precio, p.talla, p.stock, p.imagen, SUM(d.cantidad) as total_vendido
            FROM producto p
            JOIN dtventa d ON p.idp = d.fk_idp
            WHERE p.estado = '1'
            GROUP BY p.idp, p.nombre, p.marca, p.precio, p.talla, p.stock, p.imagen
            ORDER BY total_vendido DESC
            LIMIT 3
        """)
        mas_vendidos = [
            dict(idp=row[0], nombre=row[1], marca=row[2], precio=row[3], talla=row[4], stock=row[5], imagen=row[6], total_vendido=row[7])
            for row in cursor.fetchall()
        ]
        cursor.close()
        conexion.close()
    except Exception as e:
        productos = []
        mas_vendidos = []
    carrito = session.get('carrito', [])
    return render_template('index.html', productos=productos, mas_vendidos=mas_vendidos, carrito=carrito)

@app.route('/admin/modificarproducto/<int:idp>', methods=['POST'])
def modificar_producto(idp):
    nombre = request.form['nombre']
    marca = request.form['marca']
    precio = int(request.form['precio'])
    talla = request.form['talla']
    stock = request.form['stock']
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("""
            UPDATE producto
            SET nombre=%s, marca=%s, precio=%s, talla=%s, stock=%s
            WHERE idp=%s
        """, (nombre, marca, precio, talla, stock, idp))
        conexion.commit()
        cursor.close()
        conexion.close()
        flash("Producto modificado correctamente")
    except Exception as e:
        flash(f"Error al modificar producto: {str(e)}")
    return redirect(url_for('admin_inicio'))

@app.route('/agregar_carrito/<int:idp>', methods=['POST'])
def agregar_carrito(idp):
    cantidad = int(request.form.get('cantidad', 1))
    if 'carrito' not in session:
        session['carrito'] = []
    # Buscar si ya está el producto en el carrito
    for item in session['carrito']:
        if item['idp'] == idp:
            item['cantidad'] += cantidad
            break
    else:
        session['carrito'].append({'idp': idp, 'cantidad': cantidad})
    session.modified = True
    flash("Producto agregado al carrito")
    return redirect(url_for('inicio'))

@app.route('/carrito', methods=['GET', 'POST'])
def ver_carrito():
    carrito = session.get('carrito', [])
    productos = []
    total = 0
    if carrito:
        conexion = conectar()
        cursor = conexion.cursor()
        for item in carrito:
            cursor.execute("SELECT idp, nombre, marca, precio, talla, stock FROM producto WHERE idp = %s", (item['idp'],))
            prod = cursor.fetchone()
            if prod:
                subtotal = prod[3] * item['cantidad']
                total += subtotal
                productos.append({
                    'idp': prod[0],
                    'nombre': prod[1],
                    'marca': prod[2],
                    'precio': prod[3],
                    'talla': prod[4],
                    'stock': prod[5],
                    'cantidad': item['cantidad'],
                    'subtotal': subtotal
                })
        cursor.close()
        conexion.close()
    return render_template('carrito.html', productos=productos, total=total)

@app.route('/actualizar_carrito', methods=['POST'])
def actualizar_carrito():
    cantidades = request.form.getlist('cantidad')
    idps = request.form.getlist('idp')
    carrito = []
    for idp, cantidad in zip(idps, cantidades):
        carrito.append({'idp': int(idp), 'cantidad': int(cantidad)})
    session['carrito'] = carrito
    session.modified = True
    return redirect(url_for('ver_carrito'))

@app.route('/comprar', methods=['POST'])
def comprar():
    carrito = session.get('carrito', [])
    productos = []
    total = 0
    from datetime import datetime
    idc = session.get('idc')
    if not idc:
        flash("Debes iniciar sesión para comprar")
        return redirect(url_for('login'))
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        for item in carrito:
            cursor.execute("SELECT nombre, precio, stock FROM producto WHERE idp = %s", (item['idp'],))
            prod = cursor.fetchone()
            if not prod or prod[2] < item['cantidad']:
                flash(f"Stock insuficiente para el producto ID {item['idp']}")
                conexion.rollback()
                cursor.close()
                conexion.close()
                return redirect(url_for('ver_carrito'))
            subtotal = prod[1] * item['cantidad']
            total += subtotal
            productos.append({
                'idp': item['idp'],
                'nombre': prod[0],
                'precio': prod[1],
                'cantidad': item['cantidad'],
                'subtotal': subtotal
            })
        # Generar código de compra único
        codigo_compra = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        # Insertar en venta (agregar campo codigo_compra y confirmada)
        now = datetime.now()
        cursor.execute(
            "INSERT INTO venta (fk_idc, fecha, hora, total, estado, codigo_compra, confirmada) VALUES (%s, %s, %s, %s, '1', %s, false) RETURNING idv",
            (idc, now.date(), now.time(), total, codigo_compra)
        )
        idv = cursor.fetchone()[0]
        # Insertar en dtventa y actualizar stock
        for p in productos:
            cursor.execute(
                "INSERT INTO dtventa (fk_idv, fk_idp, cantidad, subtotal, estado) VALUES (%s, %s, %s, %s, '1')",
                (idv, p['idp'], p['cantidad'], p['subtotal'])
            )
            cursor.execute("UPDATE producto SET stock = stock - %s WHERE idp = %s", (p['cantidad'], p['idp']))
        conexion.commit()
        # Obtener correo del cliente
        cursor.execute("SELECT correo, nombre FROM cliente WHERE idc = %s", (idc,))
        cliente = cursor.fetchone()
        cursor.close()
        conexion.close()
        session['carrito'] = []

        # Generar texto de la factura para el QR
        factura_text = f"Factura JS SPORT\nCódigo de compra: {codigo_compra}\n"
        for p in productos:
            factura_text += f"{p['nombre']} x{p['cantidad']} = ${p['subtotal']}\n"
        factura_text += f"Total: ${total}"

        # Generar QR y guardar en static/img/qr_factura.png
        qr = qrcode.make(factura_text)
        qr_path = os.path.join(app.root_path, 'static', 'img', 'qr_factura.png')
        qr.save(qr_path)

        # Enviar correo con QR y detalles de compra
        if cliente:
            correo_cliente = cliente[0]
            nombre_cliente = cliente[1]
            try:
                email = EmailMessage()
                email["Subject"] = "¡Gracias por tu compra en JS SPORT!"
                email["From"] = GMAIL_USER
                email["To"] = correo_cliente
                cuerpo = f"Hola {nombre_cliente},\n\nGracias por tu compra.\n\nCódigo de compra: {codigo_compra}\n\nProductos:\n"
                for p in productos:
                    cuerpo += f"- {p['nombre']} x{p['cantidad']} = ${p['subtotal']}\n"
                cuerpo += f"\nTotal: ${total}\n\nAdjunto encontrarás el código QR de tu factura.\n\nPresenta este código al llegar al local para confirmar tu compra.\n\nAtentamente,\nJS SPORT"
                email.set_content(cuerpo)
                with open(qr_path, 'rb') as f:
                    email.add_attachment(f.read(), maintype='image', subtype='png', filename='qr_factura.png')
                with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
                    smtp.starttls()
                    smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                    smtp.send_message(email)
            except Exception as e:
                print('Error enviando correo de compra:', e)

        return render_template('factura.html', productos=productos, total=total, qr_img='img/qr_factura.png', codigo_compra=codigo_compra)
    except Exception as e:
        flash("Error al realizar la compra")
        return redirect(url_for('ver_carrito'))

@app.route('/confirmar_compra', methods=['GET', 'POST'])
def confirmar_compra():
    mensaje = None
    if request.method == 'POST':
        codigo = request.form.get('codigo_compra')
        if codigo:
            conexion = conectar()
            cursor = conexion.cursor()
            cursor.execute("SELECT idv, confirmada, fk_idc FROM venta WHERE codigo_compra = %s", (codigo,))
            venta = cursor.fetchone()
            if venta:
                if not venta[1]:
                    cursor.execute("UPDATE venta SET confirmada = true WHERE idv = %s", (venta[0],))
                    # Obtener correo del cliente
                    cursor.execute("SELECT correo, nombre FROM cliente WHERE idc = %s", (venta[2],))
                    cliente = cursor.fetchone()
                    if cliente:
                        correo_cliente = cliente[0]
                        nombre_cliente = cliente[1]
                        # Enviar correo
                        try:
                            email = EmailMessage()
                            email["Subject"] = "¡Tu compra ha sido confirmada!"
                            email["From"] = GMAIL_USER
                            email["To"] = correo_cliente
                            email.set_content(f"Hola {nombre_cliente},\n\nTu compra con código {codigo} ha sido confirmada.\n¡Gracias por comprar en JS SPORT!\n\nAtentamente,\nJS SPORT")
                            with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
                                smtp.starttls()
                                smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                                smtp.send_message(email)
                        except Exception as e:
                            print('Error enviando correo:', e)
                    conexion.commit()
                    mensaje = 'Compra confirmada correctamente.'
                else:
                    mensaje = 'Esta compra ya fue confirmada.'
            else:
                mensaje = 'Código de compra no encontrado.'
            cursor.close()
            conexion.close()
    return render_template('confirmar_compra.html', mensaje=mensaje)

@app.route('/sumar_stock', methods=['POST'])
def sumar_stock():
    idp = request.form['idp']
    cantidad = int(request.form['cantidad'])
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute("UPDATE producto SET stock = stock + %s WHERE idp = %s", (cantidad, idp))
        conexion.commit()
        cursor.close()
        conexion.close()
        flash('Stock actualizado correctamente.')
    except Exception as e:
        flash('Error al actualizar el stock.')
    return redirect(url_for('admin_inicio'))

@app.route('/estadisticas', methods=['GET', 'POST'])
def estadisticas():
    from datetime import datetime, timedelta
    conexion = conectar()
    cursor = conexion.cursor()
    hoy = datetime.now().date()
    # Ganancias del día
    cursor.execute("SELECT COALESCE(SUM(total),0) FROM venta WHERE fecha = %s", (hoy,))
    total_dia = cursor.fetchone()[0]
    # Ganancias de la semana
    semana_inicio = hoy - timedelta(days=hoy.weekday())
    cursor.execute("SELECT COALESCE(SUM(total),0) FROM venta WHERE fecha >= %s AND fecha <= %s", (semana_inicio, hoy))
    total_semana = cursor.fetchone()[0]
    # Ganancias del mes
    mes_inicio = hoy.replace(day=1)
    cursor.execute("SELECT COALESCE(SUM(total),0) FROM venta WHERE fecha >= %s AND fecha <= %s", (mes_inicio, hoy))
    total_mes = cursor.fetchone()[0]
    # Ganancias del año
    anio_inicio = hoy.replace(month=1, day=1)
    cursor.execute("SELECT COALESCE(SUM(total),0) FROM venta WHERE fecha >= %s AND fecha <= %s", (anio_inicio, hoy))
    total_anio = cursor.fetchone()[0]
    # Intervalo personalizado
    total_intervalo = None
    fecha_inicio = fecha_fin = None
    if request.method == 'POST':
        fecha_inicio = request.form.get('fecha_inicio')
        fecha_fin = request.form.get('fecha_fin')
        if fecha_inicio and fecha_fin:
            cursor.execute("SELECT COALESCE(SUM(total),0) FROM venta WHERE fecha >= %s AND fecha <= %s", (fecha_inicio, fecha_fin))
            total_intervalo = cursor.fetchone()[0]
    cursor.close()
    conexion.close()
    return render_template('estadisticas.html', total_dia=total_dia, total_semana=total_semana, total_mes=total_mes, total_anio=total_anio, total_intervalo=total_intervalo, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

if __name__ == '__main__':
    app.run(debug=True)
