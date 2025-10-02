"""
Script de Deploy para o Sistema E-commerce
Automatiza o processo de deploy e configuração
"""

import os
import sys
import subprocess
import time
import requests
from datetime import datetime

class DeployManager:
    def __init__(self):
        self.start_time = datetime.now()
        self.log_file = f"deploy_{self.start_time.strftime('%Y%m%d_%H%M%S')}.log"
        
    def log(self, message):
        """Log de mensagens"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    
    def run_command(self, command, description=""):
        """Executar comando e capturar resultado"""
        self.log(f"Executando: {description or command}")
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True, 
                check=True
            )
            self.log(f"✅ Sucesso: {description or command}")
            if result.stdout:
                self.log(f"Output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"❌ Erro: {description or command}")
            self.log(f"Erro: {e.stderr}")
            return False
    
    def check_dependencies(self):
        """Verificar dependências necessárias"""
        self.log("🔍 Verificando dependências...")
        
        dependencies = [
            ("docker", "Docker"),
            ("docker-compose", "Docker Compose"),
            ("python", "Python 3.11+")
        ]
        
        for cmd, name in dependencies:
            if not self.run_command(f"which {cmd}", f"Verificar {name}"):
                self.log(f"❌ {name} não encontrado!")
                return False
        
        self.log("✅ Todas as dependências estão instaladas")
        return True
    
    def install_python_dependencies(self):
        """Instalar dependências Python"""
        self.log("📦 Instalando dependências Python...")
        
        if not self.run_command(
            "pip install -r requirements_fastapi.txt",
            "Instalar dependências FastAPI"
        ):
            return False
        
        self.log("✅ Dependências Python instaladas")
        return True
    
    def build_docker_images(self):
        """Construir imagens Docker"""
        self.log("🐳 Construindo imagens Docker...")
        
        if not self.run_command(
            "docker-compose build",
            "Construir imagens Docker"
        ):
            return False
        
        self.log("✅ Imagens Docker construídas")
        return True
    
    def start_services(self):
        """Iniciar serviços"""
        self.log("🚀 Iniciando serviços...")
        
        if not self.run_command(
            "docker-compose up -d",
            "Iniciar serviços Docker"
        ):
            return False
        
        self.log("✅ Serviços iniciados")
        return True
    
    def wait_for_services(self, timeout=60):
        """Aguardar serviços ficarem prontos"""
        self.log("⏳ Aguardando serviços ficarem prontos...")
        
        services = [
            ("http://localhost:8000/health", "FastAPI"),
            ("http://localhost:8501", "Streamlit")
        ]
        
        for url, name in services:
            self.log(f"Aguardando {name}...")
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        self.log(f"✅ {name} está pronto")
                        break
                except requests.RequestException:
                    pass
                
                time.sleep(2)
            else:
                self.log(f"❌ {name} não ficou pronto em {timeout}s")
                return False
        
        return True
    
    def run_tests(self):
        """Executar testes"""
        self.log("🧪 Executando testes...")
        
        if not self.run_command(
            "python test_fastapi.py",
            "Executar testes da API"
        ):
            self.log("⚠️ Alguns testes falharam, mas continuando...")
        
        self.log("✅ Testes executados")
        return True
    
    def show_status(self):
        """Mostrar status dos serviços"""
        self.log("📊 Status dos serviços:")
        
        self.run_command("docker-compose ps", "Status dos containers")
        
        # Testar endpoints
        endpoints = [
            ("http://localhost:8000/", "API Root"),
            ("http://localhost:8000/health", "Health Check"),
            ("http://localhost:8000/docs", "API Documentation"),
            ("http://localhost:8501", "Streamlit App")
        ]
        
        for url, name in endpoints:
            try:
                response = requests.get(url, timeout=5)
                status = "✅" if response.status_code == 200 else "❌"
                self.log(f"{status} {name}: {response.status_code}")
            except requests.RequestException as e:
                self.log(f"❌ {name}: Erro - {e}")
    
    def cleanup(self):
        """Limpeza de recursos"""
        self.log("🧹 Limpando recursos...")
        
        self.run_command(
            "docker-compose down",
            "Parar serviços Docker"
        )
        
        self.log("✅ Limpeza concluída")
    
    def deploy(self):
        """Executar deploy completo"""
        self.log("🚀 Iniciando deploy do sistema e-commerce...")
        
        steps = [
            ("Verificar dependências", self.check_dependencies),
            ("Instalar dependências Python", self.install_python_dependencies),
            ("Construir imagens Docker", self.build_docker_images),
            ("Iniciar serviços", self.start_services),
            ("Aguardar serviços", lambda: self.wait_for_services()),
            ("Executar testes", self.run_tests),
            ("Mostrar status", self.show_status)
        ]
        
        for step_name, step_func in steps:
            self.log(f"📋 {step_name}...")
            if not step_func():
                self.log(f"❌ Falha em: {step_name}")
                return False
        
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        self.log("🎉 Deploy concluído com sucesso!")
        self.log(f"⏱️ Tempo total: {duration}")
        self.log("📝 Logs salvos em: " + self.log_file)
        
        return True

def main():
    """Função principal"""
    print("🚀 Sistema de Deploy - E-commerce FastAPI")
    print("=" * 50)
    
    deploy_manager = DeployManager()
    
    try:
        success = deploy_manager.deploy()
        
        if success:
            print("\n✅ Deploy realizado com sucesso!")
            print("🌐 Acesse:")
            print("   - API: http://localhost:8000")
            print("   - Docs: http://localhost:8000/docs")
            print("   - Streamlit: http://localhost:8501")
            print("   - Nginx: http://localhost")
        else:
            print("\n❌ Deploy falhou!")
            print("📝 Verifique os logs para mais detalhes")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⏹️ Deploy interrompido pelo usuário")
        deploy_manager.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Erro inesperado: {e}")
        deploy_manager.cleanup()
        sys.exit(1)

if __name__ == "__main__":
    main()
