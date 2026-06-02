# 🔍 Monitor de Links

Ferramenta para monitoramento de disponibilidade de sites em tempo real com dashboard web, alertas automáticos e importação de planilhas.

## 📸 Preview

Dashboard web com atualização automática, cards de resumo, tabela de status e alertas recentes.

## ✅ Funcionalidades

- Verificação assíncrona de múltiplas URLs simultaneamente
- Dashboard web com atualização automática
- Pesquisa em tempo real por nome, URL ou categoria
- Alertas automáticos quando sites mudam de status
- Notificações pop-up no navegador
- Histórico completo de verificações no SQLite
- Importação de URLs via CSV, Excel (.xlsx) ou Word (.docx)
- Exportação de relatórios em CSV e JSON
- Intervalo de verificação configurável pelo painel
- Detecção inteligente de sites com Cloudflare e WAF
- Fallback TCP para sites que bloqueiam requisições HTTP

## 🛠️ Tecnologias

- **Python 3.12+**
- **FastAPI** — servidor web assíncrono
- **asyncio + aiohttp** — verificações assíncronas
- **aiosqlite** — banco de dados assíncrono
- **Pydantic** — validação de dados
- **Rich** — dashboard no terminal
- **Jinja2** — templates HTML
- **python-docx** — leitura de arquivos Word

## 🚀 Instalação

```bash
# Clone o repositório
git clone https://github.com/CipherWatch/Monitor-Links.git
cd Monitor-Links

# Crie o ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt

# Crie a pasta de dados
mkdir -p data

# Rode o servidor web
uvicorn api:app --reload --port 8000
```

Acesse: **http://localhost:8000**

## 📋 Comandos disponíveis

```bash
# Interface web
uvicorn api:app --reload --port 8000

# Terminal — verificação única
python main.py

# Terminal — scheduler contínuo
python main.py watch

# Filtrar histórico
python main.py filter --status offline
python main.py filter --name google

# Exportar relatório CSV
python main.py export

# Exportar resumo JSON
python main.py summary
```

## 📂 Formato de importação

### CSV ou Excel
| url | name |
|-----|------|
| https://exemplo.com | Meu Site |
| https://google.com | Google |

### Word (.docx)
Suporta tabela com colunas `url` e `name`, ou lista simples com um link por linha.

## 🗂️ Estrutura do projeto
Monitor-Links/
├── api.py          # Servidor FastAPI com todas as rotas
├── checker.py      # Motor de verificação assíncrono
├── scheduler.py    # Agendador de verificações
├── db.py           # Banco de dados SQLite
├── alerts.py       # Sistema de alertas
├── dashboard.py    # Dashboard no terminal (Rich)
├── report.py       # Exportação de relatórios
├── models.py       # Modelos de dados (Pydantic)
├── main.py         # Ponto de entrada CLI
├── requirements.txt
├── templates/
│   └── index.html  # Dashboard web
└── static/
├── css/style.css
└── js/app.js
## ⚙️ Configuração

O arquivo `config.json` é criado automaticamente. Exemplo:

```json
{
  "check_interval_seconds": 60,
  "timeout_seconds": 10,
  "urls": [
    {
      "url": "https://www.google.com",
      "name": "Google",
      "category": "buscadores"
    }
  ]
}
```

## 📡 API Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/` | Dashboard web |
| GET | `/api/status` | Status atual de todas as URLs |
| GET | `/api/alerts` | Histórico de alertas |
| GET | `/api/links` | Lista de URLs cadastradas |
| POST | `/api/links` | Adicionar nova URL |
| DELETE | `/api/links` | Remover URL |
| POST | `/api/links/import` | Importar planilha |
| GET | `/api/scheduler` | Intervalo atual |
| POST | `/api/scheduler` | Atualizar intervalo |

Documentação interativa disponível em: **http://localhost:8000/docs**

## 👨‍💻 Autor

**CipherWatch** — https://github.com/CipherWatch
