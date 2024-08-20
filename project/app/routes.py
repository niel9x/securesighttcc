from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import bcrypt
import mysql.connector
import os
import jwt
import datetime
import requests
from app.models import gerar_link_pagamento
from dotenv import load_dotenv
from babel.dates import format_date
import matplotlib.pyplot as plt

# Carregar variáveis de ambiente
load_dotenv()

routes = Blueprint('routes', __name__)

def test_connection_to_secondary():
    try:
        response = requests.get('http://localhost:5001/test_connection')
        print(response.json())
    except requests.exceptions.RequestException as e:
        print(f'Erro ao conectar ao servidor secundário: {e}')

# Configuração do JWT
SECRET_KEY = '#'

# Dicionário com os valores dos planos
plan_values = {
    'LifeGuard': 479.90,
    'SecureShield': 799.90,
    'SafeGuard': 1650.00
}

# Configuração do servidor secundário
SECONDARY_SERVER_URL = os.getenv('SECONDARY_SERVER_URL', 'http://localhost:5001/alert')

# Função auxiliar para conexão ao banco de dados
def get_db_connection():
    db_config = {
        'user': os.getenv('DB_USER', '#'),
        'password': os.getenv('DB_PASSWORD', '#'),
        'host': os.getenv('DB_HOST', '#'),
        'port': os.getenv('DB_PORT', '#'),
        'database': os.getenv('DB_NAME', '#')
    }
    conn = mysql.connector.connect(**db_config)
    return conn

# Função para enviar alerta para o servidor secundário
def enviar_alerta_para_secundario(email, nome_user, label, confidence):
    data = {
        'email': email,
        'nome_user': nome_user,
        'label': label,
        'confidence': confidence
    }
    try:
        response = requests.post(SECONDARY_SERVER_URL, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f'Erro ao enviar alerta para o servidor secundário: {e}')

# Função para verificar o token JWT
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

# Rota para a página inicial
@routes.route('/')
def home():
    return render_template('home.html')

@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password').encode('utf-8')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password, user['senha_hash'].encode('utf-8')):
            if user['assinante']:
                token = jwt.encode({
                    'email': user['email'],
                    'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
                }, SECRET_KEY, algorithm='HS256')
                
                return redirect(f'http://localhost:5001/user-int?token={token}')
            else:
                return render_template('login.html', message='Você não possui planos ativos', show_plan_button=True)
        else:
            return render_template('login.html', message='Email ou senha inválidos')
    return render_template('login.html')

# Rota para signup
@routes.route('/signup', methods=['POST'])
def signup():
    data = request.form
    phone = data.get('number')
    name = data.get('nome')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    
    # Validação do número de telefone
    if len(phone) != 11:
        return jsonify({'success': False, 'message': 'Número de telefone deve ter exatamente 11 dígitos'})
    
    # Verificação de correspondência de senhas
    if password != confirm_password:
        return jsonify({'success': False, 'message': 'Senhas não são idênticas'})
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Verificar se o email já está cadastrado
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Email já cadastrado'})
        
        # Verificar se o número de telefone já está cadastrado
        cursor.execute("SELECT * FROM usuarios WHERE numero_telefone = %s", (phone,))
        if cursor.fetchone():
            return jsonify({'success': False, 'message': 'Número de telefone já cadastrado'})
        
        # Gerar salt e hash da senha
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        # Inserir novo usuário no banco de dados
        cursor.execute("INSERT INTO usuarios (nome, email, numero_telefone, senha_hash, salt, assinante) VALUES (%s, %s, %s, %s, %s, %s)", 
                       (name, email, phone, hashed_password.decode('utf-8'), salt.decode('utf-8'), False))
        conn.commit()
        session['email'] = email
        return redirect(url_for('routes.choose_plan'))
    
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erro ao cadastrar usuário: {str(err)}'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': f'Erro inesperado: {str(e)}'})
    finally:
        conn.close()


# Rota para escolher plano
@routes.route('/choose_plan', methods=['GET', 'POST'])
def choose_plan():
    if 'email' in session:
        if request.method == 'POST':
            selected_plan = request.form.get('plan')
            link_pagamento = gerar_link_pagamento(selected_plan)
            return redirect(link_pagamento)
        
        return render_template('planos.html')
    else:
        return redirect(url_for('routes.login'))

# Rota para processar pagamento aprovado
@routes.route('/compracerta', methods=['GET'])
def processar_pagamento_aprovado():
    collection_id = request.args.get('collection_id')
    payment_id = request.args.get('payment_id')
    preference_id = request.args.get('preference_id')
    status = request.args.get('status')
    payment_type = request.args.get('payment_type')
    plan = request.args.get('plan')
    
    email = session.get('email')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id, nome FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user:
            if status == 'approved':
                valor = plan_values.get(plan)
                cursor.execute(
                    "INSERT INTO pagamentos (id_usuario, nome_usuario, collection_id, payment_id, preference_id, status, payment_type, nome_produto, valor) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                    (user['id'], user['nome'], collection_id, payment_id, preference_id, status, payment_type, plan, valor)
                )
                conn.commit()

                cursor.execute("UPDATE usuarios SET assinante = TRUE WHERE id = %s", (user['id'],))
                conn.commit()
                
                enviar_alerta_para_secundario(email, user['nome'], plan, valor)
                
                return redirect(url_for('routes.confirmacao_pagamento'))
        
        return redirect(url_for('routes.confirmacao_pagamento'))

    except Exception as e:
        conn.rollback()
        return f"Erro ao processar pagamento: {str(e)}"
    finally:
        conn.close()

