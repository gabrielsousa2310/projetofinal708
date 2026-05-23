# python -m venv venv - cria o ambiente virtual
# venv/scripts/activate - ativa o ambiente virtual
# pip install -r requirements.txt - instala as dependências do projeto
# pip freeze > requirements.txt - salva as dependências do projeto no arquivo requirements.txt

from flask import *
from dotenv import load_dotenv
import os

from supabase import create_client

# senha da sessão


load_dotenv()
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase = create_client(supabase_url,supabase_key)

app = Flask(__name__)
app.secret_key = '12345'


@app.route('/', methods=['GET','POST'])
def index():
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        print(email,senha)
        resposta = supabase.table('usuarios').select('*').eq('email',email).eq('senha',senha).execute()
        if len(resposta.data) > 0:
            print(resposta)
            session['id_usuario'] = resposta.data[0]['id']
            return redirect(url_for('tarefas'))
        else:
            print('Usuário não cadastrado')
    return render_template('index.html')

@app.route('/tarefas')
def tarefas():

    if 'id_usuario' not in session:
        print('Usuário não logado')
        return redirect(url_for('index'))
    
    id = session['id_usuario']
    resposta = supabase.table('tarefas').select('*').eq('usuario_id',id).execute()
    
    return render_template('tarefas.html',tarefas = resposta.data)

@app.route('/cadastro')
def cadastro():
    return render_template('cadastro.html')

if __name__ == '__main__':
    app.run(debug=True)
