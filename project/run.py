import subprocess
import os
import time
from app import create_app  # Importa a função create_app
from app import create_app, socketio
from flask import Flask

def start_server(script_name, port):
    """Função para iniciar o servidor em uma porta específica e retornar o processo."""
    process = subprocess.Popen(
        ['python', script_name],
        env={**os.environ, 'PYTHONPATH': os.path.abspath(os.path.join(os.path.dirname(__file__), 'app'))},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return process

def main():
    # Inicializa a aplicação Flask principal
    app = create_app()

    # Inicia o servidor principal (primário)
    print("Iniciando o servidor principal (primário)...")
    process_main = subprocess.Popen(
        ['python', '-m', 'flask', 'run', '--host=0.0.0.0', '--port=5000'],
        env={**os.environ, 'PYTHONPATH': os.path.abspath(os.path.join(os.path.dirname(__file__), 'app'))},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    time.sleep(2)  # Aguarde um pouco para garantir que o servidor principal tenha iniciado

    # Inicia o servidor secundário
    print("Iniciando o servidor secundário...")
    process_secondary = start_server('app/detector.py', 5001)

    try:
        # Monitorar a saída dos servidores
        while True:
            output_main = process_main.stdout.readline().strip()
            if output_main:
                print(f'Main Server: {output_main}')
                if 'Running on' in output_main:
                    print(f'URL do servidor principal (primário): {output_main.split(" ")[-1]}')

            error_main = process_main.stderr.readline().strip()
            if error_main:
                print(f'Main Server Error: {error_main}')

            output_secondary = process_secondary.stdout.readline().strip()
            if output_secondary:
                print(f'Secondary Server: {output_secondary}')
                if 'Running on' in output_secondary:
                    print(f'URL do servidor secundário: {output_secondary.split(" ")[-1]}')

            error_secondary = process_secondary.stderr.readline().strip()
            if error_secondary:
                print(f'Secondary Server Error: {error_secondary}')

    except KeyboardInterrupt:
        print('Interrompendo servidores...')
        process_main.terminate()
        process_secondary.terminate()

if __name__ == '__main__':
    main()