# Rota para confirmação de pagamento
@routes.route('/confirmacao_pagamento')
def confirmacao_pagamento():
    return render_template('success.html')

# Rota para logout
@routes.route('/logout')
def logout():
    session.pop('email', None)
    return redirect(url_for('routes.login'))

@routes.route('/user-int')
def user_int():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('routes.login'))

    decoded_token = verificar_token(token)
    if not decoded_token:
        return redirect(url_for('routes.login'))

    email = decoded_token['email']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar se o usuário existe
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()

    if not user:
        return redirect(url_for('routes.login'))
    
    if not user.get('assinante', False):
        return redirect(url_for('routes.choose_plan'))
    
    # Se o usuário estiver autenticado e for assinante, renderizar user-int.html
    return render_template('user-int.html', token=token)

@routes.route('/charts')
def charts():
    token = request.args.get('token')
    if not token:
        return redirect(url_for('routes.login'))

    decoded_token = verificar_token(token)
    if not decoded_token:
        return redirect(url_for('routes.login'))

    email = decoded_token['email']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar se o usuário existe
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()

    if not user:
        return redirect(url_for('routes.login'))

    if not user.get('assinante', False):
        return redirect(url_for('routes.choose_plan'))

    # Obter notificações do usuário
    cursor.execute("SELECT data FROM alerta WHERE email = %s ORDER BY data DESC", (email,))
    notificacoes = cursor.fetchall()

    # Inicializar os dados dos meses
    meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    quantidade_alertas_por_mes = [0] * 12  # Lista para armazenar a quantidade de alertas para cada mês

    # Contar alertas por mês
    for n in notificacoes:
        mes = n['data'].month - 1  # Mês é de 1 a 12, por isso subtrai 1 para usar como índice
        quantidade_alertas_por_mes[mes] += 1

    # Obter número de alertas e data do último alerta
    num_alertas = len(notificacoes)
    ultimo_alerta = (f'Último alerta em: {format_date(notificacoes[0]["data"], format="d MMMM", locale="pt_BR")}'
                     if notificacoes 
                     else 'Nenhum alerta registrado nos últimos dias')

    # Obter alarmes por período do dia (manhã, tarde, noite)
    cursor.execute("""
        SELECT
            CASE
                WHEN EXTRACT(HOUR FROM data) BETWEEN 0 AND 11 THEN 'Manhã'
                WHEN EXTRACT(HOUR FROM data) BETWEEN 12 AND 17 THEN 'Tarde'
                ELSE 'Noite'
            END AS periodo,
            COUNT(*) AS quantidade
        FROM alerta
        WHERE email = %s
        GROUP BY periodo
    """, (email,))
    periodos = cursor.fetchall()

    labels_periodos = ['Manhã', 'Tarde', 'Noite']
    quantidade_periodos = [0, 0, 0]

    # Preencher a quantidade de alarmes para cada período
    for periodo in periodos:
        if periodo['periodo'] == 'Manhã':
            quantidade_periodos[0] = periodo['quantidade']
        elif periodo['periodo'] == 'Tarde':
            quantidade_periodos[1] = periodo['quantidade']
        elif periodo['periodo'] == 'Noite':
            quantidade_periodos[2] = periodo['quantidade']

    conn.close()

    return render_template('charts.html', notificacoes=notificacoes, num_alertas=num_alertas, 
                       ultimo_alerta=ultimo_alerta, token=token,
                       meses=meses, quantidade_alertas=quantidade_alertas_por_mes,
                       labels_periodos=labels_periodos, quantidade_periodos=quantidade_periodos)


def obter_labels_alert():
    # Conectar ao banco de dados
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Executar uma consulta para obter os labels dos alertas
        cursor.execute("SELECT DISTINCT label FROM alertas ORDER BY label")
        result = cursor.fetchall()
        
        # Extrair labels de cada registro
        labels = [row['label'] for row in result] if result else []
    except Exception as e:
        print(f"Erro ao obter labels de alertas: {e}")
        labels = []
    finally:
        # Fechar a conexão com o banco de dados
        conn.close()
    
    return labels
# Rota para checar assinatura
@routes.route('/api/check-subscription', methods=['GET'])
def check_subscription():
    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'E-mail não fornecido'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT assinante FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return jsonify({'assinante': user['assinante']})
    else:
        return jsonify({'error': 'Usuário não encontrado'}), 404
