# python -m venv venv - cria o ambiente virtual
# venv/scripts/activate - ativa o ambiente virtual
# pip install -r requirements.txt - instala as dependências do projeto
# pip freeze > requirements.txt - salva as dependências do projeto no arquivo requirements.txt
# ola
from flask import *
from dotenv import load_dotenv
import os
from supabase import create_client

# senha da sessão: 12345


load_dotenv()
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase = create_client(supabase_url,supabase_key)

app = Flask(__name__)
app.secret_key = '12345'


@app.route('/', methods=['GET','POST'])
def index():
    if 'id_usuario' not in session:
        print('Usuário não logado')
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        print(email,senha)
        resposta = supabase.table('usuarios').select('*').eq('email',email).eq('senha',senha).execute()
        if len(resposta.data) > 0:
            print(resposta)
            session['id_usuario'] = resposta.data[0]['id']
            return redirect(url_for('dashboard'))
        else:
            print('Usuário não cadastrado')
    return render_template('index.html')


@app.route('/dashboard')
def dashboard():
    if 'id_usuario' not in session:
        print('Usuário não logado')
        return redirect(url_for('index'))
    clientes = supabase.table('clientes').select('*').execute()
    registro_os = supabase.table('registro_os').select('*').execute()
    funcionarios = supabase.table('funcionarios').select('*').execute()

    total_clientes = len(clientes.data) if clientes.data else 0 
    total_registro_os = len(registro_os.data) if registro_os.data else 0 
    total_funcionarios = len(funcionarios.data) if funcionarios.data else 0 

    return render_template('dashboard.html',total_clientes=total_clientes, total_registro_os=total_registro_os, total_funcionarios=total_funcionarios)


@app.route('/cadastro_clientes',methods=['GET','POST'])
def cadastro_clientes():
    #verificar se o usuário está logado
    if 'id_usuario' not in session:
        print('Usuário não logado')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        endereco = request.form.get('endereco')
        observacoes = request.form.get('observacoes')

        dados = {
            'nome': nome,
            'telefone': telefone,
            'email': email,
            'cpf': cpf,
            'endereco': endereco,
            'observacoes': observacoes
        }
        supabase.table('clientes').insert(dados).execute()

        return redirect(url_for('dashboard'))

    return render_template('cadastro_clientes.html')


@app.route('/cadastro_funcionarios', methods=['GET', 'POST'])
def cadastro_funcionarios():
    #verificar se o usuário está logado
    if 'id_usuario' not in session:
        print('Usuário não logado')
        return redirect(url_for('index'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        telefone = request.form.get('telefone')
        email = request.form.get('email')
        endereco = request.form.get('endereco')

        cargo = request.form.get('cargo')
        especialidade = request.form.get('especialidade')
        salario = request.form.get('salario')
        data_admissao = request.form.get('data_admissao')

        possui_cnh = request.form.get('possui_cnh')
        
        observacoes = request.form.get('observacoes')

        dados = {
            'nome': nome,
            'cpf': cpf,
            'telefone': telefone,
            'email': email,
            'endereco': endereco,
            'cargo': cargo,
            'especialidade': especialidade,
            'salario': salario,
            'data_admissao': data_admissao,
            'possui_cnh': possui_cnh,
            'observacoes': observacoes
        }

        supabase.table('funcionarios').insert(dados).execute()

        return redirect(url_for('dashboard'))

    return render_template('cadastro_funcionarios.html')


@app.route('/registro_os', methods=['GET', 'POST'])
def registro_os():

    if 'id_usuario' not in session:
        print('Usuário não logado')
        return redirect(url_for('index'))

    if request.method == 'POST':

        cliente = request.form.get('cliente')
        veiculo = request.form.get('veiculo')
        placa = request.form.get('placa')
        funcionario = request.form.get('funcionario')
        problema_relatado = request.form.get('problema_relatado')
        servico_realizado = request.form.get('servico_realizado')
        valor = request.form.get('valor')
        status = request.form.get('status')
        observacoes = request.form.get('observacoes')

        dados = {
            'cliente': cliente,
            'veiculo': veiculo,
            'placa': placa,
            'funcionario': funcionario,
            'problema_relatado': problema_relatado,
            'servico_realizado': servico_realizado,
            'valor': valor,
            'status': status,
            'observacoes': observacoes
        }

        supabase.table('registro_os').insert(dados).execute()
        flash('Ordem de serviço registrada com sucesso!')

        return redirect(url_for('registro_os'))
    return render_template('registro_os.html')
    

@app.route('/cadastro_veiculos', methods=['GET', 'POST'])
def cadastro_veiculos():
    if 'id_usuario' not in session:
        print('Usuario nao logado')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        ano = request.form.get('ano')
        placa = request.form.get('placa')
        cor = request.form.get('cor')
        observacoes = request.form.get('observacoes')

        dados = {
            'marca': marca,
            'modelo': modelo,
            'ano': ano,
            'placa': placa,
            'cor': cor,
            'observacoes': observacoes
        }

        supabase.table('veiculos').insert(dados).execute()
        return redirect(url_for('cadastro_veiculos'))
    return render_template('cadastro_veiculos.html')
    

@app.route('/ver_clientes')
def ver_clientes():
    if 'id_usuario' not in session:
        print('Usuario nao logado')
        return redirect(url_for('index'))

    clientes = supabase.table('clientes').select('*').execute()

    return render_template('ver_clientes.html',clientes=clientes.data)  

@app.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    if 'id_usuario' not in session:
        print('Usuario nao logado')
        return redirect(url_for('index'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        telefone = request.form.get('telefone')

        dados = {
            'nome': nome,
            'email': email,
            'telefone': telefone
        }

        supabase.table('clientes').update(dados).eq('id', id).execute()
        return redirect(url_for('ver_clientes'))

    cliente = supabase.table('clientes').select('*').eq('id', id).execute()
    return render_template('editar_cliente.html', cliente=cliente.data[0])

@app.route('/excluir_cliente/<int:id>')
def excluir_cliente(id):
    supabase.table('clientes').delete().eq('id', id).execute()
    return redirect(url_for('ver_clientes'))


@app.route('/sair')
def sair():
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)
