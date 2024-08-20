import cv2
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import mysql.connector
import datetime
import jwt
import sys
import os
from ultralytics import YOLO
import threading
import time
import winsound
from flask import Flask, Response, request, jsonify, render_template, redirect, url_for
from flask_socketio import SocketIO, emit
import base64
import bcrypt

app = Flask(__name__)
socketio = SocketIO(app)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.routes import routes

app.register_blueprint(routes, url_prefix='/')

MAIL_USERNAME = '#@gmail.com'
MAIL_PASSWORD = '#'
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587

DB_CONFIG = {
    'user': '#',
    'password': '#',
    'host': '#',
    'port': '#',
    'database': '#'
}

SECRET_KEY = '#!'

video = cv2.VideoCapture('app/ex01.mp4')
modelo = YOLO('yolov8n.pt')
area = [100, 190, 1150, 700]
alarmeCtl = False
alert_message = ""
count = 0

def get_db_connection():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

def capturar_frame(camera_url, output_path):
    cap = cv2.VideoCapture(camera_url)
    if not cap.isOpened():
        raise Exception("Não foi possível conectar à câmera.")
    ret, frame = cap.read()
    if not ret:
        raise Exception("Não foi possível capturar o frame.")
    cv2.imwrite(output_path, frame)
    cap.release()

def enviar_email(destinatario, assunto, corpo, anexo_path=None):
    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_USERNAME
        msg['To'] = destinatario
        msg['Subject'] = assunto
        
        msg.attach(MIMEText(corpo, 'plain'))
        
        if anexo_path:
            with open(anexo_path, 'rb') as file:
                parte = MIMEBase('application', 'octet-stream')
                parte.set_payload(file.read())
                encoders.encode_base64(parte)
                parte.add_header('Content-Disposition', f'attachment; filename={os.path.basename(anexo_path)}')
                msg.attach(parte)
        
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Erro ao enviar e-mail: {str(e)}")

def armazenar_notificacao(email, nome_user, label, confidence, frame_path):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT data FROM alerta WHERE email = %s ORDER BY data DESC LIMIT 1"
    cursor.execute(query, (email,))
    last_notification = cursor.fetchone()
    
    now = datetime.datetime.now()
    
    if last_notification:
        last_notification_time = last_notification['data']
        time_diff = now - last_notification_time
        
        if time_diff < datetime.timedelta(minutes=30):
            conn.close()
            return
    
    query = """
        INSERT INTO alerta (data, email, Invasao, nome_user, confidence)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (now, email, 'Invasor detectado', nome_user, confidence))
    conn.commit()
    conn.close()
    
    assunto = 'Alerta de Invasão Detectada!'
    corpo = (f'Prezado(a) Cliente,\n\n'
         'Detectamos uma atividade suspeita em sua área monitorada. '
         'Abaixo estão os detalhes da detecção:\n\n'
         f'Objeto detectado: {label}\n'
         f'Confiança: {confidence * 100:.2f}%\n\n'
         'Para sua segurança, anexamos uma imagem do momento em que a atividade foi detectada. '
         'Por favor, revise a imagem para verificar se há alguma ameaça.\n\n'
         'Caso tenha alguma dúvida ou precise de assistência adicional, não hesite em entrar em contato com as autoridades locais.\n\n'
         'Atenciosamente,\n'
         'Equipe SecureSight')
    enviar_email(email, assunto, corpo, frame_path)

def verificar_token(token):
    print(f"Token recebido: {token}")  # Para debug
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        print(f"Token decodificado: {decoded}")  # Para debug
        return decoded
    except jwt.ExpiredSignatureError:
        print("Token expirado.")  # Para debug
        return None
    except jwt.InvalidTokenError:
        print("Token inválido.")  # Para debug
        return None

    
def alarme():
    global alarmeCtl
    for _ in range(7):
        winsound.Beep(2500, 500)
    alarmeCtl = False

def gerar_feed_video(email):
    global alarmeCtl, alert_message, count, area

    while True:
        success, img = video.read()
        if not success:
            break
        
        img = cv2.resize(img, (1270, 720))
        img2 = img.copy()

        # Desenhar o contorno da área de detecção
        cv2.rectangle(img2, (area[0], area[1]), (area[2], area[3]), (0, 255, 0), 2)

        resultado = modelo(img)

        detected = False

        for objetos in resultado:
            obj = objetos.boxes
            for dados in obj:
                x1, y1, x2, y2 = dados.xyxy[0]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                cls = int(dados.cls[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                if cls == 0:  # Supondo que 0 é a classe de interesse
                    cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    if area[0] <= cx <= area[2] and area[1] <= cy <= area[3]:
                        cv2.rectangle(img2, (area[0], area[1]), (area[2], area[3]), (0, 0, 255), 2)
                        cv2.rectangle(img, (100, 30), (470, 80), (0, 0, 255), -1)
                        cv2.putText(img, 'INVASOR DETECTADO', (105, 65), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 3)
                        
                        if not alarmeCtl:
                            alarmeCtl = True
                            alert_message = f"Invasor Detectado! Contagem: {count + 1}"
                            count += 1
                            threading.Thread(target=alarme).start()
                            frame_path = 'invasor_detectado.jpg'
                            cv2.imwrite(frame_path, img)
                            armazenar_notificacao(email, 'Nome do Usuário', 'Pessoa', 0.95, frame_path)
                        detected = True

        if not detected:
            alert_message = ""

        # Combinar a imagem original e a imagem com a área de detecção
        imgFinal = cv2.addWeighted(img2, 0.5, img, 0.5, 0)
        ret, buffer = cv2.imencode('.jpg', imgFinal)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Token ausente'}), 401

    decoded_token = verificar_token(token)
    if not decoded_token:
        return jsonify({'error': 'Token inválido ou expirado'}), 401

    email = decoded_token['email']
    return Response(gerar_feed_video(email),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('request_video_feed')
def handle_video_feed():
    while True:
        success, img = video.read()
        if not success:
            break
        ret, buffer = cv2.imencode('.jpg', img)
        frame = base64.b64encode(buffer).decode('utf-8')
        emit('video_frame', {'data': frame})

@app.route('/charts')
def charts():
    token = request.args.get('token')  # Captura o token da URL
    if not token:
        return redirect(url_for('routes.login'))

    decoded_token = verificar_token(token)
    if not decoded_token:
        return redirect(url_for('routes.login'))

    return render_template('charts.html', token=token)

@app.route('/notifications', methods=['GET'])
def notifications():
    token = request.args.get('token')
    if not token:
        return jsonify({'error': 'Token ausente'}), 401

    decoded_token = verificar_token(token)
    if not decoded_token:
        return jsonify({'error': 'Token inválido ou expirado'}), 401

    email = decoded_token['email']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT data, Invasao, confidence
        FROM alerta
        WHERE email = %s
        ORDER BY data DESC
        LIMIT 10
    """
    cursor.execute(query, (email,))
    notificacoes = cursor.fetchall()
    conn.close()

    return jsonify({'notificacoes': notificacoes})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5001, debug=True, allow_unsafe_werkzeug=True)

