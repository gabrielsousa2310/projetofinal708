# python -m venv venv - cria o ambiente virtual
# venv/scripts/activate - ativa o ambiente virtual
# pip install -r requirements.txt - instala as dependências do projeto
# pip freeze > requirements.txt - salva as dependências do projeto no arquivo requirements.txt
# ola
import logging
import os
import secrets
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from supabase import create_client


        

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Permite abrir a página de login mesmo antes de configurar o banco. As operações
# de dados só são liberadas quando as credenciais do Supabase estão presentes.
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("COOKIE_SECURE", "false").lower() == "true"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=8)
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)
if not os.getenv("SECRET_KEY"):
    logger.warning("SECRET_KEY não definida; configure uma chave fixa no .env antes de publicar o sistema.")


def get_csrf_token():
    """Retorna um token CSRF estável durante a sessão do usuário."""
    token = session.get("_csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.context_processor
def inject_template_helpers():
    return {"csrf_token": get_csrf_token}


@app.before_request
def protect_requests():
    if request.method == "POST":
        submitted_token = request.form.get("csrf_token", "")
        expected_token = session.get("_csrf_token", "")
        if not expected_token or not secrets.compare_digest(submitted_token, expected_token):
            abort(400, description="Token de segurança inválido. Atualize a página e tente novamente.")

    # Não expõe páginas internas se o banco não estiver configurado.
    if supabase is None and request.endpoint not in {"index", "static"}:
        flash("Configure SUPABASE_URL e SUPABASE_KEY no arquivo .env para usar o sistema.", "warning")
        return redirect(url_for("index"))

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""

        if supabase is None:
            flash("O banco de dados não está configurado. Confira o arquivo .env.", "danger")
            return render_template("index.html"), 503

        try:
            resposta = supabase.table("usuarios").select("*").eq("email", email).limit(1).execute()
            usuario = resposta.data[0] if resposta.data else None
            senha_valida = False

            if usuario:
                senha_salva = str(usuario.get("senha") or "")
                # Compatibilidade com contas antigas que ainda guardam senha em texto puro.
                if senha_salva.startswith(("scrypt:", "pbkdf2:", "argon2:")):
                    try:
                        senha_valida = check_password_hash(senha_salva, senha)
                    except (ValueError, TypeError):
                        senha_valida = False
                else:
                    senha_valida = secrets.compare_digest(senha_salva, senha)
                    if senha_valida:
                        # Migra a senha antiga para hash quando as permissões do banco permitem.
                        # A falha da migração não deve impedir o login do usuário.
                        try:
                            supabase.table("usuarios").update({"senha": generate_password_hash(senha)}).eq("id", usuario["id"]).execute()
                        except Exception:
                            logger.warning("Não foi possível migrar a senha antiga para hash; revise as permissões da tabela usuarios.")

            if usuario and senha_valida:
                session.clear()
                session["id_usuario"] = usuario["id"]
                session.permanent = True
                get_csrf_token()
                return redirect(url_for("dashboard"))

            flash("E-mail ou senha incorretos.", "danger")
        except Exception:
            logger.exception("Falha ao autenticar usuário")
            flash("Não foi possível realizar o login. Tente novamente mais tarde.", "danger")

    return render_template("index.html")


# PAGINA INICIAL


@app.route("/dashboard")
def dashboard():
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    registro_os = supabase.table("registro_os").select("*").execute()
    funcionarios = supabase.table("funcionarios").select("*").execute()
    clientes = supabase.table("clientes").select("*,registro_os(id)").execute()
    veiculos = supabase.table("veiculos").select("id").execute()

    total_clientes = len(clientes.data) if clientes.data else 0
    total_registro_os = len(registro_os.data) if registro_os.data else 0
    total_funcionarios = len(funcionarios.data) if funcionarios.data else 0
    total_veiculos = len(veiculos.data) if veiculos.data else 0
    
    relatorio = (
        supabase.table("registro_os")
        .select("*, clientes(nome), funcionarios(nome), veiculos(placa, marca, modelo)")
        .execute()
    )

    return render_template(
        "dashboard.html",
        total_clientes=total_clientes,
        total_registro_os=total_registro_os,
        total_funcionarios=total_funcionarios,
        total_veiculos=total_veiculos,
        relatorio=relatorio.data,
        clientes=clientes.data,
    )


# ROTAS DE CADASTRO DE CLIENTES, FUNCIONARIOS, VEICULOS E REGISTRO DE ORDEM DE SERVIÇO
@app.route("/cadastro_clientes", methods=["GET", "POST"])
def cadastro_clientes():

    if "id_usuario" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        email = request.form.get("email")
        cpf = request.form.get("cpf")
        endereco = request.form.get("endereco")
        observacoes = request.form.get("observacoes")

        dados = {
            "nome": nome,
            "telefone": telefone,
            "email": email,
            "cpf": cpf,
            "endereco": endereco,
            "observacoes": observacoes,
            "ativo": True,
        }
        supabase.table("clientes").insert(dados).execute()

        return redirect(url_for("dashboard"))

    return render_template("clientes/cadastro_clientes.html")


@app.route("/cadastro_funcionarios", methods=["GET", "POST"])
def cadastro_funcionarios():

    if "id_usuario" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":

        nome = request.form.get("nome")
        cpf = request.form.get("cpf")
        telefone = request.form.get("telefone")
        email = request.form.get("email")
        endereco = request.form.get("endereco")
        numero = request.form.get("numero")
        complemento = request.form.get("complemento")

        cargo = request.form.get("cargo")
        especialidade = request.form.get("especialidade")
        salario = request.form.get("salario")
        data_admissao = request.form.get("data_admissao")

        possui_cnh = request.form.get("possui_cnh")

        observacoes = request.form.get("observacoes")

        dados = {
            "nome": nome,
            "cpf": cpf,
            "telefone": telefone,
            "email": email,
            "endereco": endereco,
            "numero": numero,
            "complemento": complemento,
            "cargo": cargo,
            "especialidade": especialidade,
            "salario": salario,
            "data_admissao": data_admissao,
            "possui_cnh": possui_cnh,
            "observacoes": observacoes,
            "ativo": True,
        }

        supabase.table("funcionarios").insert(dados).execute()

        return redirect(url_for("dashboard"))

    return render_template("funcionarios/cadastro_funcionarios.html")


@app.route("/registro_os", methods=["GET", "POST"])
def registro_os():

    if "id_usuario" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        veiculo_id = request.form.get("veiculo_id")
        funcionario_id = request.form.get("funcionario_id")
        problema_relatado = request.form.get("problema_relatado")
        servico_realizado = request.form.get("servico_realizado")
        valor = request.form.get("valor")
        status = request.form.get("status")
        observacoes = request.form.get("observacoes")

        dados = {
            "cliente_id": cliente_id,
            "veiculo_id": veiculo_id,
            "funcionario_id": funcionario_id,
            "problema_relatado": problema_relatado,
            "servico_realizado": servico_realizado,
            "valor": valor,
            "status": status,
            "observacoes": observacoes,
        }
        try:
            if valor:
                dados["valor"] = float(valor.replace(",", "."))
            else:
                dados["valor"] = None
            supabase.table("registro_os").insert(dados).execute()
            flash("Ordem de serviço registrada com sucesso!", "success")
        except (ValueError, TypeError):
            flash("Informe um valor válido para a ordem de serviço.", "danger")
            return redirect(url_for("registro_os"))
        except Exception:
            logger.exception("Falha ao registrar ordem de serviço")
            flash("Não foi possível registrar a ordem de serviço.", "danger")
            return redirect(url_for("registro_os"))

        return redirect(url_for("registro_os"))

    clientes = supabase.table("clientes").select("*").execute()
    funcionarios = supabase.table("funcionarios").select("*").execute()
    veiculos = supabase.table("veiculos").select("*").execute()
    registro_os = (supabase.table("registro_os").select("*,clientes(nome),veiculos(marca,modelo,placa)").execute())
    os = (supabase.table("registro_os").select("*, clientes(nome), funcionarios(nome), veiculos(placa)").execute())

    return render_template(
        "os/registro_os.html",
        os=os.data,
        registro_os=registro_os.data,
        funcionarios=funcionarios.data,
        clientes=clientes.data,
        veiculos=veiculos.data,
    )


@app.route("/cadastro_veiculos", methods=["GET", "POST"])
def cadastro_veiculos():
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        cliente_id = request.form.get("cliente_id")
        marca = request.form.get("marca")
        modelo = request.form.get("modelo")
        ano = request.form.get("ano")
        placa = request.form.get("placa")
        cor = request.form.get("cor")
        observacoes = request.form.get("observacoes")

        dados = {
            "cliente_id": cliente_id,
            "marca": marca,
            "modelo": modelo,
            "ano": ano,
            "placa": placa,
            "cor": cor,
            "observacoes": observacoes,
        }

        try:
            if not cliente_id:
                flash("Selecione o cliente responsável pelo veículo.", "danger")
                return redirect(url_for("cadastro_veiculos"))
            if not marca or not modelo or not placa:
                flash("Preencha marca, modelo e placa do veículo.", "danger")
                return redirect(url_for("cadastro_veiculos"))
            if ano:
                dados["ano"] = int(ano)
            dados["marca"] = marca.strip()
            dados["modelo"] = modelo.strip()
            dados["placa"] = placa.strip().upper()
            dados["cor"] = (cor or "").strip() or None
            dados["observacoes"] = (observacoes or "").strip() or None
            supabase.table("veiculos").insert(dados).execute()
            flash("Veículo cadastrado com sucesso!", "success")
            return redirect(url_for("listar_veiculos"))
        except (ValueError, TypeError):
            flash("Informe um ano válido para o veículo.", "danger")
        except Exception:
            logger.exception("Falha ao cadastrar veículo")
            flash("Não foi possível cadastrar o veículo. Confira os dados e tente novamente.", "danger")

    clientes = supabase.table("clientes").select("*").eq("ativo", True).order("nome").execute()

    return render_template("veiculos/cadastro_veiculos.html", clientes=clientes.data)


@app.route("/veiculos")
def listar_veiculos():
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    try:
        resultado = supabase.table("veiculos").select("*").order("id", desc=True).execute()
        clientes_resultado = supabase.table("clientes").select("id,nome").execute()
        clientes_por_id = {str(cliente["id"]): cliente.get("nome", "-") for cliente in (clientes_resultado.data or [])}
        veiculos = resultado.data or []
        for veiculo in veiculos:
            veiculo["cliente_nome"] = clientes_por_id.get(str(veiculo.get("cliente_id")), "Cliente não encontrado")
        return render_template("veiculos/listar_veiculos.html", veiculos=veiculos)
    except Exception:
        logger.exception("Falha ao listar veículos")
        flash("Não foi possível carregar a lista de veículos.", "danger")
        return render_template("veiculos/listar_veiculos.html", veiculos=[])


@app.route("/editar_veiculo/<int:id>", methods=["GET", "POST"])
def editar_veiculo(id):
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    resultado = supabase.table("veiculos").select("*").eq("id", id).limit(1).execute()
    if not resultado.data:
        abort(404)
    veiculo = resultado.data[0]

    if request.method == "POST":
        try:
            ano = (request.form.get("ano") or "").strip()
            cliente_id = request.form.get("cliente_id")
            marca = (request.form.get("marca") or "").strip()
            modelo = (request.form.get("modelo") or "").strip()
            placa = (request.form.get("placa") or "").strip().upper()
            if not cliente_id or not marca or not modelo or not placa:
                flash("Cliente, marca, modelo e placa são obrigatórios.", "danger")
            else:
                dados = {
                    "cliente_id": cliente_id,
                    "marca": marca,
                    "modelo": modelo,
                    "ano": int(ano) if ano else None,
                    "placa": placa,
                    "cor": (request.form.get("cor") or "").strip() or None,
                    "observacoes": (request.form.get("observacoes") or "").strip() or None,
                }
                supabase.table("veiculos").update(dados).eq("id", id).execute()
                flash("Veículo atualizado com sucesso!", "success")
                return redirect(url_for("listar_veiculos"))
        except (ValueError, TypeError):
            flash("Informe um ano válido para o veículo.", "danger")
        except Exception:
            logger.exception("Falha ao atualizar veículo")
            flash("Não foi possível atualizar o veículo.", "danger")

    clientes = supabase.table("clientes").select("*").order("nome").execute()
    return render_template("veiculos/editar_veiculo.html", veiculo=veiculo, clientes=clientes.data or [])


# LISTAGEM DE CLIENTES, FUNCIONARIOS, VEICULOS E REGISTRO DE ORDEM DE SERVIÇO


@app.route("/listar_clientes_ativos")
def listar_clientes_ativos():
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    clientes = supabase.table("clientes").select("*").eq("ativo", True).execute()

    return render_template("clientes/listar_clientes_ativos.html", clientes=clientes.data)


@app.route("/listar_clientes_inativos")
def listar_clientes_inativos():
    if "id_usuario" not in session:
        return redirect(url_for("index"))
    
    clientes = supabase.table("clientes").select("*").eq("ativo", False).order("nome").execute()

    return render_template("clientes/listar_clientes_inativos.html", clientes=clientes.data)


@app.route("/listar_os")
def listar_os():
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    os_service = (
        supabase.table("registro_os")
        .select(
            "*, clientes(id, nome), funcionarios(id, nome), veiculos(marca,modelo,placa)"
        )
        .execute()
    )

    return render_template("os/listar_os.html", os_service=os_service.data)


@app.route("/listar_funcionarios_ativos")
def listar_funcionarios_ativos():
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    funcionarios = supabase.table("funcionarios").select("*").eq("ativo", True).execute()
    
    return render_template("funcionarios/listar_funcionarios_ativos.html", funcionarios=funcionarios.data)

@app.route("/listar_funcionarios_inativos")
def listar_funcionarios_inativos():
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    funcionarios = supabase.table("funcionarios").select("*").eq("ativo", False).execute()

    return render_template("funcionarios/listar_funcionarios_inativos.html", funcionarios=funcionarios.data)



# GERENCIAMENTO DO SISTEMA, EXCLUSAO, EDICAO E LOGOUT


# EDICOES
#BOTAO
@app.route("/editar_clientes/<int:id>", methods=["GET", "POST"])
def editar_clientes(id):
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        email = request.form.get("email")
        cpf = request.form.get("cpf")
        endereco = request.form.get("endereco")
        observacoes = request.form.get("observacoes")

        dados = {
            "nome": nome,
            "telefone": telefone,
            "email": email,
            "cpf": cpf,
            "endereco": endereco,
            "observacoes": observacoes,
        }

        supabase.table("clientes").update(dados).eq("id", id).execute()
        flash("Cliente atualizado com sucesso!", "success")
        return redirect(url_for("listar_clientes_ativos"))

    cliente = supabase.table("clientes").select("*").eq("id", id).limit(1).execute()
    if not cliente.data:
        abort(404)
    return render_template("clientes/editar_clientes.html", cliente=cliente.data[0])


@app.route("/editar_funcionario/<int:id>", methods=["GET", "POST"])
def editar_funcionario(id):
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        salario = (request.form.get("salario") or "").strip()
        try:
            dados = {
                "nome": (request.form.get("nome") or "").strip(),
                "cpf": (request.form.get("cpf") or "").strip() or None,
                "telefone": (request.form.get("telefone") or "").strip() or None,
                "email": (request.form.get("email") or "").strip() or None,
                "endereco": (request.form.get("endereco") or "").strip() or None,
                "numero": (request.form.get("numero") or "").strip() or None,
                "complemento": (request.form.get("complemento") or "").strip() or None,
                "cargo": (request.form.get("cargo") or "").strip() or None,
                "especialidade": (request.form.get("especialidade") or "").strip() or None,
                "salario": float(salario.replace(",", ".")) if salario else None,
                "data_admissao": request.form.get("data_admissao") or None,
                "possui_cnh": request.form.get("possui_cnh") or None,
                "observacoes": (request.form.get("observacoes") or "").strip() or None,
            }
            if not dados["nome"]:
                flash("O nome do funcionário é obrigatório.", "danger")
            else:
                supabase.table("funcionarios").update(dados).eq("id", id).execute()
                flash("Funcionário atualizado com sucesso!", "success")
                return redirect(url_for("listar_funcionarios_ativos"))
        except (ValueError, TypeError):
            flash("Informe um salário válido.", "danger")
        except Exception:
            logger.exception("Falha ao atualizar funcionário")
            flash("Não foi possível atualizar o funcionário.", "danger")

    resultado = supabase.table("funcionarios").select("*").eq("id", id).limit(1).execute()
    if not resultado.data:
        abort(404)
    return render_template("funcionarios/editar_funcionario.html", funcionario=resultado.data[0])


# EDICAO DE OS
#BOTAO
@app.route("/editar_os/<int:id>", methods=["GET", "POST"])
def editar_os(id):
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    if request.method == "POST":
        valor = (request.form.get("valor") or "").strip()
        try:
            dados = {
                "cliente_id": request.form.get("cliente_id"),
                "veiculo_id": request.form.get("veiculo_id"),
                "funcionario_id": request.form.get("funcionario_id"),
                "problema_relatado": request.form.get("problema_relatado"),
                "servico_realizado": request.form.get("servico_realizado"),
                "valor": float(valor.replace(",", ".")) if valor else None,
                "status": request.form.get("status"),
                "observacoes": request.form.get("observacoes"),
            }
            supabase.table("registro_os").update(dados).eq("id", id).execute()
            flash("Ordem de serviço atualizada com sucesso!", "success")
            return redirect(url_for("listar_os"))
        except (ValueError, TypeError):
            flash("Informe um valor válido para a ordem de serviço.", "danger")

    ordem_resultado = supabase.table("registro_os").select("*").eq("id", id).limit(1).execute()
    if not ordem_resultado.data:
        abort(404)
    ordem = ordem_resultado.data[0]
    clientes = supabase.table("clientes").select("*").execute()
    funcionarios = supabase.table("funcionarios").select("*").execute()
    veiculos = supabase.table("veiculos").select("*").execute()

    return render_template(
        "os/editar_os.html",
        ordem=ordem,
        funcionarios=funcionarios.data,
        clientes=clientes.data,
        veiculos=veiculos.data,
    )

#BOTAO
@app.route("/excluir_cliente/<int:id>", methods=["POST"])
def excluir_cliente(id):
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    supabase.table("clientes").delete().eq("id", id).execute()

    return redirect(url_for("listar_clientes_ativos"))

#BOTAO
@app.route("/inativar_cliente/<int:id>", methods=["POST"])
def inativar_cliente(id):

    if "id_usuario" not in session:
        return redirect(url_for("index"))

    supabase.table("clientes").update({"ativo": False}).eq("id", id).execute()

    return redirect(url_for("listar_clientes_ativos"))
#BOTAO
@app.route("/reativar_cliente/<int:id>", methods=["POST"])
def reativar_cliente(id):
    
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    supabase.table("clientes").update({"ativo": True}).eq("id", id).execute()

    return redirect(url_for("listar_clientes_inativos"))
#BOTAO
@app.route("/inativar_funcionario/<int:id>", methods=["POST"])
def inativar_funcionario(id):
    if "id_usuario" not in session:
        return redirect(url_for("index"))
    
    supabase.table("funcionarios").update({"ativo": False}).eq("id", id).execute()
    
    return redirect(url_for("listar_funcionarios_ativos"))
#BOTAO
@app.route("/reativar_funcionario/<int:id>", methods=["POST"])
def reativar_funcionario(id):
    if "id_usuario" not in session:
        return redirect(url_for("index"))
    
    supabase.table("funcionarios").update({"ativo": True}).eq("id", id).execute()
    
    return redirect(url_for("listar_funcionarios_inativos"))

# EXCLUSAO DE VEICULO
#BOTAO
@app.route("/excluir_veiculo/<int:id>", methods=["POST"])
def excluir_veiculo(id):
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    try:
        supabase.table("veiculos").delete().eq("id", id).execute()
        flash("Veículo excluído com sucesso.", "success")
    except Exception:
        logger.exception("Falha ao excluir veículo")
        flash("Não foi possível excluir este veículo. Verifique se ele está vinculado a uma ordem de serviço.", "danger")
    return redirect(url_for("listar_veiculos"))


# EXCLUSAO DE OS
#BOTAO
@app.route("/excluir_os/<int:id>", methods=["POST"])
def excluir_os(id):
    if "id_usuario" not in session:
        return redirect(url_for("index"))

    supabase.table("registro_os").delete().eq("id", id).execute()

    return redirect(url_for("listar_os"))

#BOTAO
@app.route("/sair", methods=["POST"])
def sair():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
